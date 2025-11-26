import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Sparkles, XCircle, Clock } from 'lucide-react';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [ws, setWs] = useState(null);
  const [clientId] = useState(`customer-${Math.random().toString(36).substr(2, 9)}`);
  const [isAgentConnected, setIsAgentConnected] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? 'localhost:8080' : window.location.host;
    const socket = new WebSocket(`${protocol}//${host}/ws/${clientId}/customer`);

    socket.onopen = () => {
      console.log('Connected');
      // Initial greeting
      setMessages([{
        sender: 'bot',
        content: 'Hello! I am your virtual assistant. How can I help you today?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.sender === 'agent' || (data.sender === 'system' && data.content.includes('Agent has joined'))) {
        setIsAgentConnected(true);
      }
      setMessages(prev => [...prev, {
        sender: data.sender,
        content: data.content,
        timestamp: data.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    };

    setWs(socket);

    return () => socket.close();
  }, [clientId]);

  const sendMessage = (e) => {
    e.preventDefault();
    if (!input.trim() || !ws) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    ws.send(JSON.stringify({ content: input, timestamp }));
    setMessages(prev => [...prev, { sender: 'customer', content: input, timestamp }]);
    setInput('');
  };

  const handleEndChat = () => {
    if (!ws) return;
    ws.send(JSON.stringify({ type: 'end_session', targetClientId: clientId }));
    setMessages(prev => [...prev, {
      sender: 'system',
      content: 'Chat ended.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
    setIsAgentConnected(false);
    // Optional: Disable input or show restart button
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-10 shadow-sm">
        <div className="w-[60%] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="text-blue-600" size={24} />
            <h1 className="text-xl font-bold text-slate-800 tracking-tight">Nebula Assistant</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-500 hidden sm:inline">Always here to help</span>
            {isAgentConnected && (
              <button
                onClick={handleEndChat}
                className="flex items-center gap-2 px-3 py-1.5 bg-red-50 text-red-600 hover:bg-red-100 rounded-full text-sm font-medium transition-colors border border-red-200"
              >
                <XCircle size={16} /> End Chat
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent">
        <div className="w-[60%] mx-auto space-y-6">
          {messages.map((msg, idx) => {
            // System Message
            if (msg.sender === 'system') {
              return (
                <div key={idx} className="flex justify-center my-4">
                  <span className="text-xs font-medium text-slate-400 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                    {msg.content}
                  </span>
                </div>
              );
            }

            // Chat Message
            const isCustomer = msg.sender === 'customer';
            const isAgent = msg.sender === 'agent';
            const isBot = msg.sender === 'bot';

            return (
              <div key={idx} className={`flex ${isCustomer ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex flex-col max-w-[80%] sm:max-w-[70%] ${isCustomer ? 'items-end' : 'items-start'}`}>

                  {/* Sender Name (Optional, good for Agent) */}
                  {!isCustomer && (
                    <span className="text-xs text-slate-400 mb-1 ml-1">
                      {isAgent ? 'Agent' : 'Virtual Assistant'}
                    </span>
                  )}

                  <div className={`px-5 py-3.5 text-[15px] leading-relaxed shadow-sm relative group ${isCustomer
                    ? 'bg-blue-600 text-white rounded-2xl rounded-tr-sm'
                    : isAgent
                      ? 'bg-purple-600 text-white rounded-2xl rounded-tl-sm' // Agent Style
                      : 'bg-white text-slate-700 border border-slate-200 rounded-2xl rounded-tl-sm' // Bot Style
                    }`}>
                    {msg.content}
                  </div>

                  {/* Timestamp */}
                  <div className={`mt-1 flex items-center gap-1 text-[10px] text-slate-400 ${isCustomer ? 'mr-1' : 'ml-1'}`}>
                    <span>{msg.timestamp}</span>
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-slate-200 p-4 sm:p-6">
        <div className="w-[60%] mx-auto">
          <form onSubmit={sendMessage} className="relative flex items-center gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                className="w-full bg-slate-50 border border-slate-200 text-slate-800 rounded-xl pl-5 pr-12 py-4 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all shadow-sm placeholder-slate-400"
              />
              <button
                type="submit"
                disabled={!input.trim()}
                className="absolute right-2 top-2 p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg transition-all shadow-md shadow-blue-500/20"
              >
                <Send size={20} />
              </button>
            </div>
          </form>
          <div className="text-center mt-3">
            <p className="text-xs text-slate-400">
              Powered by <span className="font-semibold text-blue-600">Zirconia AI</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
