import React, { useState, useEffect } from 'react';
import { Bell, User, Gavel, Clock, Search } from 'lucide-react';

// MOCK DATA
const INITIAL_AUCTIONS = [
  {
    id: "auc_001",
    item: "Vintage Rolex Submariner",
    description: "A pristine condition 1978 Submariner. Original parts, box and papers included.",
    seller: "alice_hash",
    highest_bid: 15000,
    highest_bidder: "bob_hash",
    status: "open",
    time_remaining: 10 // Short time to test the feature!
  },
  {
    id: "auc_002",
    item: "Gibson Les Paul 1959",
    description: "Original sunburst finish. Verified by experts.",
    seller: "charlie_hash",
    highest_bid: 250000,
    highest_bidder: "dave_hash",
    status: "open",
    time_remaining: 45
  },
  {
    id: "auc_003",
    item: "SpaceX Starship Model",
    description: "Signed by the engineering team. 1:100 scale.",
    seller: "elon_hash",
    highest_bid: 500,
    highest_bidder: "frank_hash",
    status: "open",
    time_remaining: 3600
  }
];

// COMPONENTS

const Navbar = () => (
  <nav className="bg-slate-900 text-white p-4 shadow-md">
    <div className="w-full px-4 flex justify-between items-center">
      <div className="flex items-center space-x-2 text-xl font-bold cursor-pointer">
        <Gavel className="text-yellow-500" />
        <span>AuctionHouse</span>
      </div>
      <div className="flex items-center space-x-6">
        <a href="#" className="hover:text-yellow-400 transition">Home</a>
        <a href="#" className="hover:text-yellow-400 transition">My Auctions</a>
        <button className="relative hover:text-yellow-400 transition">
          <Bell size={20} />
          <span className="absolute -top-1 -right-1 bg-red-500 rounded-full w-2 h-2"></span>
        </button>
        <div className="flex items-center space-x-4 border-l border-slate-700 pl-6">
          <a href="#" className="text-sm text-gray-300 hover:text-white flex items-center gap-1">
            <User size={16} /> Login
          </a>
          <a href="#" className="bg-yellow-500 text-slate-900 px-4 py-1.5 rounded-md font-medium text-sm hover:bg-yellow-400 transition">
            Sign Up
          </a>
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
        
        {/* Dynamic Badge Color */}
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

const AuctionDetail = ({ auction, onPlaceBid }) => {
  const [bidAmount, setBidAmount] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setBidAmount('');
  }, [auction?.id]);

  if (!auction) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-400">
        <Search size={48} className="mb-4 opacity-50" />
        <p className="text-lg">Select an auction from the left to view details.</p>
      </div>
    );
  }

  const isOpen = auction.status === 'open';
  const minBid = auction.highest_bid + 1;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!isOpen) return;
    setLoading(true);
    setTimeout(() => {
      onPlaceBid(auction.id, Number(bidAmount));
      setLoading(false);
      setBidAmount('');
    }, 600);
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

        {/* Bidding Interface - Disabled if Closed */}
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
        </form>
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
  const [auctions, setAuctions] = useState(INITIAL_AUCTIONS);
  const [selectedAuctionId, setSelectedAuctionId] = useState(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setAuctions(prev => prev.map(a => {
        const newTime = Math.max(0, a.time_remaining - 1);
        
        const newStatus = newTime === 0 ? 'closed' : a.status;

        return {
          ...a,
          time_remaining: newTime,
          status: newStatus
        };
      }));
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const handlePlaceBid = (auctionId, amount) => {
    setAuctions(prev => prev.map(a => {
      if (a.id === auctionId) {
        return { ...a, highest_bid: amount, highest_bidder: "me_hash" };
      }
      return a;
    }));
  };

  const sortedAuctions = [...auctions].sort((a, b) => {
    if (a.status === 'open' && b.status !== 'open') return -1; // a comes first
    if (a.status !== 'open' && b.status === 'open') return 1;  // b comes first
    return 0; // maintain order otherwise
  });

  const selectedAuction = auctions.find(a => a.id === selectedAuctionId);

  return (
    <div className="h-screen flex flex-col bg-white">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        
        {/* Left Pane */}
        <div className="w-1/3 min-w-[350px] overflow-y-auto border-r border-gray-200 bg-white">
          <div className="p-4 bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
            <h2 className="text-lg font-bold text-gray-700">Active Auctions</h2>
            <p className="text-sm text-gray-500">{auctions.filter(a => a.status === 'open').length} items currently open</p>
          </div>
          <div className="divide-y divide-gray-100">
            {/* Render the SORTED list */}
            {sortedAuctions.map(auction => (
              <AuctionCard 
                key={auction.id} 
                auction={auction} 
                isSelected={selectedAuctionId === auction.id}
                onClick={(a) => setSelectedAuctionId(a.id)}
              />
            ))}
          </div>
        </div>

        {/* Right Pane */}
        <div className="flex-1 overflow-y-auto bg-white relative">
          <AuctionDetail 
            auction={selectedAuction} 
            onPlaceBid={handlePlaceBid} 
          />
        </div>
      </div>
    </div>
  );
}
