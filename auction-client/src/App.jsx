import React, { useState, useEffect, useRef } from 'react';
import { Bell, User, Gavel, Clock, Search, LogOut, Plus, X } from 'lucide-react';
import JSEncrypt from 'jsencrypt';
import CryptoJS from 'crypto-js';

//API CONFIG
const API_URL = 'https://localhost:8000';
const WS_URL = 'wss://localhost:8000/ws';

//Sec help funcitons

const generateAESKey = () => {
  return CryptoJS.lib.WordArray.random(32);
};

const encryptRSA = (data, publicKey) => {
  const encrypt = new JSEncrypt();
  encrypt.setPublicKey(publicKey);
  return encrypt.encrypt(data);
};

const encryptAES = (data, key) => {
  const jsonStr = JSON.stringify(data);
  const iv = CryptoJS.lib.WordArray.random(16);
  const encrypted = CryptoJS.AES.encrypt(jsonStr, key, {
    iv: iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7
  });

  const combined = iv.clone().concat(encrypted.ciphertext);
  return CryptoJS.enc.Base64.stringify(combined);
};

const decryptAES = (encryptedB64, key) => {
  const combined = CryptoJS.enc.Base64.parse(encryptedB64);

  const iv = CryptoJS.lib.WordArray.create(combined.words.slice(0, 4), 16);

  const ciphertext = CryptoJS.lib.WordArray.create(combined.words.slice(4), combined.sigBytes - 16);

  const decrypted = CryptoJS.AES.decrypt(
    { ciphertext: ciphertext },
    key,
    {
      iv: iv,
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    }
  );

  return JSON.parse(decrypted.toString(CryptoJS.enc.Utf8));
};


const createApiClient = (session) => {
  const request = async (endpoint, method = 'GET', body = null) => {
    if (!session) throw new Error("No secure session established");

    const headers = {
      'Content-Type': 'application/json',
      'X-Session-ID': session.id
    };

    let payload = null;
    if (method === 'POST' && body) {
      const encryptedData = encryptAES(body, session.key);
      payload = JSON.stringify({ data: encryptedData });
    }

    const res = await fetch(`${API_URL}${endpoint}`, {
      method,
      headers,
      body: payload
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errData.detail || "Request failed");
    }

    const resData = await res.json();
    if (resData.data) {
      return decryptAES(resData.data, session.key);
    }
    return resData;
  };

  return {
    get: (endpoint) => request(endpoint, 'GET'),
    post: (endpoint, body) => request(endpoint, 'POST', body)
  };
};

// COMPONENTS

const Navbar = ({ user, onLoginClick, onLogout, onCreateClick, onAccountClick }) => (
  <nav className="bg-slate-900 text-white p-4 shadow-md">
    <div className="w-full px-4 flex justify-between items-center">
      <div className="flex items-center space-x-2 text-xl font-bold cursor-pointer">
        <Gavel className="text-yellow-500" />
        <span>AuctionHouse</span>
      </div>
      <div className="flex items-center space-x-6">
        <a href="#" className="hover:text-yellow-400 transition">Home</a>
        {user && (
          <button onClick={onCreateClick} className="flex items-center gap-1 bg-green-600 hover:bg-green-500 px-3 py-1 rounded text-sm font-bold transition">
            <Plus size={16} /> Create Auction
          </button>
        )}
        <button className="relative hover:text-yellow-400 transition">
          <Bell size={20} />
          {/* <span className="absolute -top-1 -right-1 bg-red-500 rounded-full w-2 h-2"></span> */}
        </button>
        <div className="flex items-center space-x-4 border-l border-slate-700 pl-6">
          {user ? (
            <>
              <button onClick={onAccountClick} className="text-sm text-gray-300 flex items-center gap-1 hover:text-white">
                <User size={16} /> {user.username}
              </button>
              <button onClick={onLogout} className="text-sm text-red-400 hover:text-red-300 flex items-center gap-1">
                <LogOut size={16} /> Logout
              </button>
            </>
          ) : (
            <button onClick={onLoginClick} className="text-sm text-gray-300 hover:text-white flex items-center gap-1">
              <User size={16} /> Login / Register
            </button>
          )}
        </div>
      </div>
    </div>
  </nav>
);

