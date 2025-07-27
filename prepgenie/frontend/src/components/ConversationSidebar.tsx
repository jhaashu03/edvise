import React, { useState, useEffect } from 'react';
import { 
  ChatBubbleLeftIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  ArchiveBoxIcon,
  BookmarkIcon,
  CalendarIcon,
  TagIcon,
  EllipsisVerticalIcon,
  TrashIcon,
  DocumentArrowDownIcon,
  PencilIcon
} from '@heroicons/react/24/outline';
import { 
  ChatBubbleLeftIcon as ChatBubbleLeftSolidIcon,
  BookmarkIcon as BookmarkSolidIcon 
} from '@heroicons/react/24/solid';
import { apiService } from '../services/api';

interface Conversation {
  id: string;
  uuid: string;
  title: string;
  topic?: string;
  summary?: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  is_pinned: boolean;
  tags?: string;
  first_message_preview?: string;
  last_message_time?: string;
}

interface ConversationStats {
  active_conversations: number;
  archived_conversations: number;
  total_messages: number;
  conversations_this_week: number;
  most_active_topics: Array<{topic: string, count: number}>;
}

interface ConversationSidebarProps {
  currentConversationId?: string;
  onConversationSelect: (conversationId: string) => void;
  onNewConversation: () => void;
  onConversationCreated?: () => void;
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  currentConversationId,
  onConversationSelect,
  onNewConversation
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [stats, setStats] = useState<ConversationStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'active' | 'archived'>('active');
  const [loading, setLoading] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [showContextMenu, setShowContextMenu] = useState<string | null>(null);

