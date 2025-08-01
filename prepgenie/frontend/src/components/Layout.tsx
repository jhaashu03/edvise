import React, { useState, useEffect, useRef } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { NavigationProvider } from '../contexts/NavigationContext';
import {
  HomeIcon,
  BookOpenIcon,
  MagnifyingGlassIcon,
  DocumentTextIcon,
  CalendarDaysIcon,
  ChartBarIcon,
  ChatBubbleLeftRightIcon,
  UserIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

const Layout: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [navCollapsed, setNavCollapsed] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Simple manual toggle functionality
  const toggleNavCollapse = () => {
    setNavCollapsed(!navCollapsed);
  };

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
    { name: 'Syllabus', href: '/syllabus', icon: BookOpenIcon },
    { name: 'PYQ Search', href: '/pyq-search', icon: MagnifyingGlassIcon },
    { name: 'Answer Upload', href: '/answers', icon: DocumentTextIcon },
    { name: 'Study Plan', href: '/study-plan', icon: CalendarDaysIcon },
    { name: 'Progress', href: '/progress', icon: ChartBarIcon },
    { name: 'AI Chat', href: '/chat', icon: ChatBubbleLeftRightIcon },
  ];

  if (!isAuthenticated) {
    return <Outlet />;
  }

  return (
    <div className="h-screen bg-gradient-to-br from-ai-50 via-primary-50 to-secondary-50">
      {/* Background Pattern */}
      <div className="fixed inset-0 bg-ai-mesh opacity-30 pointer-events-none"></div>
      
      <div className="flex relative h-full">
        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-gray-600 bg-opacity-75 z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <div className={`fixed inset-y-0 left-0 z-50 transform transition-all duration-300 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:static lg:inset-0 ${
          navCollapsed ? 'w-16' : 'w-64'
        }`}>
          <div className="flex flex-col h-full bg-white/80 backdrop-blur-xl shadow-2xl border-r border-white/20">
            {/* Logo and Toggle */}
            <div className={`flex items-center border-b border-gray-200/50 ${
              navCollapsed ? 'px-2 py-4 justify-center' : 'px-6 py-6'
            }`}>
              {navCollapsed ? (
                /* Collapsed Mode - Show only hamburger toggle */
                <button
                  onClick={toggleNavCollapse}
                  className="p-3 rounded-xl bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-lg hover:from-primary-600 hover:to-secondary-600 transition-all duration-200 group"
                  title="Expand Navigation"
                >
                  <Bars3Icon className="w-5 h-5 group-hover:scale-110 transition-transform" />
                </button>
              ) : (
                /* Expanded Mode - Show full logo and toggle */
                <>
                  <div className="flex items-center">
                    <div className="relative">
                      <div className="w-10 h-10 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center shadow-lg">
                        <SparklesIcon className="w-6 h-6 text-white" />
                      </div>
                      <div className="absolute -top-1 -right-1 w-4 h-4 bg-accent-400 rounded-full animate-pulse-slow"></div>
                    </div>
                    <div className="ml-3">
                      <span className="text-xl font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                        PrepGenie
                      </span>
                      <div className="text-xs text-ai-500 font-medium">AI-Powered UPSC Prep</div>
                    </div>
                  </div>
                  
                  {/* Desktop collapse button */}
                  <button
                    onClick={toggleNavCollapse}
                    className="hidden lg:block ml-auto p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100/50 transition-all duration-200"
                    title="Collapse Navigation"
                  >
                    <Bars3Icon className="w-5 h-5" />
                  </button>
                  
                  {/* Mobile close button */}
                  <button
                    onClick={() => setSidebarOpen(false)}
                    className="ml-auto lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </>
              )}
            </div>

            {/* Navigation */}
            <nav className={`flex-1 py-6 space-y-2 overflow-y-auto ${
              navCollapsed ? 'px-2' : 'px-4'
            }`}>
              {navigation.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`group flex items-center text-sm font-medium rounded-xl transition-all duration-200 ${
                      navCollapsed 
                        ? 'px-3 py-3 justify-center'
                        : 'px-4 py-3'
                    } ${
                      isActive
                        ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-lg shadow-primary-500/25'
                        : 'text-ai-700 hover:bg-white/50 hover:shadow-md'
                    }`}
                    title={navCollapsed ? item.name : undefined}
                  >
                    <item.icon className={`w-5 h-5 transition-transform group-hover:scale-110 ${
                      isActive ? 'text-white' : 'text-ai-500'
                    } ${
                      navCollapsed ? '' : 'mr-3'
                    }`} />
                    {!navCollapsed && (
                      <>
                        <span>{item.name}</span>
                        {isActive && (
                          <div className="ml-auto w-2 h-2 bg-white rounded-full animate-pulse"></div>
                        )}
                      </>
                    )}
                    {navCollapsed && isActive && (
                      <div className="absolute right-1 w-2 h-2 bg-white rounded-full animate-pulse"></div>
                    )}
                  </Link>
                );
              })}
            </nav>

            {/* User menu */}
            <div className={`border-t border-gray-200/50 ${
              navCollapsed ? 'px-2 py-4' : 'px-4 py-4'
            }`}>
              {navCollapsed ? (
                /* Collapsed Mode - Avatar and logout button only */
                <div className="flex flex-col items-center space-y-3">
                  <div className="relative" title={`${user?.first_name} ${user?.last_name}`}>
                    <div className="w-10 h-10 bg-gradient-to-r from-accent-400 to-accent-500 rounded-full flex items-center justify-center shadow-md">
                      <UserIcon className="w-5 h-5 text-white" />
                    </div>
                    <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-white"></div>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="p-2 text-ai-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-200"
                    title="Logout"
                  >
                    <ArrowRightOnRectangleIcon className="w-5 h-5" />
                  </button>
                </div>
              ) : (
                /* Expanded Mode - Full user info */
                <div className="flex items-center p-3 rounded-xl bg-gradient-to-r from-gray-50 to-gray-100/50 border border-gray-200/50">
                  <div className="relative">
                    <div className="w-10 h-10 bg-gradient-to-r from-accent-400 to-accent-500 rounded-full flex items-center justify-center shadow-md">
                      <UserIcon className="w-5 h-5 text-white" />
                    </div>
                    <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-white"></div>
                  </div>
                  <div className="ml-3 flex-1 min-w-0">
                    <p className="text-sm font-semibold text-ai-900 truncate">
                      {user?.first_name} {user?.last_name}
                    </p>
                    <p className="text-xs text-ai-500 truncate">{user?.email}</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="p-2 text-ai-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-200"
                    title="Logout"
                  >
                    <ArrowRightOnRectangleIcon className="w-5 h-5" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 flex flex-col h-screen transition-all duration-300">
          {/* Mobile header */}
          <div className="lg:hidden flex-shrink-0 sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-gray-200/50 px-4 py-4">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
              >
                <Bars3Icon className="w-6 h-6" />
              </button>
              <div className="flex items-center">
                <div className="w-8 h-8 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center">
                  <SparklesIcon className="w-5 h-5 text-white" />
                </div>
                <span className="ml-2 text-lg font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                  PrepGenie
                </span>
              </div>
              <div className="w-10 h-10"></div> {/* Spacer for balance */}
            </div>
          </div>

          <main className="flex-1 overflow-y-auto relative m-0 p-0">
            <div className="min-h-full m-0 p-0">
              <NavigationProvider navCollapsed={navCollapsed}>
                <Outlet />
              </NavigationProvider>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default Layout;
