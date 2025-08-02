import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { PYQSearchResult } from '../types';
import { 
  MagnifyingGlassIcon, 
  FunnelIcon, 
  SparklesIcon, 
  CpuChipIcon,
  BoltIcon,
  DocumentTextIcon,
  CalendarDaysIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline';

const PYQSearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PYQSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    subject: '',
    year: '',
  });
  const [showFilters, setShowFilters] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMoreResults, setHasMoreResults] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  
  // Ref to prevent concurrent search conflicts
  const isAutoSearchingRef = useRef(false);

  const subjects = [
    'General Studies Paper 1',
    'General Studies Paper 2',
    'General Studies Paper 3',
    'General Studies Paper 4',
    'Essay',
    'Optional Subject',
  ];

  const years = Array.from({ length: 10 }, (_, i) => 2024 - i);

  // Auto-search when filters change (only if there's already a query and results)
  useEffect(() => {
    if (query.trim() && results.length > 0 && !isAutoSearchingRef.current) {
      console.log('🔄 Frontend: Filters changed, auto-triggering search...');
      console.log('📊 Frontend: New filters:', filters);
      
      // Use a small debounce to prevent rapid filter changes from causing multiple searches
      const debounceTimer = setTimeout(() => {
        // Trigger new search with current query and new filters
        const performSearch = async () => {
          isAutoSearchingRef.current = true;
          setLoading(true);
          
          try {
            const searchFilters = {
              ...(filters.subject && { subject: filters.subject }),
              ...(filters.year && { year: parseInt(filters.year) }),
              page: 1,
              limit: 10,
            };
            
            console.log('📤 Frontend: Auto-search API request filters:', searchFilters);
            const searchResults = await apiService.searchPYQs(query, searchFilters);
            console.log(`📥 Frontend: Auto-search received ${searchResults.length} results`);
            
            // Always update results for auto-search to ensure consistency
            setResults(searchResults);
            setCurrentPage(1);
            setHasMoreResults(searchResults.length === 10);
            setTotalResults(searchResults.length);
          } catch (error) {
            console.error('Auto-search failed:', error);
          } finally {
            setLoading(false);
            isAutoSearchingRef.current = false;
          }
        };
        
        performSearch();
      }, 200); // Slightly longer debounce for smoother experience
      
      // Cleanup function to cancel pending searches
      return () => {
        clearTimeout(debounceTimer);
        isAutoSearchingRef.current = false;
      };
    }
  }, [filters.subject, filters.year]); // Only trigger on filter changes, not query changes

  const handleSearch = async (page: number = 1) => {
    if (!query.trim()) return;

    setLoading(true);
    console.log(`🔍 Frontend: Searching page ${page} for query: "${query}"`);
    
    try {
      const searchFilters = {
        ...(filters.subject && { subject: filters.subject }),
        ...(filters.year && { year: parseInt(filters.year) }),
        page,
        limit: 10,
      };

      console.log('📤 Frontend: API request filters:', searchFilters);
      const searchResults = await apiService.searchPYQs(query, searchFilters);
      console.log(`📥 Frontend: Received ${searchResults.length} results for page ${page}`);
      
      if (searchResults.length > 0) {
        const firstResult = searchResults[0];
        const lastResult = searchResults[searchResults.length - 1];
        console.log(`📝 Frontend: First result: ${firstResult.question?.substring(0, 50)}...`);
        console.log(`📝 Frontend: Last result: ${lastResult.question?.substring(0, 50)}...`);
      }
      
      // Always update results and page - this was correct
      setResults(searchResults);
      setCurrentPage(page);
      
      // Better logic for hasMoreResults: assume more if we got exactly 10 results
      // In a real app, the backend should return total count
      setHasMoreResults(searchResults.length === 10);
      setTotalResults((page - 1) * 10 + searchResults.length);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch(1);
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy':
        return 'bg-gradient-to-r from-green-100 to-emerald-100 text-green-800 border border-green-200/50';
      case 'medium':
        return 'bg-gradient-to-r from-amber-100 to-yellow-100 text-amber-800 border border-amber-200/50';
      case 'hard':
        return 'bg-gradient-to-r from-red-100 to-pink-100 text-red-800 border border-red-200/50';
      default:
        return 'bg-gradient-to-r from-gray-100 to-slate-100 text-gray-800 border border-gray-200/50';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-ai-50 via-primary-50 to-secondary-50 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-20">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-ai-purple to-ai-blue rounded-2xl mb-4 shadow-xl">
            <SparklesIcon className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-ai-900 via-primary-700 to-secondary-700 bg-clip-text text-transparent mb-3">
            AI-Powered PYQ Search
          </h1>
          <p className="text-ai-600 text-lg max-w-2xl mx-auto">
            Discover past year questions using intelligent semantic search. Our AI understands context and themes, not just keywords.
          </p>
        </div>

        {/* Search Interface */}
        <div className="ai-card p-8 mb-8 relative overflow-hidden">
          {/* Background Pattern */}
          <div className="absolute inset-0 circuit-pattern opacity-5"></div>
          
          <div className="relative z-10">
            <div className="flex flex-col lg:flex-row space-y-4 lg:space-y-0 lg:space-x-4">
              <div className="flex-1 relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <CpuChipIcon className="h-6 w-6 text-ai-purple group-focus-within:text-primary-600 transition-colors" />
                </div>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="block w-full pl-12 pr-4 py-4 border border-ai-200 rounded-xl shadow-sm placeholder-ai-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white/80 backdrop-blur-sm transition-all duration-200 text-lg"
                  placeholder="Ask AI: 'Find questions about women empowerment in governance'..."
                />
                <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
                  <div className="w-2 h-2 bg-ai-emerald rounded-full animate-pulse"></div>
                </div>
              </div>
              
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`inline-flex items-center px-6 py-4 border border-ai-200 rounded-xl shadow-sm text-sm font-medium transition-all duration-200 transform hover:scale-105 ${
                  showFilters 
                    ? 'bg-gradient-to-r from-ai-purple to-ai-blue text-white shadow-xl' 
                    : 'text-ai-700 bg-white/80 backdrop-blur-sm hover:bg-white'
                }`}
              >
                <FunnelIcon className="h-5 w-5 mr-2" />
                Smart Filters
              </button>
              
              <button
                onClick={() => handleSearch(1)}
                disabled={loading}
                className="inline-flex items-center px-8 py-4 border border-transparent text-sm font-semibold rounded-xl shadow-lg text-white bg-gradient-to-r from-primary-500 to-secondary-500 hover:from-primary-600 hover:to-secondary-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 transition-all duration-200 transform hover:scale-105"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    AI Searching...
                  </>
                ) : (
                  <>
                    <BoltIcon className="h-5 w-5 mr-2" />
                    Search with AI
                  </>
                )}
              </button>
            </div>

            {/* Enhanced Filters */}
            {showFilters && (
              <div className="mt-6 pt-6 border-t border-ai-200/50 animate-slide-up">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-semibold text-ai-700 mb-3 flex items-center">
                      <DocumentTextIcon className="w-4 h-4 mr-2 text-ai-purple" />
                      Subject Filter
                    </label>
                    <select
                      value={filters.subject}
                      onChange={(e) => setFilters({ ...filters, subject: e.target.value })}
                      className="block w-full px-4 py-3 border border-ai-200 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white/50 backdrop-blur-sm transition-all duration-200"
                    >
                      <option value="">All Subjects</option>
                      {subjects.map((subject) => (
                        <option key={subject} value={subject}>
                          {subject}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-ai-700 mb-3 flex items-center">
                      <CalendarDaysIcon className="w-4 h-4 mr-2 text-ai-purple" />
                      Year Filter
                    </label>
                    <select
                      value={filters.year}
                      onChange={(e) => setFilters({ ...filters, year: e.target.value })}
                      className="block w-full px-4 py-3 border border-ai-200 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white/50 backdrop-blur-sm transition-all duration-200"
                    >
                      <option value="">All Years</option>
                      {years.map((year) => (
                        <option key={year} value={year.toString()}>
                          {year}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* AI-Enhanced Results */}
        <div className="space-y-6 relative">
          {/* Subtle loading overlay during filter changes */}
          {loading && results.length > 0 && (
            <div className="absolute inset-0 bg-white/60 backdrop-blur-sm z-10 flex items-center justify-center rounded-lg">
              <div className="ai-card p-4 shadow-lg">
                <div className="flex items-center space-x-3">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-500"></div>
                  <span className="text-sm font-medium text-ai-700">Updating results...</span>
                </div>
              </div>
            </div>
          )}
          {results.length > 0 && (
            <div className="flex items-center justify-between ai-card p-4">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-gradient-to-r from-ai-emerald to-ai-blue rounded-lg flex items-center justify-center mr-3">
                  <SparklesIcon className="w-4 h-4 text-white" />
                </div>
                <span className="text-sm font-medium text-ai-700">
                  AI found <span className="font-bold text-primary-600">{results.length}</span> relevant question(s)
                </span>
              </div>
              <div className="text-xs text-ai-500 flex items-center">
                <div className="w-2 h-2 bg-ai-emerald rounded-full mr-2 animate-pulse"></div>
                Semantic search active
              </div>
            </div>
          )}

          {results.map((pyq, index) => (
            <div 
              key={`${pyq.id}-${filters.subject}-${filters.year}`}
              className="ai-card p-6 hover:shadow-2xl transition-all duration-300 transform hover:scale-[1.02] relative overflow-hidden group"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {/* Background accent */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-primary-100/20 to-secondary-100/20 rounded-full transform translate-x-16 -translate-y-16 group-hover:scale-110 transition-transform duration-300"></div>
              
              <div className="relative z-10">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-3">
                      <div className="inline-flex items-center px-3 py-1 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-xl text-sm font-semibold shadow-lg">
                        <AcademicCapIcon className="w-4 h-4 mr-1" />
                        {pyq.paper} - {pyq.year}
                      </div>
                      <div className="inline-flex items-center px-3 py-1 bg-gradient-to-r from-ai-purple/10 to-ai-blue/10 text-ai-purple rounded-xl text-sm font-medium">
                        <BoltIcon className="w-4 h-4 mr-1" />
                        {pyq.marks} marks
                      </div>
                    </div>
                    
                    <h3 className="text-xl font-semibold text-ai-900 mb-4 leading-relaxed">
                      {pyq.question}
                    </h3>
                    
                    <div className="flex items-center space-x-4 mb-4">
                      <span
                        className={`inline-flex items-center px-3 py-1 text-sm font-semibold rounded-xl shadow-sm ${getDifficultyColor(
                          pyq.difficulty
                        )}`}
                      >
                        {pyq.difficulty.charAt(0).toUpperCase() + pyq.difficulty.slice(1)}
                      </span>
                      
                      <span className="inline-flex items-center px-3 py-1 text-sm font-medium bg-gradient-to-r from-purple-100 to-indigo-100 text-purple-800 rounded-xl border border-purple-200/50">
                        <SparklesIcon className="w-4 h-4 mr-1" />
                        {Math.round(pyq.similarity_score * 100)}% match
                      </span>
                      
                      <div className="flex flex-wrap gap-2">
                        {pyq.topics && pyq.topics.map((topic: string, topicIndex: number) => (
                          <span
                            key={topicIndex}
                            className="inline-flex items-center px-3 py-1 text-sm font-medium bg-gradient-to-r from-blue-100 to-cyan-100 text-blue-800 rounded-xl border border-blue-200/50"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="flex space-x-3">
                  <button 
                    onClick={() => {
                      // Create a modal or dedicated page to show full PYQ details
                      // For now, navigate to chat with this question pre-filled
                      const questionDetail = `Question: ${pyq.question}\n\nYear: ${pyq.year}\nPaper: ${pyq.paper}\nSubject: ${pyq.subject}\nMarks: ${pyq.marks}\nDifficulty: ${pyq.difficulty}\nTopics: ${pyq.topics?.join(', ') || 'N/A'}`;
                      
                      // Store question details in sessionStorage to access in chat
                      sessionStorage.setItem('pyq_context', JSON.stringify({
                        id: pyq.id,
                        question: pyq.question,
                        details: questionDetail,
                        mode: 'details'
                      }));
                      
                      navigate('/chat');
                    }}
                    className="inline-flex items-center px-4 py-2 border border-ai-200 shadow-sm text-sm font-medium rounded-xl text-ai-700 bg-white/80 backdrop-blur-sm hover:bg-white hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all duration-200 transform hover:scale-105"
                  >
                    <DocumentTextIcon className="w-4 h-4 mr-2" />
                    View Details
                  </button>
                  <button 
                    onClick={() => {
                      // Navigate to AI chat with practice mode for this question
                      const practicePrompt = `Let's practice this UPSC question together:\n\n"${pyq.question}"\n\nYear: ${pyq.year} | Paper: ${pyq.paper} | Marks: ${pyq.marks}\n\nPlease guide me through answering this step by step and provide hints when needed.`;
                      
                      // Store practice context in sessionStorage
                      sessionStorage.setItem('pyq_context', JSON.stringify({
                        id: pyq.id,
                        question: pyq.question,
                        prompt: practicePrompt,
                        mode: 'practice'
                      }));
                      
                      navigate('/chat');
                    }}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-accent-500 to-pink-500 hover:from-accent-600 hover:to-pink-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent-500 shadow-lg transition-all duration-200 transform hover:scale-105"
                  >
                    <SparklesIcon className="w-4 h-4 mr-2" />
                    Practice with AI
                  </button>
                </div>
              </div>
            </div>
          ))}

          {/* Pagination Controls */}
          {results.length > 0 && (
            <div className="ai-card p-6 flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <span className="text-sm text-ai-600">
                  Page {currentPage} • {results.length} results
                </span>
                {hasMoreResults && (
                  <span className="text-xs text-ai-500 bg-ai-100 px-2 py-1 rounded-full">
                    More available
                  </span>
                )}
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleSearch(currentPage - 1)}
                  disabled={currentPage === 1 || loading}
                  className="inline-flex items-center px-4 py-2 border border-ai-200 rounded-xl text-sm font-medium text-ai-700 bg-white hover:bg-ai-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 disabled:hover:scale-100"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Previous
                </button>
                
                <span className="text-sm text-ai-600 px-4">
                  {currentPage}
                </span>
                
                <button
                  onClick={() => handleSearch(currentPage + 1)}
                  disabled={!hasMoreResults || loading}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-primary-500 to-secondary-500 hover:from-primary-600 hover:to-secondary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 disabled:hover:scale-100"
                >
                  Next
                  <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {!loading && results.length === 0 && query && (
            <div className="text-center py-16 ai-card">
              <div className="w-20 h-20 bg-gradient-to-r from-gray-100 to-gray-200 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <MagnifyingGlassIcon className="h-10 w-10 text-gray-400" />
              </div>
              <h3 className="text-xl font-semibold text-ai-900 mb-3">No AI matches found</h3>
              <p className="text-ai-600 mb-6 max-w-md mx-auto">
                Our AI couldn't find questions matching your search. Try different keywords or adjust your filters.
              </p>
              <button 
                onClick={() => setQuery('')}
                className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
              >
                <BoltIcon className="w-5 h-5 mr-2" />
                Try New Search
              </button>
            </div>
          )}

          {!query && results.length === 0 && (
            <div className="text-center py-16 ai-card relative overflow-hidden">
              {/* Background pattern */}
              <div className="absolute inset-0 neural-pattern opacity-30"></div>
              
              <div className="relative z-10">
                <div className="w-24 h-24 bg-gradient-to-r from-ai-purple to-ai-blue rounded-2xl flex items-center justify-center mx-auto mb-8 shadow-xl">
                  <CpuChipIcon className="h-12 w-12 text-white" />
                </div>
                <h3 className="text-2xl font-bold text-ai-900 mb-4">
                  Intelligent Question Discovery
                </h3>
                <p className="text-ai-600 mb-8 max-w-lg mx-auto text-lg">
                  Our AI understands context, themes, and concepts. Search naturally and discover relevant past year questions.
                </p>
                
                <div className="space-y-4">
                  <p className="text-sm font-semibold text-ai-700">Try these AI-powered searches:</p>
                  <div className="flex flex-wrap justify-center gap-3">
                    {[
                      'Women leadership in governance',
                      'Digital transformation policies', 
                      'Climate adaptation strategies', 
                      'Federal cooperative dynamics'
                    ].map((example) => (
                      <button
                        key={example}
                        onClick={() => setQuery(example)}
                        className="px-4 py-2 bg-gradient-to-r from-ai-blue/10 to-ai-purple/10 hover:from-ai-blue/20 hover:to-ai-purple/20 rounded-xl text-ai-700 font-medium border border-ai-200/50 transition-all duration-200 transform hover:scale-105"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PYQSearchPage;