const AuctionCard = ({ auction, isSelected, onClick }) => {
  const isOpen = auction.status === 'open';

  return (
    <div
      onClick={() => onClick(auction)}
      className={`p-4 border-b border-gray-200 cursor-pointer transition-colors duration-200
        ${isSelected ? 'bg-blue-50 border-l-4 border-l-blue-600' : 'hover:bg-gray-50'}
        ${!isOpen ? 'opacity-60 bg-gray-50' : ''}`}
    >
      <div className="flex justify-between items-start">
        <h3 className="font-semibold text-gray-800">{auction.item}</h3>

        <span className={`text-xs font-bold px-2 py-0.5 rounded-full uppercase border
          ${isOpen
            ? 'text-green-600 border-green-200 bg-green-50'
            : 'text-red-600 border-red-200 bg-red-50'
          }`}>
          {auction.status}
        </span>
      </div>
      <div className="mt-2 flex justify-between items-center text-sm">
        <div className="text-gray-600">
          Current Bid: <span className="font-bold text-gray-900">${auction.highest_bid.toLocaleString()}</span>
        </div>
        <div className={`flex items-center font-medium ${isOpen ? 'text-orange-600' : 'text-gray-400'}`}>
          <Clock size={14} className="mr-1" />
          {isOpen ? formatTime(auction.time_remaining) : "Ended"}
        </div>
      </div>
    </div>
  );
};

const AuctionDetail = ({ auction, onPlaceBid, user }) => {
  const [bidAmount, setBidAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setBidAmount('');
    setError('');
  }, [auction?.id]);

  if (!auction) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-400">
        <Search size={48} className="mb-4 opacity-50" />
        <p className="text-lg">Select an auction to view the details and bid</p>
      </div>
    );
  }

  const isOpen = auction.status === 'open';
  const minBid = auction.highest_bid + 1;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isOpen) return;
    if (!user) {
      setError("You must be logged in to bid.");
      return;
    }

    setLoading(true);
    setError('');

    try {
      await onPlaceBid(auction.id, Number(bidAmount));
      setBidAmount('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 h-full flex flex-col animate-fadeIn">
      <div className="mb-6 pb-6 border-b border-gray-200">
        <div className="flex justify-between items-start">
          <h1 className="text-3xl font-bold text-gray-900">{auction.item}</h1>
          <span className="text-sm text-gray-500">ID: {auction.id}</span>
        </div>
        <p className="mt-2 text-gray-600">{auction.description || "No description provided."}</p>
        <div className="mt-4 flex items-center space-x-4 text-sm text-gray-500">
          <span>Seller: <span className="font-mono bg-gray-100 px-1 rounded">{auction.seller}</span></span>
        </div>
      </div>

      <div className="bg-slate-50 p-6 rounded-lg border border-slate-200 shadow-sm">
        <div className="flex justify-between items-center mb-8">
          <div>
            <p className="text-sm text-gray-500 uppercase tracking-wide">Current Highest Bid</p>
            <p className="text-4xl font-bold text-blue-600">${auction.highest_bid.toLocaleString()}</p>
            <p className="text-xs text-gray-400 mt-1">Held by: {auction.highest_bidder || "No bids yet"}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500 uppercase tracking-wide">Status</p>
            {isOpen ? (
              <p className={`text-2xl font-mono font-bold ${auction.time_remaining < 60 ? 'text-red-500' : 'text-gray-700'}`}>
                {formatTime(auction.time_remaining)}
              </p>
            ) : (
              <p className="text-2xl font-bold text-red-600">CLOSED</p>
            )}
          </div>
        </div>

        {/* Bidding Interface */}
        <form onSubmit={handleSubmit} className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {isOpen ? "Place your bid" : "This auction has ended"}
          </label>
          <div className="flex gap-4">
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
              <input
                type="number"
                min={minBid}
                value={bidAmount}
                onChange={(e) => setBidAmount(e.target.value)}
                placeholder={isOpen ? `Min offer: $${minBid}` : "Bidding closed"}
                disabled={!isOpen}
                className="w-full pl-8 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none disabled:bg-gray-100 disabled:text-gray-400"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading || !isOpen}
              className={`px-8 py-3 bg-blue-600 text-white font-bold rounded-lg transition shadow-lg
                ${(loading || !isOpen) ? 'opacity-50 cursor-not-allowed bg-gray-500 shadow-none' : 'hover:bg-blue-700 hover:shadow-xl'}`}
            >
              {loading ? 'Processing...' : (isOpen ? 'Place Bid' : 'Closed')}
            </button>
          </div>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </form>
      </div>
    </div>
  );
};

