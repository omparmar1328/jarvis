import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageSquare, 
  Mic, 
  Settings, 
  LogOut, 
  Plus, 
  Search, 
  Command,
  ChevronRight,
  Battery,
  Wifi
} from 'lucide-react';

export default function Dashboard({ user }) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [input, setInput] = useState('');

  // Logout function
  const handleLogout = () => supabase.auth.signOut();

  const sendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim()) return;

    const userMsg = { role: 'user', content: input, timestamp: new Date().toLocaleTimeString() };
    setMessages([...messages, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, user_id: user.id }),
      });
      const data = await response.json();
      
      const baitMsg = { role: 'bait', content: data.reply, timestamp: new Date().toLocaleTimeString() };
      setMessages(prev => [...prev, baitMsg]);
      
      // Save to Supabase (History) - Wrap in try to avoid crash during bypass
      try {
        await supabase.from('chats').insert([
          { user_id: user.id, message: input, response: data.reply }
        ]);
      } catch (err) {
        console.warn("Supabase save skipped (Bypass Mode)");
      }

    } catch (error) {
      console.error("Failed to reach BAIT Brain:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const [eventSource, setEventSource] = useState(null);

  const toggleVoice = () => {
    if (isVoiceActive) {
      // Stop Always-on
      if (eventSource) {
        eventSource.close();
        setEventSource(null);
      }
      fetch('http://localhost:8000/voice/stop', { method: 'POST' });
      setIsVoiceActive(false);
    } else {
      // Start Always-on
      setIsVoiceActive(true);
      const es = new EventSource('http://localhost:8000/voice/stream');
      
      es.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.user_text) {
          const userMsg = { role: 'user', content: data.user_text, timestamp: new Date().toLocaleTimeString() };
          const baitMsg = { role: 'bait', content: data.reply, timestamp: new Date().toLocaleTimeString() };
          setMessages(prev => [...prev, userMsg, baitMsg]);
        }
      };

      es.onerror = (err) => {
        console.error("Voice Stream Error:", err);
        es.close();
        setIsVoiceActive(false);
      };

      setEventSource(es);
    }
  };

  const handleInterrupt = async () => {
    await fetch('http://localhost:8000/stop', { method: 'POST' });
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') handleInterrupt();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="flex h-screen bg-transparent text-white overflow-hidden">
      
      {/* SIDEBAR */}
      <aside className="w-72 glass-effect m-4 mr-2 rounded-3xl flex flex-col">
        <div className="p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center font-bold">B</div>
            <span className="font-bold text-lg tracking-tight">BAIT</span>
          </div>
          <button className="p-2 hover:bg-white/10 rounded-xl transition-colors">
            <Plus size={18} />
          </button>
        </div>

        <div className="px-4 mb-4">
          <button className="w-full py-3 px-4 bg-white/10 hover:bg-white/15 rounded-2xl flex items-center gap-3 transition-all text-sm font-medium">
            <Plus size={16} /> New Chat
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto scrollbar-hide px-2 space-y-1">
          {['Project Alpha Strategy', 'Market Research Data', 'Code Optimization Tips'].map((chat, i) => (
            <button key={i} className="w-full p-3 hover:bg-white/5 rounded-2xl flex items-center gap-3 group transition-all text-left">
              <MessageSquare size={16} className="text-gray-500 group-hover:text-blue-400" />
              <div className="truncate flex-1">
                <p className="text-sm font-medium truncate">{chat}</p>
                <p className="text-[10px] text-gray-500 uppercase tracking-tighter">Recently</p>
              </div>
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-white/5">
          <button onClick={handleLogout} className="w-full p-3 hover:bg-red-500/10 rounded-2xl flex items-center gap-3 text-gray-400 hover:text-red-400 transition-all text-sm">
            <LogOut size={16} /> Sign Out
          </button>
        </div>
      </aside>

      {/* MAIN CHAT AREA */}
      <main className="flex-1 glass-effect m-4 ml-2 rounded-3xl flex flex-col overflow-hidden relative">
        
        {/* HEADER */}
        <header className="p-6 flex items-center justify-between border-b border-white/5">
          <div>
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Active Intelligence</h2>
            <p className="text-lg font-semibold">New Conversation</p>
          </div>
          <div className="flex items-center gap-4 text-gray-500">
            <Battery size={18} />
            <Wifi size={18} />
            <div className="w-8 h-8 bg-white/10 rounded-full flex items-center justify-center overflow-hidden border border-white/10 shadow-lg">
               <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.email}`} alt="avatar" />
            </div>
          </div>
        </header>

        {/* MESSAGES */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start gap-4'}`}>
              {msg.role === 'bait' && (
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-xs shadow-lg shadow-blue-500/20">B</div>
              )}
              <div className={`max-w-[80%] p-4 rounded-2xl ${
                msg.role === 'user' 
                ? 'bg-white/10 rounded-tr-none' 
                : 'bg-blue-600/20 border border-blue-500/30 rounded-tl-none shadow-xl'
              }`}>
                <p className={`text-sm ${msg.role === 'user' ? 'text-white/90' : 'text-blue-50'}`}>{msg.content}</p>
                <p className="text-[10px] text-gray-500 mt-2 text-right">{msg.timestamp}</p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start gap-4 animate-pulse">
              <div className="w-8 h-8 bg-white/10 rounded-lg"></div>
              <div className="w-48 h-12 bg-white/5 rounded-2xl"></div>
            </div>
          )}
        </div>

        {/* INPUT AREA */}
        <footer className="p-6 pt-0">
          <form onSubmit={sendMessage} className="relative group">
            <div className="absolute inset-0 bg-blue-500/20 blur-xl opacity-0 group-focus-within:opacity-100 transition-opacity rounded-full"></div>
            <div className="relative flex items-center gap-3 p-2 bg-white/5 border border-white/10 rounded-full focus-within:border-blue-500/50 transition-all backdrop-blur-md">
              <button type="button" className="p-2 hover:bg-white/10 rounded-full text-gray-400 transition-colors">
                <Plus size={20} />
              </button>
              <input 
                type="text" 
                placeholder="Message BAIT..."
                className="flex-1 bg-transparent border-none outline-none text-sm py-2 px-1"
                value={input}
                onChange={(e) => setInput(e.target.value)}
              />
              
                <motion.button 
                  type="button"
                  onClick={toggleVoice}
                  animate={{ 
                    scale: isVoiceActive ? [1, 1.1, 1] : 1,
                  }}
                  transition={{ 
                    repeat: isVoiceActive ? Infinity : 0, 
                    duration: 1 
                  }}
                  className={`p-3 rounded-full transition-all shadow-lg ${
                    isVoiceActive 
                    ? 'bg-red-500 text-white shadow-red-500/40' 
                    : 'bg-blue-600 text-white shadow-blue-500/40 hover:scale-105 active:scale-95'
                  }`}
                >
                  <Mic size={20} />
                </motion.button>
            </div>
          </form>
          <div className="mt-4 flex justify-center">
             <p className="text-[10px] text-gray-500 uppercase tracking-[0.2em] font-medium">Press <kbd className="bg-white/10 px-1.5 py-0.5 rounded border border-white/10">ESC</kbd> to interrupt BAIT</p>
          </div>
        </footer>

      </main>
    </div>
  );
}
