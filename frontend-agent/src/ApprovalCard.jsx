import React from 'react';
import { AlertCircle, CheckCircle, XCircle, MessageSquare, DollarSign, Truck } from 'lucide-react';

const ApprovalCard = ({ type, data, onApprove, onDecline, onTakeover }) => {
    const isCredit = type === 'credit' || (data && data.amount !== undefined && data.amount > 0);
    const isDispatch = type === 'dispatch' || (data && data.amount === 0);

    return (
        <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-[#1E293B] border border-slate-700 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden animate-in fade-in zoom-in duration-200">
                <div className="p-6">
                    <div className="flex items-center gap-3 mb-4">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isCredit ? 'bg-green-500/20 text-green-500' : 'bg-blue-500/20 text-blue-500'}`}>
                            {isCredit ? <DollarSign size={24} /> : <Truck size={24} />}
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white">
                                {isCredit ? 'Credit Approval Required' : 'Dispatch Approval Required'}
                            </h3>
                            <p className="text-sm text-slate-400">Bot has paused for manual review</p>
                        </div>
                    </div>

                    <div className="space-y-4 mb-6">
                        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Request Details</div>
                            {isCredit ? (
                                <div className="flex items-baseline gap-1">
                                    <span className="text-2xl font-bold text-white">${Number(data.amount).toFixed(2)}</span>
                                    <span className="text-slate-400 text-sm">credit</span>
                                </div>
                            ) : (
                                <div className="text-white font-medium text-lg">Technician Dispatch</div>
                            )}
                        </div>

                        <div>
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Reason</div>
                            <p className="text-slate-300 text-sm leading-relaxed bg-slate-800/30 p-3 rounded border border-slate-700/50">
                                {data.reason || "No reason provided"}
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 mb-4">
                        <button
                            onClick={onDecline}
                            className="flex items-center justify-center gap-2 py-3 px-4 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-medium transition-all hover:shadow-lg"
                        >
                            <XCircle size={18} />
                            Decline
                        </button>
                        <button
                            onClick={onApprove}
                            className="flex items-center justify-center gap-2 py-3 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium shadow-lg shadow-blue-500/20 transition-all hover:shadow-blue-500/30 hover:-translate-y-0.5"
                        >
                            <CheckCircle size={18} />
                            Approve
                        </button>
                    </div>

                    <div className="pt-4 border-t border-slate-700 text-center">
                        <button
                            onClick={onTakeover}
                            className="text-sm text-slate-400 hover:text-white font-medium flex items-center justify-center gap-2 mx-auto transition-colors group"
                        >
                            <MessageSquare size={14} className="group-hover:text-blue-400 transition-colors" />
                            Take over chat manually
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ApprovalCard;
