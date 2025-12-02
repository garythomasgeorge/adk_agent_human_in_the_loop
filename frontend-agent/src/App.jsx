import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, CheckCircle, XCircle, AlertCircle, User, Send, Clock, Shield, Activity, Search, Menu, Bell, History, X, ShieldCheck, Eye, MessageCircle } from 'lucide-react';
import ApprovalCard from './ApprovalCard';

function App() {
  const [activeChats, setActiveChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [messages, setMessages] = useState({});
  const [ws, setWs] = useState(null);
  const [clientId] = useState(`agent-${Math.random().toString(36).substr(2, 9)}`);
  const [approvalRequests, setApprovalRequests] = useState({});
  const [sessionMetadata, setSessionMetadata] = useState({});
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
        setMessages(prev => ({
          ...prev,
          [chatClientId]: [...(prev[chatClientId] || []), { sender: data.sender, content: data.content, timestamp: data.timestamp || new Date().toLocaleTimeString() }]
        }));

        // Update last activity in metadata
        setSessionMetadata(prev => ({
          ...prev,
          [chatClientId]: {
            ...prev[chatClientId],
            last_activity: new Date().toISOString()
          }
        }));
      } else if (data.type === 'approval_request') {
        const chatClientId = data.clientId;
        setApprovalRequests(prev => ({
          ...prev,
          [chatClientId]: { amount: data.amount, reason: data.reason, type: data.amount > 0 ? 'credit' : 'dispatch' }
        }));
        // Update metadata to hard handoff
        setSessionMetadata(prev => ({
          ...prev,
          [chatClientId]: {
            ...prev[chatClientId],
            status: 'hard_handoff',
            requires_approval: true
          }
        }));
      } else if (data.type === 'soft_handoff') {
        const chatClientId = data.clientId;
        setSessionMetadata(prev => ({
          ...prev,
          [chatClientId]: {
            ...prev[chatClientId],
            status: 'soft_handoff',
            sentiment_score: data.sentimentScore,
            reason: data.reason
          }
        }));
      } else if (data.type === 'hard_handoff') {
        const chatClientId = data.clientId;
        setSessionMetadata(prev => ({
          ...prev,
          [chatClientId]: {
            ...prev[chatClientId],
            status: 'hard_handoff',
            reason: data.reason
          }
        }));
      } else if (data.type === 'sync_state') {
        setMessages(data.messages);
        setSessionMetadata(data.metadata || {});

        // Map approvals
        const approvals = {};
        Object.keys(data.approvals).forEach(key => {
          approvals[key] = {
            amount: data.approvals[key].amount,
            reason: data.approvals[key].reason,
            type: data.approvals[key].amount > 0 ? 'credit' : 'dispatch'
          };
        });
        setApprovalRequests(approvals);
      } else if (data.type === 'session_ended') {
        const chatClientId = data.clientId;
        setSessionMetadata(prev => {
          const newState = { ...prev };
          delete newState[chatClientId];
          return newState;
        });
        if (selectedChatId === chatClientId) setSelectedChatId(null);
        if (view === 'history') fetchHistory();
      }
    };
    setWs(socket);
    return () => socket.close();
  }, [clientId, selectedChatId, view]);

  // Filter active chats based on metadata
  useEffect(() => {
    const filteredChats = Object.keys(sessionMetadata).filter(id => {
      const meta = sessionMetadata[id];
      // Show if: soft_handoff, hard_handoff, agent_active, or requires_approval
      // Hide if: bot_only (unless specifically debugging, but req says hide)
      return meta && (
        meta.status === 'soft_handoff' ||
        meta.status === 'hard_handoff' ||
        meta.status === 'agent_active' ||
        meta.requires_approval
      );
    });
    setActiveChats(filteredChats);
  }, [sessionMetadata]);

  const handleApproval = (approved, targetClientId) => {
    if (!ws) return;
    ws.send(JSON.stringify({ type: 'approval_response', targetClientId, approved }));
    setApprovalRequests(prev => {
      const newState = { ...prev };
      delete newState[targetClientId];
      return newState;
    });
    // Reset status to bot_only if approved/declined (unless agent took over)
    setSessionMetadata(prev => ({
      ...prev,
      [targetClientId]: {
        ...prev[targetClientId],
        status: 'bot_only',
        requires_approval: false
      }
    }));
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

    // Update status to agent_active
    setSessionMetadata(prev => ({
      ...prev,
      [selectedChatId]: {
        ...prev[selectedChatId],
        status: 'agent_active'
      }
    }));

    // Clear approval request if taking over
    if (approvalRequests[selectedChatId]) {
      setApprovalRequests(prev => {
        const newState = { ...prev };
        delete newState[selectedChatId];
        return newState;
      });
    }

    e.target.reset();
  }

  const handleManualTakeover = (chatId) => {
    if (!ws) return;
    // Just update status locally and maybe send a system message?
    setSessionMetadata(prev => ({
      ...prev,
      [chatId]: {
        ...prev[chatId],
        status: 'agent_active'
      }
    }));
    // Clear approval if exists
    if (approvalRequests[chatId]) {
      setApprovalRequests(prev => {
        const newState = { ...prev };
        delete newState[chatId];
        return newState;
      });
    }
  };

  const handleEndSession = () => {
    if (!selectedChatId || !ws) return;
    ws.send(JSON.stringify({ type: 'end_session', targetClientId: selectedChatId }));
    // Optimistic update
    setSessionMetadata(prev => {
      const newState = { ...prev };
      delete newState[selectedChatId];
      return newState;
    });
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
        <header className="bg-slate-800 border-b border-slate-700 px-6 py-4 flex items-center justify-between sticky top-0 z-10 shadow-md">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg">
              <ShieldCheck className="text-white" size={20} />
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">Nebula Agent Hub</h1>
          </div>
        </header>

        {/* View Toggle */}
        <div className="p-2 grid grid-cols-2 gap-1 border-b border-slate-700">
          <button
            onClick={() => setView('active')}
            className={`py-2 text-xs font-medium rounded-md transition-colors ${view === 'active' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`}
          >
            Active Queue
            {activeChats.length > 0 && <span className="ml-2 bg-white/20 px-1.5 rounded-full text-[10px]">{activeChats.length}</span>}
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
              {activeChats.map(id => {
                const meta = sessionMetadata[id] || {};
                const isHardHandoff = meta.status === 'hard_handoff';
                const isSoftHandoff = meta.status === 'soft_handoff';
                const isApproval = approvalRequests[id];

                return (
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
                        <div className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-[#1E293B] ${isHardHandoff || isApproval ? 'bg-red-500 animate-pulse' :
                            isSoftHandoff ? 'bg-orange-500' : 'bg-green-500'
                          }`}></div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className={`text-sm font-medium truncate ${selectedChatId === id ? 'text-blue-400' : 'text-slate-200 group-hover:text-white'}`}>
                          {id}
                        </div>
                        <div className="text-xs text-slate-500 truncate flex items-center gap-1">
                          {isApproval ? (
                            <span className="text-red-400 flex items-center gap-1 font-semibold"><AlertCircle size={10} /> Approval Needed</span>
                          ) : isHardHandoff ? (
                            <span className="text-red-400 flex items-center gap-1 font-semibold"><AlertCircle size={10} /> Action Required</span>
                          ) : isSoftHandoff ? (
                            <span className="text-orange-400 flex items-center gap-1 font-medium"><Eye size={10} /> Monitoring</span>
                          ) : (
                            <span className="flex items-center gap-1"><Activity size={10} /> Active Session</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
              {activeChats.length === 0 && (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-3 text-slate-600">
                    <MessageSquare size={24} />
                  </div>
                  <p className="text-slate-500 text-sm">No sessions requiring attention</p>
                  <p className="text-slate-600 text-xs mt-1">Bot is handling all active chats</p>
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
                  {view === 'active' && (
                    <>
                      {approvalRequests[selectedChatId] && (
                        <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-xs border border-red-500/30 font-medium">
                          Approval Needed
                        </span>
                      )}
                      {sessionMetadata[selectedChatId]?.status === 'soft_handoff' && (
                        <span className="bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded text-xs border border-orange-500/30 font-medium flex items-center gap-1">
                          <Eye size={12} /> Monitoring
                        </span>
                      )}
                    </>
                  )}
                  {view === 'history' && (
                    <span className="bg-slate-700 text-slate-300 px-2 py-0.5 rounded text-xs border border-slate-600">
                      Archived
                    </span>
                  )}
                </h2>
              </div>
              {view === 'active' && (
                <div className="flex items-center gap-2">
                  {sessionMetadata[selectedChatId]?.status === 'soft_handoff' && (
                    <button
                      onClick={() => handleManualTakeover(selectedChatId)}
                      className="px-3 py-1.5 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 text-xs rounded border border-blue-600/30 transition-colors flex items-center gap-2"
                    >
                      <MessageCircle size={14} /> Take Over
                    </button>
                  )}
                  <button
                    onClick={handleEndSession}
                    className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs rounded border border-red-500/30 transition-colors flex items-center gap-2"
                  >
                    <XCircle size={14} /> End Session
                  </button>
                </div>
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
                <ApprovalCard
                  type={approvalRequests[selectedChatId].type}
                  data={approvalRequests[selectedChatId]}
                  onApprove={() => handleApproval(true, selectedChatId)}
                  onDecline={() => handleApproval(false, selectedChatId)}
                  onTakeover={() => handleManualTakeover(selectedChatId)}
                />
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
