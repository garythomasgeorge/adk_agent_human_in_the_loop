import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, CheckCircle, XCircle, AlertCircle, User, Send, Clock, Shield, Activity, Search, Menu, Bell, History, X } from 'lucide-react';

function App() {
  const [activeChats, setActiveChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [messages, setMessages] = useState({});
  const [ws, setWs] = useState(null);
  const [clientId] = useState(`agent-${Math.random().toString(36).substr(2, 9)}`);
  const [approvalRequests, setApprovalRequests] = useState({});
  const [view, setView] = useState('active'); // 'active' or 'history'
  const [historySessions, setHistorySessions] = useState([]);
  const [historyDetail, setHistoryDetail] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, selectedChatId, historyDetail]);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? 'localhost:8080' : window.location.host;
    const socket = new WebSocket(`${protocol}//${host}/ws/${clientId}/agent`);

    socket.onopen = () => console.log('Agent Connected');
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'message') {
        const chatClientId = data.clientId;
        setActiveChats(prev => !prev.includes(chatClientId) ? [...prev, chatClientId] : prev);
        setMessages(prev => ({
          ...prev,
          [chatClientId]: [...(prev[chatClientId] || []), { sender: data.sender, content: data.content, timestamp: data.timestamp || new Date().toLocaleTimeString() }]
        }));
      } else if (data.type === 'approval_request') {
        const chatClientId = data.clientId;
        setApprovalRequests(prev => ({
          ...prev,
          [chatClientId]: { amount: data.amount, reason: data.reason }
        }));
        setActiveChats(prev => !prev.includes(chatClientId) ? [...prev, chatClientId] : prev);
      } else if (data.type === 'sync_state') {
        setActiveChats(data.active_chats);
        setMessages(data.messages);

        // Map approvals to simpler format if needed, or just use as is
        const approvals = {};
        Object.keys(data.approvals).forEach(key => {
          approvals[key] = {
            amount: data.approvals[key].amount,
            reason: data.approvals[key].reason
          };
        });
        setApprovalRequests(approvals);
      } else if (data.type === 'session_ended') {
        const chatClientId = data.clientId;
        setActiveChats(prev => prev.filter(id => id !== chatClientId));
        if (selectedChatId === chatClientId) setSelectedChatId(null);
        // Refresh history if open
        if (view === 'history') fetchHistory();
      }
    };
    setWs(socket);
    return () => socket.close();
  }, [clientId, selectedChatId, view]);

  const handleApproval = (approved, targetClientId) => {
    if (!ws) return;
    ws.send(JSON.stringify({ type: 'approval_response', targetClientId, approved }));
    setApprovalRequests(prev => {
      const newState = { ...prev };
      delete newState[targetClientId];
      return newState;
    });
  };

  const handleTakeover = (e) => {
    e.preventDefault();
    const input = e.target.elements.message.value;
    if (!input.trim() || !selectedChatId || !ws) return;
    ws.send(JSON.stringify({ type: 'takeover_message', targetClientId: selectedChatId, content: input }));
    setMessages(prev => ({
      ...prev,
      [selectedChatId]: [...(prev[selectedChatId] || []), { sender: 'agent', content: input, timestamp: new Date().toLocaleTimeString() }]
    }));
    e.target.reset();
  }

  const handleEndSession = () => {
    if (!selectedChatId || !ws) return;
    ws.send(JSON.stringify({ type: 'end_session', targetClientId: selectedChatId }));
    setActiveChats(prev => prev.filter(id => id !== selectedChatId));
    setSelectedChatId(null);
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/history');
      const data = await res.json();
      setHistorySessions(data);
    } catch (e) {
      console.error("Failed to fetch history", e);
    }
  };

  const fetchHistoryDetail = async (sessionId) => {
    try {
      const res = await fetch(`/api/history/${sessionId}`);
      const data = await res.json();
      setHistoryDetail(data);
    } catch (e) {
      console.error("Failed to fetch history detail", e);
    }
  };

  useEffect(() => {
    if (view === 'history') {
      fetchHistory();
    }
  }, [view]);

  return (
    <div className="flex h-screen bg-[#0F172A] text-slate-200 font-sans overflow-hidden">
      {/* Sidebar */}
      <div className="w-80 bg-[#1E293B] border-r border-slate-700 flex flex-col shadow-xl z-10">
        {/* Header */}
        <div className="h-16 border-b border-slate-700 flex items-center justify-between px-6 bg-[#1E293B]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Shield size={18} className="text-white" />
            </div>
            <span className="font-bold text-white tracking-tight">Zirconia Hub</span>
          </div>
        </div>

        {/* View Toggle */}
        <div className="p-2 grid grid-cols-2 gap-1 border-b border-slate-700">
          <button
            onClick={() => setView('active')}
            className={`py-2 text-xs font-medium rounded-md transition-colors ${view === 'active' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`}
          >
            Active Queue
          </button>
          <button
            onClick={() => setView('history')}
            className={`py-2 text-xs font-medium rounded-md transition-colors ${view === 'history' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`}
          >
            History
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {view === 'active' ? (
            <div className="space-y-0.5 px-2 py-2">
              {activeChats.map(id => (
                <button
                  key={id}
                  onClick={() => setSelectedChatId(id)}
                  className={`w-full text-left p-3 rounded-md flex items-center justify-between group transition-all duration-200 ${selectedChatId === id
                    ? 'bg-blue-600/10 border border-blue-500/50 shadow-sm'
                    : 'hover:bg-slate-800 border border-transparent'
                    }`}
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="relative">
                      <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 font-medium border border-slate-600">
                        {id.substr(0, 2).toUpperCase()}
                      </div>
                      <div className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-[#1E293B] ${approvalRequests[id] ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`}></div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className={`text-sm font-medium truncate ${selectedChatId === id ? 'text-blue-400' : 'text-slate-200 group-hover:text-white'}`}>
                        {id}
                      </div>
                      <div className="text-xs text-slate-500 truncate flex items-center gap-1">
                        {approvalRequests[id] ? (
                          <span className="text-red-400 flex items-center gap-1 font-semibold"><AlertCircle size={10} /> Approval Needed</span>
                        ) : (
                          <span className="flex items-center gap-1"><Activity size={10} /> Active Session</span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
              {activeChats.length === 0 && (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-3 text-slate-600">
                    <MessageSquare size={24} />
                  </div>
                  <p className="text-slate-500 text-sm">No active sessions</p>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-0.5 px-2 py-2">
              {historySessions.map(session => (
                <button
                  key={session.id}
                  onClick={() => fetchHistoryDetail(session.id)}
                  className={`w-full text-left p-3 rounded-md flex items-center justify-between group transition-all duration-200 ${historyDetail?.id === session.id
                    ? 'bg-blue-600/10 border border-blue-500/50 shadow-sm'
                    : 'hover:bg-slate-800 border border-transparent'
                    }`}
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 font-medium border border-slate-700">
                      <History size={14} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-300 truncate">{session.client_id}</div>
                      <div className="text-xs text-slate-500">{new Date(session.start_time).toLocaleDateString()}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#0F172A] relative">
        {(view === 'active' && selectedChatId) || (view === 'history' && historyDetail) ? (
          <>
            {/* Chat Header */}
            <header className="h-16 border-b border-slate-800 flex items-center justify-between px-6 bg-[#0F172A]/50 backdrop-blur-sm sticky top-0 z-10">
              <div>
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  {view === 'active' ? selectedChatId : historyDetail.client_id}
                  {view === 'active' && approvalRequests[selectedChatId] && (
                    <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-xs border border-red-500/30 font-medium">
                      Approval Needed
                    </span>
                  )}
                  {view === 'history' && (
                    <span className="bg-slate-700 text-slate-300 px-2 py-0.5 rounded text-xs border border-slate-600">
                      Archived
                    </span>
                  )}
                </h2>
              </div>
              {view === 'active' && (
                <button
                  onClick={handleEndSession}
                  className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs rounded border border-red-500/30 transition-colors flex items-center gap-2"
                >
                  <XCircle size={14} /> End Session
                </button>
              )}
            </header>

            <div className="flex-1 flex overflow-hidden relative">
              {/* Chat Area */}
              <div className="flex-1 flex flex-col relative">
                <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
                  {((view === 'active' ? messages[selectedChatId] : historyDetail?.messages) || []).map((msg, idx) => {
                    if (msg.sender === 'system') {
                      return (
                        <div key={idx} className="flex justify-center my-4">
                          <span className="text-xs font-medium text-slate-500 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50">
                            {msg.content}
                          </span>
                        </div>
                      );
                    }
                    return (
                      <div key={idx} className={`flex ${msg.sender === 'agent' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[70%] group relative ${msg.sender === 'agent' ? 'items-end' : 'items-start'} flex flex-col`}>
                          <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${msg.sender === 'agent'
                              ? 'bg-blue-600 text-white rounded-br-sm'
                              : msg.sender === 'bot'
                                ? 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-sm'
                                : 'bg-slate-700 text-white rounded-bl-sm'
                            }`}>
                            {msg.content}
                          </div>
                          <div className="flex items-center gap-2 mt-1 px-1">
                            <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">{msg.sender}</span>
                            <span className="text-[10px] text-slate-600">{msg.timestamp || 'Just now'}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input Area (Only for Active) */}
                {view === 'active' && (
                  <div className="p-4 border-t border-slate-800 bg-[#0F172A]">
                    <form onSubmit={handleTakeover} className="flex gap-3 max-w-4xl mx-auto">
                      <div className="flex-1 relative">
                        <input
                          name="message"
                          placeholder="Type a message to intervene..."
                          className="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-4 pr-12 py-3 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-slate-200 placeholder-slate-500 transition-all"
                        />
                        <button type="submit" className="absolute right-2 top-2 p-1.5 bg-blue-600 hover:bg-blue-500 rounded-md text-white transition-colors shadow-lg shadow-blue-500/20">
                          <Send size={16} />
                        </button>
                      </div>
                    </form>
                  </div>
                )}
              </div>

              {/* Approval Modal Overlay */}
              {view === 'active' && approvalRequests[selectedChatId] && (
                <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                  <div className="bg-[#1E293B] border border-slate-700 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
                    <div className="p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center text-red-500">
                          <AlertCircle size={24} />
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-white">Approval Required</h3>
                          <p className="text-sm text-slate-400">Bot has paused for manual review</p>
                        </div>
                      </div>

                      <div className="space-y-4 mb-6">
                        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Request</div>
                          <div className="text-white font-medium">Billing Credit</div>
                          <div className="text-2xl font-bold text-white mt-1">${approvalRequests[selectedChatId].amount.toFixed(2)}</div>
                        </div>

                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Reason</div>
                          <p className="text-slate-300 text-sm leading-relaxed">
                            {approvalRequests[selectedChatId].reason}
                          </p>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <button
                          onClick={() => handleApproval(false, selectedChatId)}
                          className="py-2.5 px-4 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition-colors"
                        >
                          Decline
                        </button>
                        <button
                          onClick={() => handleApproval(true, selectedChatId)}
                          className="py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium shadow-lg shadow-blue-500/20 transition-colors"
                        >
                          Approve
                        </button>
                      </div>
                      <div className="mt-3 pt-3 border-t border-slate-700 text-center">
                        <p className="text-xs text-slate-500 mb-2">Or take control manually</p>
                        <button
                          onClick={() => {
                            // Just close modal to allow typing
                            setApprovalRequests(prev => {
                              const newState = { ...prev };
                              delete newState[selectedChatId];
                              return newState;
                            });
                          }}
                          className="text-sm text-blue-400 hover:text-blue-300 font-medium"
                        >
                          Take Over Chat
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-600 bg-[#0F172A]">
            <div className="w-24 h-24 bg-slate-800/50 rounded-full flex items-center justify-center mb-6 animate-pulse">
              <Activity size={48} className="text-slate-700" />
            </div>
            <h2 className="text-xl font-semibold text-slate-400 mb-2">Ready for Operations</h2>
            <p className="text-slate-500 max-w-xs text-center">Select an active session or view history.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