  // Auto-close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showContextMenu) {
        setShowContextMenu(null);
      }
    };

    if (showContextMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showContextMenu]);

  // Load conversations on component mount and when tab changes
  useEffect(() => {
    loadConversations();
    loadStats();
  }, [activeTab]);

  const loadConversations = async () => {
    try {
      setLoading(true);
      console.log('🔄 Loading conversations...');
      
      const response = await apiService.getConversations({
        status: activeTab,
        page: 1,
        per_page: 50
      });
      
      setConversations(response.conversations);
      console.log(`📜 Loaded ${response.conversations.length} conversations`);
    } catch (error) {
      console.error('❌ Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const statsData = await apiService.getConversationStats();
      setStats(statsData);
    } catch (error) {
      console.error('❌ Failed to load stats:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadConversations();
      return;
    }

    try {
      setLoading(true);
      const response = await apiService.searchConversations({
        query: searchQuery,
        status: activeTab
      });
      setConversations(response.conversations);
    } catch (error) {
      console.error('❌ Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConversationAction = async (action: string, conversationId: string) => {
    try {
      switch (action) {
        case 'archive':
          await apiService.archiveConversation(conversationId);
          loadConversations();
          break;
        case 'delete':
          if (window.confirm('Are you sure you want to delete this conversation?')) {
            await apiService.deleteConversation(conversationId);
            loadConversations();
          }
          break;
        case 'pin':
          const conversation = conversations.find(c => c.uuid === conversationId);
          if (conversation) {
            await apiService.updateConversation(conversationId, {
              is_pinned: !conversation.is_pinned
            });
            loadConversations();
          }
          break;
        case 'export':
          const exportData = await apiService.exportConversation(conversationId, 'json');
          const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `conversation_${conversationId}.json`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          break;
      }
    } catch (error) {
      console.error(`❌ Failed to ${action} conversation:`, error);
    }
    setShowContextMenu(null);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffHours = diffTime / (1000 * 60 * 60);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    // For recent messages (within 24 hours), show time in IST
    if (diffHours < 24) {
      return date.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    }

    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays - 1} days ago`;
    return date.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata' });
  };

  const getTopicColor = (topic?: string) => {
    if (!topic) return 'bg-gray-100 text-gray-600';
    
    const colors: Record<string, string> = {
      'Polity': 'bg-blue-100 text-blue-600',
      'History': 'bg-amber-100 text-amber-600',
      'Geography': 'bg-green-100 text-green-600',
      'Economics': 'bg-purple-100 text-purple-600',
      'Current Affairs': 'bg-red-100 text-red-600',
      'Environment': 'bg-emerald-100 text-emerald-600',
      'Science Tech': 'bg-indigo-100 text-indigo-600',
      'Ethics': 'bg-pink-100 text-pink-600'
    };
    
    return colors[topic] || 'bg-gray-100 text-gray-600';
  };

  return (
    <div className="w-80 bg-white border-r border-slate-200 flex flex-col h-full m-0 p-0">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-white">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl shadow-sm">
              <ChatBubbleLeftSolidIcon className="h-5 w-5 text-white" />
            </div>
            <h2 className="text-xl font-bold bg-gradient-to-r from-slate-700 to-slate-900 bg-clip-text text-transparent">Conversations</h2>
          </div>
          <button
            onClick={onNewConversation}
            className="group relative p-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 hover:scale-105"
            title="Start New Conversation"
          >
            <PlusIcon className="h-5 w-5 transition-transform group-hover:rotate-90" />
            <div className="absolute inset-0 bg-white/20 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>
          </button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 gap-3 mb-4 text-xs">
            <div 
              className="bg-blue-50 p-3 rounded-lg border border-blue-100 cursor-help transition-all hover:bg-blue-100" 
              title="Active conversations are ongoing chats that haven't been archived. These are your current discussion threads."
            >
              <div className="font-bold text-blue-900 text-lg">{stats.active_conversations}</div>
              <div className="text-blue-600 font-medium">Active Chats</div>
            </div>
            <div 
              className="bg-gray-50 p-3 rounded-lg border border-gray-100 cursor-help transition-all hover:bg-gray-100" 
              title="Total messages sent and received across all your conversations, including both your questions and AI responses."
            >
              <div className="font-bold text-gray-900 text-lg">{stats.total_messages}</div>
              <div className="text-gray-600 font-medium">All Messages</div>
            </div>
          </div>
        )}

        {/* Search Bar */}
        <div className="relative mb-6">
          <MagnifyingGlassIcon className="h-4 w-4 absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="w-full pl-11 pr-4 py-3 bg-slate-50/50 border border-slate-200/60 rounded-xl text-sm text-slate-700 placeholder-slate-400 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/40 focus:bg-white transition-all duration-200 shadow-sm focus:shadow-md"
          />
        </div>

        {/* Tabs */}
        <div className="flex bg-slate-100/60 p-1 rounded-xl mb-2">
          <button
            onClick={() => setActiveTab('active')}
            className={`flex-1 py-2.5 px-4 text-sm font-medium rounded-lg transition-all duration-200 ${
              activeTab === 'active'
                ? 'bg-white text-slate-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-600 hover:bg-white/50'
            }`}
          >
            Active
          </button>
          <button
            onClick={() => setActiveTab('archived')}
            className={`flex-1 py-2.5 px-4 text-sm font-medium rounded-lg transition-all duration-200 ${
              activeTab === 'archived'
                ? 'bg-white text-slate-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-600 hover:bg-white/50'
            }`}
          >
            Archived
          </button>
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-gray-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <div className="mt-2">Loading conversations...</div>
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <ChatBubbleLeftIcon className="h-12 w-12 mx-auto mb-2 text-gray-300" />
            <div>No conversations found</div>
            <div className="text-sm mt-1">Start a new conversation to get started</div>
          </div>
        ) : (
          <div className="px-3 py-2 space-y-2">
            {conversations.map((conversation) => (
              <div
                key={conversation.uuid}
                className={`relative group p-4 rounded-xl cursor-pointer transition-all duration-200 border ${
                  currentConversationId === conversation.uuid
                    ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200/60 shadow-md transform scale-[1.02]'
                    : 'hover:bg-white/70 border-transparent hover:border-slate-200/40 hover:shadow-sm hover:transform hover:scale-[1.01]'
                }`}
                onClick={() => onConversationSelect(conversation.uuid)}
              >
                {/* Pinned indicator */}
                {conversation.is_pinned && (
                  <div className="absolute top-3 right-3 bg-gradient-to-r from-yellow-400 to-orange-500 p-1.5 rounded-full shadow-sm">
                    <BookmarkSolidIcon className="h-3 w-3 text-white" />
                  </div>
                )}

                {/* Context menu button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowContextMenu(showContextMenu === conversation.uuid ? null : conversation.uuid);
                  }}
                  className="absolute top-3 right-10 opacity-0 group-hover:opacity-100 p-1.5 hover:bg-slate-200/60 rounded-lg transition-all duration-200"
                >
                  <EllipsisVerticalIcon className="h-4 w-4 text-slate-400" />
                </button>

                {/* Context menu */}
                {showContextMenu === conversation.uuid && (
                  <div className="absolute right-2 top-10 bg-white border border-slate-200 rounded-lg shadow-lg z-50 py-2 min-w-[140px] animate-in slide-in-from-top-2 duration-200">
                    <button
                      onClick={() => handleConversationAction('pin', conversation.uuid)}
                      className="w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center transition-all duration-150 rounded-md mx-1"
                    >
                      <BookmarkIcon className="h-4 w-4 mr-3 text-slate-400" />
                      {conversation.is_pinned ? 'Unpin' : 'Pin'}
                    </button>
                    <button
                      onClick={() => handleConversationAction('export', conversation.uuid)}
                      className="w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center transition-all duration-150 rounded-md mx-1"
                    >
                      <DocumentArrowDownIcon className="h-4 w-4 mr-3 text-slate-400" />
                      Export
                    </button>
                    <button
                      onClick={() => handleConversationAction('archive', conversation.uuid)}
                      className="w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center transition-all duration-150 rounded-md mx-1"
                    >
                      <ArchiveBoxIcon className="h-4 w-4 mr-3 text-slate-400" />
                      Archive
                    </button>
                    <div className="border-t border-slate-200 my-2"></div>
                    <button
                      onClick={() => handleConversationAction('delete', conversation.uuid)}
                      className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center transition-all duration-150 rounded-md mx-1"
                    >
                      <TrashIcon className="h-4 w-4 mr-3 text-red-500" />
                      Delete
                    </button>
                  </div>
                )}

                {/* Conversation content */}
                <div className="pr-12">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-slate-800 truncate text-base leading-tight">
                        {conversation.title}
                      </h3>
                    </div>
                    
                    {conversation.topic && (
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium shadow-sm ${getTopicColor(conversation.topic)}`}>
                        <div className="w-1.5 h-1.5 rounded-full bg-current opacity-60 mr-1.5"></div>
                        {conversation.topic}
                      </span>
                    )}

                    {conversation.first_message_preview && (
                      <p className="text-sm text-slate-600 leading-relaxed line-clamp-2">
                        {conversation.first_message_preview}
                      </p>
                    )}

                    <div className="flex items-center justify-between pt-1">
                      <div className="flex items-center space-x-3 text-xs text-slate-400">
                        <span className="flex items-center bg-slate-100/60 px-2 py-1 rounded-full">
                          <ChatBubbleLeftIcon className="h-3 w-3 mr-1" />
                          {conversation.message_count}
                        </span>
                        <span className="flex items-center">
                          <CalendarIcon className="h-3 w-3 mr-1" />
                          {formatDate(conversation.updated_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Most Active Topics */}
      {stats && stats.most_active_topics.length > 0 && (
        <div className="p-4 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Popular Topics</h3>
          <div className="space-y-1">
            {stats.most_active_topics.slice(0, 3).map((topicStat, index) => (
              <div key={index} className="flex items-center justify-between text-xs">
                <span className={`px-2 py-1 rounded-full ${getTopicColor(topicStat.topic)}`}>
                  {topicStat.topic}
                </span>
                <span className="text-gray-500">{topicStat.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ConversationSidebar;
