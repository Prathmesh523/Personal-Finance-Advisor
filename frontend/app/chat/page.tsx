// app/chat/page.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Send, Sparkles, TrendingUp, ShoppingCart, DollarSign, Loader2, Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { TransactionModal } from '@/components/TransactionModal';

interface Message {
  role: 'user' | 'bot';
  content: string;
  data?: any[];
  show_table?: boolean;
  timestamp: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalData, setModalData] = useState<any[]>([]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const suggestedQuestions = [
    { text: 'How much did I spend on food?', icon: ShoppingCart, gradient: 'from-orange-500 to-red-500' },
    { text: 'Show me my grocery transactions', icon: ShoppingCart, gradient: 'from-green-500 to-emerald-500' },
    { text: 'What are my biggest expenses?', icon: TrendingUp, gradient: 'from-purple-500 to-pink-500' },
    { text: 'List transactions above ₹5000', icon: DollarSign, gradient: 'from-blue-500 to-cyan-500' },
  ];

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/chat?question=${encodeURIComponent(input)}&user_id=1`,
        { method: 'POST' }
      );

      if (!response.ok) throw new Error('Failed to get response');

      const data = await response.json();

      const botMessage: Message = {
        role: 'bot',
        content: data.answer,
        data: data.data,
        show_table: data.show_table,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'bot',
        content: "Sorry, I couldn't process that question. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestedClick = (question: string) => {
    setInput(question);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-8 flex items-center justify-center">
        <div className="w-full max-w-4xl h-full max-h-[calc(100vh-4rem)] flex flex-col">

        {/* Chat Container */}
        <Card className="flex-1 bg-white/80 backdrop-blur-sm border-white/20 shadow-2xl rounded-3xl overflow-hidden flex flex-col">
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              /* Empty State */
              <div className="flex flex-col items-center justify-center h-full space-y-6">
                <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center animate-pulse">
                  <Bot className="w-10 h-10 text-white" />
                </div>
                <div className="text-center space-y-2">
                  <h3 className="text-xl font-semibold text-gray-900">
                    👋 Hi! I'm your financial assistant
                  </h3>
                  <p className="text-gray-600 max-w-md">
                    Ask me questions about your spending, transactions, or get insights into your finances
                  </p>
                </div>

                {/* Suggested Questions */}
                <div className="w-full max-w-2xl mt-8">
                  <p className="text-sm font-medium text-gray-700 mb-4 text-center">Try asking:</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {suggestedQuestions.map((q, idx) => {
                      const Icon = q.icon;
                      return (
                        <button
                          key={idx}
                          onClick={() => handleSuggestedClick(q.text)}
                          className="group relative overflow-hidden bg-white hover:bg-gray-50 border-2 border-gray-200 hover:border-blue-400 rounded-2xl p-4 text-left transition-all duration-300 hover:shadow-lg hover:scale-105"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 bg-gradient-to-br ${q.gradient} rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform`}>
                              <Icon className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900">
                              {q.text}
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : (
              /* Messages */
              <>
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} animate-in slide-in-from-bottom-4 duration-500`}
                  >
                    {/* Avatar */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      msg.role === 'user' 
                        ? 'bg-gradient-to-br from-blue-500 to-blue-600' 
                        : 'bg-gradient-to-br from-purple-500 to-pink-500'
                    }`}>
                      {msg.role === 'user' ? (
                        <User className="w-5 h-5 text-white" />
                      ) : (
                        <Bot className="w-5 h-5 text-white" />
                      )}
                    </div>

                    {/* Message Bubble */}
                    <div className={`flex flex-col max-w-[75%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                      <div
                        className={`rounded-2xl px-4 py-3 shadow-md ${
                          msg.role === 'user'
                            ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-tr-sm'
                            : 'bg-white border border-gray-200 text-gray-900 rounded-tl-sm'
                        }`}
                      >
                        {msg.role === 'bot' ? (
                            <div className="prose prose-sm max-w-none prose-strong:font-bold prose-ul:my-2">
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>
                        ) : (
                            <p className="text-sm leading-relaxed whitespace-pre-line">{msg.content}</p>
                        )}
                        
                        {/* View Details Button */}
                        {msg.show_table && msg.data && msg.data.length > 0 && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="mt-3 bg-blue-600 hover:bg-blue-700 text-white border-none shadow-md"
                            onClick={() => {
                              setModalData(msg.data || []);
                              setModalOpen(true);
                            }}
                          >
                            View {msg.data.length} Transactions →
                          </Button>
                        )}
                      </div>
                      <span className="text-xs text-gray-500 mt-1 px-2">
                        {formatTime(msg.timestamp)}
                      </span>
                    </div>
                  </div>
                ))}

                {/* Typing Indicator */}
                {loading && (
                  <div className="flex gap-3 animate-in slide-in-from-bottom-4 duration-500">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-md">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 bg-white/50 backdrop-blur-sm p-4">
            <div className="flex gap-3">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about your finances..."
                disabled={loading}
                className="flex-1 bg-white border-2 border-gray-200 focus:border-blue-400 rounded-xl px-4 py-3 text-sm shadow-sm transition-all"
              />
              <Button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-xl px-6 shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Press Enter to send • Shift+Enter for new line
            </p>
          </div>
        </Card>

        {/* Footer Note */}
        <p className="text-center text-xs text-gray-500 mt-4">
          Powered by AI • Your data is processed securely
        </p>

        {/* Transaction Modal */}
        <TransactionModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          transactions={modalData}
        />
      </div>
    </div>
  );
}