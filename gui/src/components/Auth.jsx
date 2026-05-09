import React, { useState } from 'react';
import { supabase } from '../lib/supabase';
import { motion } from 'framer-motion';

export default function Auth() {
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isSignUp) {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: name } }
        });
        if (error) throw error;
        alert('Check your email for the login link!');
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (error) {
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen p-4 bg-transparent">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md p-8 glass-effect rounded-3xl"
      >
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 mb-4 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
            <span className="text-3xl font-bold text-white">B</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            {isSignUp ? 'Join BAIT' : 'Welcome Back'}
          </h1>
          <p className="text-sm text-gray-400 mt-2">
            Experience the future of personal automation.
          </p>
        </div>

        <form onSubmit={handleAuth} className="space-y-4">
          {isSignUp && (
            <div>
              <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">Name</label>
              <input
                type="text"
                placeholder="Tony Stark"
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-white"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">Email</label>
            <input
              type="email"
              placeholder="boss@bait.ai"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-white"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">Password</label>
            <input
              type="password"
              placeholder="••••••••"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-white"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-blue-500/25 active:scale-95 transition-all"
          >
            {loading ? 'Processing...' : isSignUp ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsSignUp(!isSignUp)}
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
