import React, { useState, useEffect, useRef } from 'react';
import { apiService } from '../services/api';
import { ChatMessage } from '../types';
import { 
  PaperAirplaneIcon, 
  UserIcon, 
  SparklesIcon,
  BoltIcon,
  BookOpenIcon,
  GlobeAltIcon,
  LightBulbIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-scroll when loading state changes
  useEffect(() => {
    if (loading) {
      setTimeout(scrollToBottom, 100);
    }
  }, [loading]);

  useEffect(() => {
    // Check for PYQ context from navigation
    const pyqContext = sessionStorage.getItem('pyq_context');
    if (pyqContext) {
      try {
        const context = JSON.parse(pyqContext);
        if (context.mode === 'details') {
          setNewMessage(`Please explain this UPSC question in detail:\n\n${context.details}`);
        } else if (context.mode === 'practice') {
          setNewMessage(context.prompt);
        }
        // Clear the context so it doesn't persist on refresh
        sessionStorage.removeItem('pyq_context');
      } catch (error) {
        console.error('Error parsing PYQ context:', error);
      }
    }
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: newMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setNewMessage('');
    setLoading(true);

    try {
      const response = await apiService.sendChatMessage(newMessage);
      setMessages((prev) => [...prev, response]);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Add error message
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    {
      question: "Explain the Doctrine of Basic Structure with examples",
      icon: BookOpenIcon,
      category: "Constitution"
    },
    {
      question: "What are the key committees for environmental policy?",
      icon: GlobeAltIcon,
      category: "Environment"
    },
    {
      question: "Discuss the role of SHGs in women empowerment",
      icon: AcademicCapIcon,
      category: "Social Issues"
    },
    {
      question: "Explain the concept of Cooperative Federalism",
      icon: LightBulbIcon,
      category: "Polity"
    },
    {
      question: "What is the significance of 73rd Constitutional Amendment?",
      icon: BookOpenIcon,
      category: "Constitution"
    },
  ];

  return (
    <div className="flex flex-col h-screen">
      {/* Fixed Header */}
      <div className="flex-shrink-0 bg-white/80 backdrop-blur-xl border-b border-gray-200/50 shadow-sm">
        <div className="px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-10 h-10 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center shadow-lg">
                <SparklesIcon className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-ai-900 via-primary-700 to-secondary-700 bg-clip-text text-transparent">
                  AI Chat Assistant
                </h1>
                <div className="flex items-center space-x-2 text-sm">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span className="text-ai-600 font-medium">Online</span>
                </div>
              </div>
            </div>
            
            {/* Status indicator on desktop */}
            <div className="hidden sm:flex items-center space-x-2 text-sm text-ai-500">
              <BoltIcon className="w-4 h-4" />
              <span>Powered by advanced AI</span>
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable Messages Container */}
      <div className="flex-1 min-h-0 overflow-hidden relative bg-gradient-to-br from-ai-50 via-white to-primary-50">
        <div className="h-full overflow-y-auto" ref={messagesContainerRef}>
          <div className="px-4 sm:px-6 lg:px-8 py-6">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center min-h-full">
                <div className="text-center max-w-2xl mx-auto px-4">
                  <div className="relative mb-8">
                    <div className="w-20 h-20 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-2xl flex items-center justify-center mx-auto shadow-xl">
                      <SparklesIcon className="h-10 w-10 text-white" />
                    </div>
                    <div className="absolute -top-1 -right-1 w-6 h-6 bg-accent-400 rounded-full animate-pulse"></div>
                    <div className="absolute -bottom-1 -left-1 w-4 h-4 bg-green-400 rounded-full animate-bounce"></div>
                  </div>
                  
                  <h3 className="text-xl sm:text-2xl font-bold text-ai-900 mb-4">
                    Start Your AI-Powered Learning Journey
                  </h3>
                  <p className="text-ai-600 mb-8 text-sm sm:text-base">
                    Ask me anything about UPSC preparation, current affairs, or specific topics. I'm here to help you succeed!
                  </p>
                  
                  <div className="space-y-4">
                    <p className="text-sm font-semibold text-ai-700 flex items-center justify-center">
                      <BoltIcon className="w-4 h-4 mr-2" />
                      Try these AI-powered questions:
                    </p>
                    <div className="grid gap-3">
                      {suggestedQuestions.map((item, index) => (
                        <button
                          key={index}
                          onClick={() => setNewMessage(item.question)}
                          className="group flex items-center p-3 sm:p-4 bg-white/70 backdrop-blur-sm hover:bg-white/90 rounded-xl text-left transition-all duration-200 transform hover:scale-[1.02] shadow-lg hover:shadow-xl border border-white/20"
                        >
                          <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center mr-3 sm:mr-4 group-hover:scale-110 transition-transform flex-shrink-0">
                            <item.icon className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-ai-900 truncate">{item.question}</div>
                            <div className="text-xs text-ai-500 mt-1">{item.category}</div>
                          </div>
                          <SparklesIcon className="w-4 h-4 sm:w-5 sm:h-5 text-primary-500 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-6 pb-4">
                {messages.map((message, index) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    style={{ animationDelay: `${index * 0.1}s` }}
                  >
                    <div
                      className={`flex space-x-3 max-w-3xl ${
                        message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                      }`}
                    >
                      <div
                        className={`w-8 h-8 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shadow-lg flex-shrink-0 ${
                          message.role === 'user'
                            ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white'
                            : 'bg-gradient-to-r from-accent-400 to-accent-500 text-white'
                        }`}
                      >
                        {message.role === 'user' ? (
                          <UserIcon className="w-4 h-4 sm:w-5 sm:h-5" />
                        ) : (
                          <SparklesIcon className="w-4 h-4 sm:w-5 sm:h-5" />
                        )}
                      </div>
                      <div
                        className={`px-4 py-3 sm:px-6 sm:py-4 rounded-2xl shadow-lg backdrop-blur-sm border max-w-full ${
                          message.role === 'user'
                            ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white border-primary-300/50'
                            : 'bg-white/70 text-ai-900 border-white/20'
                        }`}
                      >
                        <div className="prose prose-sm max-w-none break-words">
                          {message.role === 'user' ? (
                            <p className="whitespace-pre-wrap leading-relaxed text-sm sm:text-base m-0 text-white">{message.content}</p>
                          ) : (
                            <div className="markdown-content">
                              <ReactMarkdown 
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  p: ({children}) => <p className="mb-3 last:mb-0 leading-relaxed text-sm sm:text-base">{children}</p>,
                                  h1: ({children}) => <h1 className="text-lg font-bold mb-3 text-ai-900">{children}</h1>,
                                  h2: ({children}) => <h2 className="text-base font-bold mb-2 text-ai-900">{children}</h2>,
                                  h3: ({children}) => <h3 className="text-sm font-bold mb-2 text-ai-900">{children}</h3>,
                                  strong: ({children}) => <strong className="font-black text-ai-900" style={{fontWeight: 800}}>{children}</strong>,
                                  b: ({children}) => <b className="font-black text-ai-900" style={{fontWeight: 800}}>{children}</b>,
                                  em: ({children}) => <em className="italic text-ai-800">{children}</em>,
                                  ul: ({children}) => <ul className="list-disc pl-4 mb-3 space-y-1">{children}</ul>,
                                  ol: ({children}) => <ol className="list-decimal pl-4 mb-3 space-y-1">{children}</ol>,
                                  li: ({children}) => <li className="leading-relaxed">{children}</li>,
                                  blockquote: ({children}) => <blockquote className="border-l-4 border-primary-300 pl-4 py-2 bg-primary-50/50 rounded-r mb-3 italic">{children}</blockquote>,
                                  code: ({children}) => <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                                  pre: ({children}) => <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto mb-3 text-xs">{children}</pre>,
                                  a: ({children, href}) => <a href={href} className="text-primary-600 hover:text-primary-700 underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                                }}
                              >
                                {message.content}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                        <div className={`text-xs mt-2 flex items-center ${
                          message.role === 'user' ? 'text-white/70' : 'text-ai-500'
                        }`}>
                          {message.role === 'assistant' && (
                            <SparklesIcon className="w-3 h-3 mr-1" />
                          )}
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="flex space-x-3 max-w-3xl">
                      <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-r from-accent-400 to-accent-500 text-white flex items-center justify-center shadow-lg">
                        <SparklesIcon className="w-4 h-4 sm:w-5 sm:h-5 animate-pulse" />
                      </div>
                      <div className="px-4 py-3 sm:px-6 sm:py-4 rounded-2xl bg-white/70 backdrop-blur-sm shadow-lg border border-white/20">
                        <div className="flex items-center space-x-2">
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce"></div>
                            <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                            <div className="w-2 h-2 bg-accent-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                          </div>
                          <span className="text-sm text-ai-600 font-medium">AI is thinking...</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Fixed Input Area */}
      <div className="flex-shrink-0 bg-white/80 backdrop-blur-xl border-t border-gray-200/50">
        <div className="px-4 sm:px-6 lg:px-8 py-4">
          <form onSubmit={handleSendMessage} className="flex space-x-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Ask about UPSC topics, current affairs, or study strategies..."
                className="block w-full px-4 py-3 sm:px-6 sm:py-4 pr-10 sm:pr-12 border border-gray-200/50 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white/50 backdrop-blur-sm placeholder-ai-400 text-ai-900 shadow-lg transition-all duration-200 text-sm sm:text-base"
                disabled={loading}
              />
              <div className="absolute right-3 sm:right-4 top-1/2 transform -translate-y-1/2">
                <SparklesIcon className="w-4 h-4 sm:w-5 sm:h-5 text-ai-400" />
              </div>
            </div>
            <button
              type="submit"
              disabled={!newMessage.trim() || loading}
              className="inline-flex items-center justify-center px-4 py-3 sm:px-6 sm:py-4 border border-transparent text-sm font-semibold rounded-2xl shadow-lg text-white bg-gradient-to-r from-primary-500 to-secondary-500 hover:from-primary-600 hover:to-secondary-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-4 w-4 sm:h-5 sm:w-5 border-b-2 border-white"></div>
              ) : (
                <PaperAirplaneIcon className="w-4 h-4 sm:w-5 sm:h-5" />
              )}
            </button>
          </form>
          
          <div className="mt-2 text-center">
            <p className="text-xs text-ai-500 flex items-center justify-center">
              <BoltIcon className="w-3 h-3 mr-1" />
              Powered by advanced AI • Always fact-check important information
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