const AuthModal = ({ isOpen, onClose, onLogin, api }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const endpoint = isRegister ? '/register' : '/login';

    try {
      const passwordHash = CryptoJS.SHA256(password).toString();

      await api.post(endpoint, { username, password: passwordHash });

      if (isRegister) {
        await api.post('/login', { username, password: passwordHash });
      }

      onLogin({ username });
      onClose();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-8 rounded-lg shadow-xl w-96 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"><X size={20} /></button>
        <h2 className="text-2xl font-bold mb-4">{isRegister ? 'Register' : 'Login'}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full p-2 border rounded"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full p-2 border rounded"
              required
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
            {isRegister ? 'Sign Up' : 'Sign In'}
          </button>
        </form>
        <p className="mt-4 text-sm text-center">
          {isRegister ? "Already have an account? " : "Don't have an account? "}
          <button onClick={() => setIsRegister(!isRegister)} className="text-blue-600 hover:underline">
            {isRegister ? 'Login' : 'Register'}
          </button>
        </p>
      </div>
    </div>
  );
};

const CreateAuctionModal = ({ isOpen, onClose, user, onCreate }) => {
  const [item, setItem] = useState('');
  const [description, setDescription] = useState('');
  const [minPrice, setMinPrice] = useState('');
  const [duration, setDuration] = useState('60');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await onCreate({
        item,
        description,
        min_price: Number(minPrice),
        time_remaining: Number(duration),
        seller: user.username
      });
      onClose();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-8 rounded-lg shadow-xl w-96 relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"><X size={20} /></button>
        <h2 className="text-2xl font-bold mb-4">Create Auction</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Item Name</label>
            <input type="text" value={item} onChange={e => setItem(e.target.value)} className="w-full p-2 border rounded" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} className="w-full p-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Min Price ($)</label>
            <input type="number" value={minPrice} onChange={e => setMinPrice(e.target.value)} className="w-full p-2 border rounded" required min="1" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Duration (seconds)</label>
            <input type="number" value={duration} onChange={e => setDuration(e.target.value)} className="w-full p-2 border rounded" required min="10" />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" className="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700">Create Auction</button>
        </form>
      </div>
    </div>
  );
};

