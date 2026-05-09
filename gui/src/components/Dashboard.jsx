import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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

export default function Dashboard() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [input, setInput] = useState('');
  const [eventSource, setEventSource] = useState(null);
  const [history, setHistory] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  const scrollRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const loadHistory = async () => {
    try {
      const res = await fetch('http://localhost:8000/chats');
      const data = await res.json();
      const historyData = Array.isArray(data) ? data : [];
      setHistory(historyData);
      
      if (!currentConvId && historyData.length > 0) {
        const last = historyData[historyData.length - 1];
        if (last && last.messages) {
          setCurrentConvId(last.id);
          setMessages(last.messages);
        }
      }
    } catch (err) {
      console.error("Failed to load history:", err);
      setHistory([]);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

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
      const response = await fetch('http://localhost:8000/chat', {
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
      fetch('http://localhost:8000/voice/stop', { method: 'POST' });
      setIsVoiceActive(false);
    } else {
      setIsVoiceActive(true);
      const url = `http://localhost:8000/voice/stream${currentConvId ? `?conversation_id=${currentConvId}` : ''}`;
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
              <button 
                key={conv.id} 
                onClick={() => selectConversation(conv)}
                className={`w-full p-3 rounded-xl flex items-center gap-3 group transition-all text-left border ${
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
            ))}
          </div>

          <div className="p-4 mt-auto">
             <div className="bg-black/20 rounded-2xl p-3 border border-white/5 flex items-center gap-2.5">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
                <span className="text-[8px] font-black text-gray-500 uppercase tracking-[0.2em]">Ready</span>
             </div>
          </div>
        </aside>

        {/* MAIN AREA */}
        <main className="flex-1 glass-effect rounded-3xl flex flex-col overflow-hidden relative border border-white/10 shadow-2xl backdrop-blur-3xl">
          
          <header className="px-8 py-5 flex items-center justify-between border-b border-white/5 bg-white/2 backdrop-blur-md">
            <div className="flex items-center gap-4">
               <div className={`p-3 rounded-xl border transition-all ${isVoiceActive ? 'bg-red-500/10 border-red-500/20' : 'bg-blue-500/10 border-blue-500/20'}`}>
                  {isVoiceActive ? <Mic size={18} className="text-red-400" /> : <Command size={18} className="text-blue-400" />}
               </div>
               <div>
                  <h2 className="text-[9px] font-black text-blue-500 uppercase tracking-[0.3em] mb-0.5">Neural Interface</h2>
                  <p className="text-lg font-black tracking-tighter text-white/95 truncate max-w-lg italic uppercase">
                    {currentConvId ? activeConv?.title || 'Session' : 'Standby'}
                  </p>
               </div>
            </div>
            
            <div className="flex items-center gap-6 text-gray-400 bg-black/20 py-2 px-5 rounded-2xl border border-white/5">
              <div className="flex items-center gap-2">
                 <Battery size={14} className="text-blue-400" />
                 <span className="text-[10px] font-black">100%</span>
              </div>
              <div className="w-px h-4 bg-white/5"></div>
              <Wifi size={14} className="text-blue-500" />
              <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center overflow-hidden border border-white/10">
                 <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=boss`} alt="avatar" />
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
    </div>
  );
}
