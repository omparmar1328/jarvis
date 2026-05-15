import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { supabase } from '../lib/supabase';
import { 
  MessageSquare, 
  Mic, 
  LogOut, 
  Plus, 
  Battery,
  Wifi,
  Send,
  Sparkles,
  Command
} from 'lucide-react';

export default function Dashboard({ user }) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [input, setInput] = useState('');
  const [eventSource, setEventSource] = useState(null);
  const [history, setHistory] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  const [batteryLevel, setBatteryLevel] = useState('100');
  const [tokens, setTokens] = useState({ 
    groq: {prompt:0, completion:0}, 
    gemini: {prompt:0, completion:0},
    openrouter: {prompt:0, completion:0} 
  });
  const [showTokens, setShowTokens] = useState(false);
  const scrollRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const [isConnected, setIsConnected] = useState(false);

  const loadHistory = async (retries = 5) => {
    try {
      const res = await fetch('http://127.0.0.1:8000/chats');
      if (!res.ok) throw new Error("Server not ready");
      const data = await res.json();
      const historyData = Array.isArray(data) ? data : [];
      setHistory(historyData);
      setIsConnected(true);
    } catch (err) {
      // Keep console clean by only logging real errors, not initial connection attempts
      if (isConnected) console.error("Failed to load history:", err);
      setIsConnected(false);
      if (retries > 0) {
        setTimeout(() => loadHistory(retries - 1), 2000); // Retry after 2s
      }
      setHistory([]);
    }
  };

  const fetchBattery = async () => {
    if (!isConnected) return;
    try {
      const res = await fetch('http://127.0.0.1:8000/system/battery');
      if (!res.ok) return;
      const data = await res.json();
      setBatteryLevel(data.percentage);
    } catch (err) {}
  };

  const fetchTokens = async () => {
    if (!isConnected) return;
    try {
      const res = await fetch('http://127.0.0.1:8000/tokens');
      if (!res.ok) return;
      const data = await res.json();
      setTokens(data);
    } catch (err) {}
  };

  useEffect(() => {
    loadHistory();
    fetchBattery();
    fetchTokens();
    const batteryInterval = setInterval(fetchBattery, 60000); 
    const reconnectInterval = setInterval(() => {
      if (!isConnected) loadHistory();
    }, 5000); // Check connection every 5s if disconnected

    return () => {
      clearInterval(batteryInterval);
      clearInterval(reconnectInterval);
    };
  }, [isConnected]);

  const deleteConversation = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("Delete this thread, Boss?")) return;
    try {
      await fetch(`http://127.0.0.1:8000/chats/${id}`, { method: 'DELETE' });
      if (currentConvId === id) startNewChat();
      loadHistory();
    } catch (err) {
      console.error("Failed to delete:", err);
    }
  };

  const handleLogout = async () => {
    if (window.confirm("Disconnect from BAIT, Boss?")) {
      await supabase.auth.signOut();
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setCurrentConvId(null);
  };

  const selectConversation = (conv) => {
    if (!conv) return;
    setCurrentConvId(conv.id);
    setMessages(Array.isArray(conv.messages) ? conv.messages : []);
  };

  const sendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;

    const currentInput = input;
    const userMsg = { role: 'user', content: currentInput, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: currentInput,
          conversation_id: currentConvId || null 
        }),
      });

      const data = await response.json();
      
      if (data.conversation_id && !currentConvId) {
        setCurrentConvId(data.conversation_id);
      }

      const baitMsg = { role: 'bait', content: data.reply, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
      setMessages(prev => [...prev, baitMsg]);
      loadHistory();
      fetchTokens();
    } catch (error) {
      console.error("Chat Error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleVoice = () => {
    if (isVoiceActive) {
      if (eventSource) {
        eventSource.close();
        setEventSource(null);
      }
      fetch('http://127.0.0.1:8000/voice/stop', { method: 'POST' });
      setIsVoiceActive(false);
    } else {
      setIsVoiceActive(true);
      const url = `http://127.0.0.1:8000/voice/stream${currentConvId ? `?conversation_id=${currentConvId}` : ''}`;
      const es = new EventSource(url);
      
      es.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.user_text) {
          if (data.conversation_id && !currentConvId) {
            setCurrentConvId(data.conversation_id);
          }
          const userMsg = { role: 'user', content: data.user_text, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
          const baitMsg = { role: 'bait', content: data.reply, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
          setMessages(prev => [...prev, userMsg, baitMsg]);
          loadHistory();
          fetchTokens();
        }
      };
      es.onerror = (err) => {
        es.close();
        setIsVoiceActive(false);
      };
      setEventSource(es);
    }
  };

  const safeHistory = Array.isArray(history) ? history : [];
  const activeConv = safeHistory.find(c => c.id === currentConvId);

  return (
    <div className="flex h-screen bg-transparent text-white overflow-hidden font-sans selection:bg-blue-500/30 relative">
      
      {/* DRAG AREA */}
      <div className="fixed top-0 left-0 right-0 h-8 z-[100]" style={{ WebkitAppRegion: 'drag' }}></div>

      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-5%] left-[-5%] w-[35%] h-[35%] bg-blue-600/10 blur-[100px] rounded-full animate-pulse"></div>
        <div className="absolute bottom-[-5%] right-[-5%] w-[35%] h-[35%] bg-purple-600/10 blur-[100px] rounded-full"></div>
      </div>

      <div className="flex flex-1 z-10 relative p-3 gap-3">
        
        {/* SIDEBAR */}
        <aside className="w-64 glass-effect rounded-3xl flex flex-col border border-white/10 shadow-2xl overflow-hidden backdrop-blur-3xl">
          <div className="p-6">
            <div className="flex items-center gap-2.5 mb-8">
              <div className="w-8 h-8 bg-gradient-to-tr from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center font-black text-base shadow-lg shadow-blue-500/20">B</div>
              <div>
                <span className="font-black text-sm block leading-none tracking-tighter uppercase italic">BAIT</span>
                <span className="text-[8px] text-blue-400 font-black uppercase tracking-[0.3em] opacity-50">v2.5</span>
              </div>
            </div>
            
            <button onClick={startNewChat} className="w-full py-3 px-4 bg-white/5 hover:bg-white/10 rounded-xl flex items-center justify-between transition-all border border-white/5 text-[10px] font-black uppercase tracking-widest group">
              <span>New Thread</span>
              <Plus size={14} className="text-blue-400 group-hover:rotate-90 transition-transform" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-3 space-y-1 scrollbar-hide">
            <p className="text-[9px] font-black text-gray-500 uppercase tracking-[0.2em] ml-3 mb-2">History</p>
            {safeHistory.slice().reverse().map((conv) => (
              <div key={conv.id} className="relative group">
                <button 
                  onClick={() => selectConversation(conv)}
                  className={`w-full p-3 rounded-xl flex items-center gap-3 transition-all text-left border ${
                    currentConvId === conv.id 
                    ? 'bg-blue-600/15 border-blue-500/20' 
                    : 'bg-transparent border-transparent hover:bg-white/5'
                  }`}
                >
                  <div className={`w-1 h-6 rounded-full transition-all ${currentConvId === conv.id ? 'bg-blue-500 scale-100' : 'bg-transparent scale-0'}`}></div>
                  <div className="truncate flex-1">
                    <p className={`text-[13px] font-bold truncate ${currentConvId === conv.id ? 'text-white' : 'text-gray-400'}`}>
                      {conv.title || "New Chat"}
                    </p>
                  </div>
                </button>
                <button 
                  onClick={(e) => deleteConversation(conv.id, e)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 opacity-0 group-hover:opacity-100 hover:text-red-500 transition-all"
                >
                  <Plus size={14} className="rotate-45" />
                </button>
              </div>
            ))}
          </div>

          <div className="p-4 mt-auto space-y-2">
             <button 
               onClick={handleLogout}
               className="w-full py-3 px-4 bg-red-500/5 hover:bg-red-500/10 rounded-xl flex items-center justify-between transition-all border border-red-500/10 text-[10px] font-black uppercase tracking-widest text-red-400 group"
             >
                <span>Disconnect</span>
                <LogOut size={14} className="group-hover:translate-x-1 transition-transform" />
             </button>

             <div className="bg-black/20 rounded-2xl p-3 border border-white/5 flex items-center gap-2.5">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
                <span className="text-[8px] font-black text-gray-500 uppercase tracking-[0.2em]">Ready</span>
             </div>
          </div>
        </aside>

        {/* MAIN AREA */}
        <main className="flex-1 glass-effect rounded-3xl flex flex-col overflow-hidden relative border border-white/10 shadow-2xl backdrop-blur-3xl">
          
          {/* Neural Link Status Bar */}
          {!isConnected && (
            <div className="absolute top-0 left-0 right-0 bg-red-500/10 border-b border-red-500/20 py-1.5 px-4 z-[150] backdrop-blur-md flex items-center justify-center gap-3">
              <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-ping"></div>
              <span className="text-[10px] font-black uppercase tracking-[0.3em] text-red-400">Neural Link: Reconnecting...</span>
            </div>
          )}

          <header className="px-8 py-5 flex items-center justify-between border-b border-white/5 bg-white/2 backdrop-blur-md">
            <div className="flex items-center gap-4">
               <div className={`p-3 rounded-xl border transition-all ${isVoiceActive ? 'bg-red-500/10 border-red-500/20' : 'bg-blue-500/10 border-blue-500/20'}`}>
                  {isVoiceActive ? <Mic size={18} className="text-red-400" /> : <Command size={18} className="text-blue-400" />}
               </div>
               <div>
                  <div className="flex items-center gap-2 mb-0.5">
                    <h2 className="text-[9px] font-black text-blue-500 uppercase tracking-[0.3em]">Neural Interface</h2>
                    {isConnected && <div className="w-1.5 h-1.5 bg-green-500 rounded-full shadow-[0_0_5px_rgba(34,197,94,0.5)]"></div>}
                  </div>
                  <p className="text-lg font-black tracking-tighter text-white/95 truncate max-w-lg italic uppercase">
                    {currentConvId ? activeConv?.title || 'Session' : 'Standby'}
                  </p>
               </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="relative">
                <button 
                  onClick={() => setShowTokens(!showTokens)}
                  className="flex items-center gap-2 text-gray-400 bg-black/20 py-2 px-4 rounded-2xl border border-white/5 hover:border-blue-500/30 transition-all z-[200]"
                >
                  <Sparkles size={14} className="text-blue-400" />
                  <Plus size={10} className={`transition-transform duration-300 ${showTokens ? 'rotate-180' : ''}`} />
                </button>
                
                <AnimatePresence>
                  {showTokens && (
                    <motion.div 
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      className="absolute top-full mt-2 right-0 w-64 bg-black/90 backdrop-blur-3xl border border-white/10 rounded-2xl p-5 shadow-2xl z-[1000]"
                    >
                      <h4 className="text-[10px] font-black uppercase tracking-widest text-blue-500 mb-4 italic flex items-center justify-between">
                        <span>Token Intelligence</span>
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                      </h4>
                      <div className="space-y-4">
                        {Object.entries(tokens).map(([provider, data]) => (
                          <div key={provider} className="flex flex-col gap-2">
                            <div className="flex justify-between items-end">
                              <span className="text-[9px] font-black uppercase tracking-widest text-gray-500">{provider}</span>
                              <span className="text-[9px] font-bold text-gray-600">{data.prompt + data.completion} total</span>
                            </div>
                            <div className="flex justify-between text-[10px] font-bold">
                              <span className="text-gray-400">P: {data.prompt}</span>
                              <span className="text-blue-400">C: {data.completion}</span>
                            </div>
                            <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                               <motion.div 
                                 initial={{ width: 0 }}
                                 animate={{ width: `${Math.min(100, (data.prompt + data.completion) / 50)}%` }}
                                 className="h-full bg-gradient-to-r from-blue-600 to-indigo-500" 
                               />
                            </div>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="flex items-center gap-6 text-gray-400 bg-black/20 py-2 px-5 rounded-2xl border border-white/5">
                <div className="flex items-center gap-2">
                  <Battery size={14} className={`${parseInt(batteryLevel) < 20 ? 'text-red-500' : 'text-blue-400'}`} />
                  <span className="text-[10px] font-black">{batteryLevel}%</span>
                </div>
                <div className="w-px h-4 bg-white/5"></div>
                <Wifi size={14} className="text-blue-500" />
                <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center overflow-hidden border border-white/10 shadow-inner">
                  <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.email || 'boss'}`} alt="avatar" />
                </div>
              </div>
            </div>
          </header>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-6 scrollbar-hide">
            {messages.length === 0 && !isLoading && (
              <div className="h-full flex flex-col items-center justify-center text-center opacity-40">
                 <Command size={40} className="text-blue-500/30 mb-4" />
                 <h3 className="text-xl font-black text-white/90 tracking-tighter uppercase italic">Ready for Command</h3>
              </div>
            )}
            
            {messages.map((msg, i) => (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                key={i} 
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start gap-4'}`}
              >
                {msg.role === 'bait' && (
                  <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center flex-shrink-0 font-black text-xs shadow-xl border border-white/10">B</div>
                )}
                <div className={`max-w-[70%] p-4 rounded-2xl shadow-xl relative border backdrop-blur-xl ${
                  msg.role === 'user' 
                  ? 'bg-blue-600/15 border-blue-500/20 rounded-tr-none' 
                  : 'bg-white/5 border-white/10 rounded-tl-none'
                }`}>
                  <p className={`text-[14px] leading-relaxed font-bold ${msg.role === 'user' ? 'text-blue-50' : 'text-white/90'}`}>
                    {msg.content}
                  </p>
                  <div className={`flex items-center gap-2 mt-3 opacity-20 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                     <span className="text-[8px] font-black uppercase tracking-widest">{msg.timestamp}</span>
                  </div>
                </div>
              </motion.div>
            ))}
            {isLoading && (
              <div className="flex justify-start gap-4 animate-pulse">
                <div className="w-9 h-9 bg-white/5 rounded-xl"></div>
                <div className="w-48 h-12 bg-white/5 rounded-2xl"></div>
              </div>
            )}
          </div>

          <footer className="p-8 pt-0">
            <form onSubmit={sendMessage} className="relative group max-w-4xl mx-auto">
              <div className="absolute inset-0 bg-blue-500/5 blur-[60px] opacity-0 group-focus-within:opacity-100 transition-all duration-1000"></div>
              <div className="relative flex items-center gap-3 p-3 bg-black/40 border border-white/10 rounded-2xl focus-within:border-blue-500/40 transition-all shadow-xl backdrop-blur-3xl">
                <button type="button" className="p-2.5 hover:bg-white/10 rounded-lg text-gray-500 transition-all hover:text-white">
                  <Plus size={20} />
                </button>
                <input 
                  type="text" 
                  placeholder="Execute Command..."
                  className="flex-1 bg-transparent border-none outline-none text-base py-1.5 px-1 placeholder:text-gray-700 font-bold tracking-tight text-white/90"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                />
                
                <div className="flex items-center gap-2">
                  <motion.button 
                    type="button"
                    onClick={toggleVoice}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    animate={isVoiceActive ? { scale: [1, 1.1, 1] } : {}}
                    className={`p-3 rounded-xl transition-all shadow-xl ${
                      isVoiceActive 
                      ? 'bg-red-500 text-white' 
                      : 'bg-white/5 text-gray-500 hover:text-blue-400 hover:bg-blue-500/10'
                    }`}
                  >
                    <Mic size={18} />
                  </motion.button>

                  <motion.button 
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className={`p-3 rounded-xl transition-all shadow-xl ${
                      input.trim() && !isLoading
                      ? 'bg-blue-600 text-white shadow-blue-500/40' 
                      : 'bg-white/5 text-gray-800'
                    }`}
                  >
                    <Send size={18} />
                  </motion.button>
                </div>
              </div>
            </form>
            <div className="mt-5 flex justify-center items-center gap-4 opacity-20">
               <p className="text-[8px] font-black text-gray-500 uppercase tracking-[0.4em] italic">
                 Neural Link v2.5 Stable
               </p>
            </div>
          </footer>

        </main>
      </div>

      {/* VOICE MODE 2.0 OVERLAY */}
      <AnimatePresence>
        {isVoiceActive && (
          <motion.div 
            initial={{ opacity: 0, backdropFilter: 'blur(0px)' }}
            animate={{ opacity: 1, backdropFilter: 'blur(50px)' }}
            exit={{ opacity: 0, backdropFilter: 'blur(0px)' }}
            className="fixed inset-0 z-[2000] bg-black/60 flex flex-col items-center justify-center p-12 text-center overflow-hidden"
          >
            {/* Background Glow */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
               <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-blue-600/10 blur-[120px] rounded-full animate-pulse"></div>
               <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-purple-600/10 blur-[120px] rounded-full"></div>
            </div>

            <button 
              onClick={toggleVoice}
              className="absolute top-10 right-10 w-14 h-14 bg-white/5 hover:bg-white/10 rounded-full flex items-center justify-center border border-white/10 transition-all group z-[2001]"
            >
              <Plus size={28} className="rotate-45 text-gray-400 group-hover:text-white transition-colors" />
            </button>

            <div className="mb-16 relative z-10">
               <motion.h2 
                 initial={{ opacity: 0, y: -20 }}
                 animate={{ opacity: 1, y: 0 }}
                 className="text-[12px] font-black text-blue-500 uppercase tracking-[0.6em] mb-4 italic"
               >
                 Neural Link Active
               </motion.h2>
               <motion.p 
                 initial={{ opacity: 0 }}
                 animate={{ opacity: 1 }}
                 transition={{ delay: 0.2 }}
                 className="text-4xl font-black italic uppercase tracking-tighter text-white/95"
               >
                 Listening for Command, Boss...
               </motion.p>
            </div>

            {/* THE COOL ANIMATED CIRCLE (VISUALIZER) */}
            <div className="relative w-80 h-80 flex items-center justify-center z-10">
               <motion.div 
                 animate={{ 
                   scale: [1, 1.15, 1],
                   rotate: [0, 120, 240, 360],
                   borderRadius: ["38% 62% 63% 37% / 41% 44% 56% 59%", "62% 38% 37% 63% / 54% 45% 55% 46%", "38% 62% 63% 37% / 41% 44% 56% 59%"]
                 }}
                 transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                 className="absolute inset-0 bg-gradient-to-tr from-blue-600/30 to-purple-600/30 blur-3xl"
               />
               
               <div className="relative w-56 h-56 rounded-full border border-white/10 flex items-center justify-center overflow-hidden bg-black/60 backdrop-blur-3xl shadow-[0_0_100px_rgba(59,130,246,0.1)]">
                  <div className="flex gap-1.5 items-end h-16">
                     {[...Array(12)].map((_, i) => (
                       <motion.div 
                         key={i}
                         animate={{ height: [10, Math.random() * 50 + 15, 10] }}
                         transition={{ duration: 0.4, repeat: Infinity, delay: i * 0.05, ease: "easeInOut" }}
                         className="w-2 bg-gradient-to-t from-blue-600 to-blue-400 rounded-full"
                       />
                     ))}
                  </div>
               </div>

               {/* ORBITAL RINGS */}
               <motion.div 
                 animate={{ rotate: 360 }}
                 transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                 className="absolute inset-[-30px] border border-blue-500/10 rounded-full border-dashed"
               />
               <motion.div 
                 animate={{ rotate: -360 }}
                 transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
                 className="absolute inset-[-60px] border border-white/5 rounded-full"
               />
            </div>

            <div className="mt-24 flex flex-col items-center gap-6 relative z-10">
               <motion.div 
                 animate={{ opacity: [0.4, 1, 0.4] }}
                 transition={{ duration: 2, repeat: Infinity }}
                 className="px-8 py-3 bg-blue-500/5 border border-blue-500/10 rounded-full flex items-center gap-4 shadow-lg shadow-blue-500/5"
               >
                  <div className="w-2.5 h-2.5 bg-blue-500 rounded-full shadow-[0_0_100px_rgba(59,130,246,0.5)]"></div>
                  <span className="text-[11px] font-black uppercase tracking-[0.2em] text-blue-400">Live Listening Engaged</span>
               </motion.div>
               <p className="text-gray-600 text-[11px] font-bold uppercase tracking-[0.3em] max-w-sm leading-relaxed opacity-60">
                  Speak clearly, Boss. I'm processing every syllable. Click the [X] to return to text interface.
               </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