const AccountModal = ({ isOpen, onClose, user, auctions }) => {
  if (!isOpen || !user) return null;

  const myAuctions = auctions.filter(a => a.seller === user.username);
  const winningAuctions = auctions.filter(a => a.highest_bidder === user.username && a.status === 'open');
  const wonAuctions = auctions.filter(a => a.highest_bidder === user.username && a.status === 'closed');

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-8 rounded-lg shadow-xl w-[600px] max-h-[80vh] overflow-y-auto relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"><X size={20} /></button>
        <h2 className="text-2xl font-bold mb-6">My Account: {user.username}</h2>

        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">My Active Auctions ({myAuctions.length})</h3>
            <div className="bg-gray-50 p-4 rounded border">
              {myAuctions.length === 0 ? <p className="text-gray-500 text-sm">No active auctions.</p> : (
                <ul className="space-y-2">
                  {myAuctions.map(a => (
                    <li key={a.id} className="flex justify-between text-sm">
                      <span>{a.item}</span>
                      <span className="font-mono">${a.highest_bid}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Winning ({winningAuctions.length})</h3>
            <div className="bg-blue-50 p-4 rounded border border-blue-100">
              {winningAuctions.length === 0 ? <p className="text-gray-500 text-sm">You are not winning any auctions.</p> : (
                <ul className="space-y-2">
                  {winningAuctions.map(a => (
                    <li key={a.id} className="flex justify-between text-sm">
                      <span>{a.item}</span>
                      <span className="font-bold text-blue-600">${a.highest_bid}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Won Auctions ({wonAuctions.length})</h3>
            <div className="bg-green-50 p-4 rounded border border-green-100">
              {wonAuctions.length === 0 ? <p className="text-gray-500 text-sm">You haven't won any auctions yet.</p> : (
                <ul className="space-y-2">
                  {wonAuctions.map(a => (
                    <li key={a.id} className="flex justify-between text-sm">
                      <span>{a.item}</span>
                      <span className="font-bold text-green-600">${a.highest_bid}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

// MAIN APP
export default function AuctionPlatform() {
  const [auctions, setAuctions] = useState([]);
  const [selectedAuctionId, setSelectedAuctionId] = useState(null);
  const [user, setUser] = useState(null);
  const [showAuth, setShowAuth] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showAccount, setShowAccount] = useState(false);
  const [session, setSession] = useState(null);
  const ws = useRef(null);

  useEffect(() => {
    const initSession = async () => {
      try {
        //Server Public Key
        const res = await fetch(`${API_URL}/public-key`);
        const { key: publicKey } = await res.json();

        //Generate AES Key
        const aesKey = generateAESKey();

        //Encrypt AES Key with RSA
        const aesKeyB64 = CryptoJS.enc.Base64.stringify(aesKey);
        const encryptedKey = encryptRSA(aesKeyB64, publicKey);

        if (!encryptedKey) throw new Error("RSA Encryption failed");

        //Handshake
        const hsRes = await fetch(`${API_URL}/handshake`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ encrypted_key: encryptedKey })
        });

        if (!hsRes.ok) throw new Error("Handshake failed");
        const { session_id } = await hsRes.json();

        console.log("Secure Session Established:", session_id);
        setSession({ id: session_id, key: aesKey });

      } catch (err) {
        console.error("Security Init Failed:", err);
        alert("Failed to establish secure connection. Please reload.");
      }
    };

    initSession();
  }, []);

  const api = React.useMemo(() => session ? createApiClient(session) : null, [session]);

  const fetchAuctions = async () => {
    if (!api) return;
    try {
      const data = await api.get('/auctions');
      setAuctions(data);
    } catch (err) {
      console.error("Failed to fetch auctions:", err);
    }
  };

  useEffect(() => {
    if (session) {
      fetchAuctions();
    }
  }, [session]);

  useEffect(() => {
    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => {
      console.log("WS Connected");
    };

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      console.log("WS Message:", message);

      if (message.event === 'NEW_BID') {
        setAuctions(prev => prev.map(a => {
          if (a.id === message.id) {
            return { ...a, highest_bid: message.amount, highest_bidder: message.bidder };
          }
          return a;
        }));
      } else if (message.event === 'END') {
        setAuctions(prev => prev.map(a => {
          if (a.id === message.id) {
            return { ...a, status: 'closed', time_remaining: 0 };
          }
          return a;
        }));
      } else if (message.event === 'CREAT') {
        if (api) fetchAuctions();
      }
    };

    ws.current.onclose = () => console.log("WS Disconnected");

    // Timer
    const timer = setInterval(() => {
      setAuctions(prev => prev.map(a => {
        if (a.status !== 'open') return a;
        const newTime = Math.max(0, a.time_remaining - 1);
        const newStatus = newTime === 0 ? 'closed' : a.status;
        return { ...a, time_remaining: newTime, status: newStatus };
      }));
    }, 1000);

    return () => {
      if (ws.current) ws.current.close();
      clearInterval(timer);
    };
  }, [api]);

  const handlePlaceBid = async (auctionId, amount) => {
    if (!api) return;
    await api.post('/bid', {
      id: auctionId,
      bidder: user.username,
      amount: amount
    });
  };

  const handleCreateAuction = async (auctionData) => {
    if (!api) return;
    const id = `auc_${Date.now()}`;
    await api.post('/auction', {
      id,
      ...auctionData
    });
    fetchAuctions();
  };

  const sortedAuctions = [...auctions].sort((a, b) => {
    if (a.status === 'open' && b.status !== 'open') return -1;
    if (a.status !== 'open' && b.status === 'open') return 1;
    return 0;
  });

  const selectedAuction = auctions.find(a => a.id === selectedAuctionId);

  if (!session) {
    return <div className="h-screen flex items-center justify-center">Initializing Secure Session...</div>;
  }

  return (
    <div className="h-screen flex flex-col bg-white">
      <Navbar
        user={user}
        onLoginClick={() => setShowAuth(true)}
        onLogout={() => setUser(null)}
        onCreateClick={() => setShowCreate(true)}
        onAccountClick={() => setShowAccount(true)}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel */}
        <div className="w-1/3 min-w-[350px] overflow-y-auto border-r border-gray-200 bg-white">
          <div className="p-4 bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <h2 className="text-lg font-bold text-gray-700">Active Auctions</h2>
            <p className="text-sm text-gray-500">{auctions.filter(a => a.status === 'open').length} items currently open</p>
          </div>
          <div className="divide-y divide-gray-100">
            {sortedAuctions.map(auction => (
              <AuctionCard
                key={auction.id}
                auction={auction}
                isSelected={selectedAuctionId === auction.id}
                onClick={(a) => setSelectedAuctionId(a.id)}
              />
            ))}
            {sortedAuctions.length === 0 && (
              <div className="p-4 text-center text-gray-500">No auctions available</div>
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div className="flex-1 overflow-y-auto bg-white relative">
          <AuctionDetail
            auction={selectedAuction}
            onPlaceBid={handlePlaceBid}
            user={user}
          />
        </div>
      </div>

      <AuthModal
        isOpen={showAuth}
        onClose={() => setShowAuth(false)}
        onLogin={(u) => { setUser(u); setShowAuth(false); }}
        api={api}
      />

      <CreateAuctionModal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        user={user}
        onCreate={handleCreateAuction}
      />

      <AccountModal
        isOpen={showAccount}
        onClose={() => setShowAccount(false)}
        user={user}
        auctions={auctions}
      />
    </div>
  );
}
