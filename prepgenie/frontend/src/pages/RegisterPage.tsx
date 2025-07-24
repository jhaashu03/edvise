import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { EyeIcon, EyeSlashIcon, SparklesIcon, BoltIcon, CpuChipIcon, RocketLaunchIcon } from '@heroicons/react/24/outline';

const RegisterPage: React.FC = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      await register({
        email: formData.email,
        password: formData.password,
        first_name: formData.first_name,
        last_name: formData.last_name,
      });
      // Navigate to login page with success message
      navigate('/login', { 
        state: { 
          message: 'Registration successful! Please log in with your credentials.',
          email: formData.email 
        } 
      });
    } catch (err: any) {
      console.error('Registration error:', err);
      
      // Handle different error formats
      let errorMessage = 'Registration failed. Please try again.';
      
      if (err.response?.data) {
        const data = err.response.data;
        if (typeof data === 'string') {
          errorMessage = data;
        } else if (data.detail) {
          // Handle validation errors that might be objects or arrays
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (Array.isArray(data.detail)) {
            // Handle Pydantic validation errors
            errorMessage = data.detail.map((e: any) => e.msg || e.message || String(e)).join(', ');
          } else {
            errorMessage = String(data.detail);
          }
        } else if (data.message) {
          errorMessage = data.message;
        }
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-secondary-600 via-primary-700 to-accent-700 relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 bg-ai-mesh opacity-20"></div>
        
        {/* Floating elements */}
        <div className="absolute top-32 left-16 w-28 h-28 bg-white/10 rounded-full animate-float"></div>
        <div className="absolute top-20 right-20 w-16 h-16 bg-accent-400/20 rounded-full animate-float" style={{ animationDelay: '1s' }}></div>
        <div className="absolute bottom-40 left-24 w-20 h-20 bg-primary-400/20 rounded-full animate-float" style={{ animationDelay: '3s' }}></div>
        <div className="absolute bottom-20 right-32 w-12 h-12 bg-secondary-400/20 rounded-full animate-float" style={{ animationDelay: '5s' }}></div>
        
        <div className="relative z-10 flex flex-col justify-center items-center text-white p-12">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-28 h-28 bg-white/10 rounded-3xl backdrop-blur-xl mb-8 shadow-2xl">
              <RocketLaunchIcon className="w-14 h-14 text-white" />
            </div>
            
            <h1 className="text-6xl font-bold mb-6 bg-gradient-to-r from-white to-blue-100 bg-clip-text text-transparent">
              Join the Future
            </h1>
            
            <p className="text-xl text-blue-100 mb-8 max-w-md">
              Unlock AI-powered UPSC preparation and transform your study journey
            </p>
            
            <div className="space-y-5 text-left max-w-sm">
              <div className="flex items-center space-x-4 text-blue-100">
                <SparklesIcon className="w-7 h-7 text-accent-300" />
                <span className="text-lg">Personalized AI Learning Paths</span>
              </div>
              <div className="flex items-center space-x-4 text-blue-100">
                <CpuChipIcon className="w-7 h-7 text-accent-300" />
                <span className="text-lg">Intelligent Answer Evaluation</span>
              </div>
              <div className="flex items-center space-x-4 text-blue-100">
                <BoltIcon className="w-7 h-7 text-accent-300" />
                <span className="text-lg">Real-time AI Assistance</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Registration form */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-ai-50 via-white to-primary-50">
        <div className="max-w-md w-full space-y-8">
          {/* Mobile logo */}
          <div className="lg:hidden text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-2xl mb-4 shadow-xl">
              <SparklesIcon className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
              PrepGenie
            </h2>
          </div>

          <div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 p-8">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-ai-900 mb-2">
                Start Your AI Journey
              </h2>
              <p className="text-ai-600">
                Join thousands of UPSC aspirants already using AI
              </p>
            </div>

            <form className="space-y-6" onSubmit={handleSubmit}>
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl backdrop-blur-sm">
                  {error}
                </div>
              )}
              
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="first_name" className="block text-sm font-semibold text-ai-700 mb-2">
                      First Name
                    </label>
                    <input
                      id="first_name"
                      name="first_name"
                      type="text"
                      required
                      value={formData.first_name}
                      onChange={handleChange}
                      className="block w-full px-4 py-3 border border-ai-200 rounded-xl shadow-sm placeholder-ai-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white/50 backdrop-blur-sm transition-all duration-200"
                      placeholder="First name"
                    />
                  </div>
                  <div>
                    <label htmlFor="lastName" className="block text-sm font-semibold text-ai-700 mb-2">
                      Last Name
                    </label>
                    <input
                      id="last_name"
                      name="last_name"
                      type="text"
                      required
                      value={formData.last_name}
                      onChange={handleChange}
                      className="block w-full px-4 py-3 border border-ai-200 rounded-xl shadow-sm placeholder-ai-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white/50 backdrop-blur-sm transition-all duration-200"
                      placeholder="Last name"
                    />
                  </div>
                </div>
                
                <div>
                  <label htmlFor="email" className="block text-sm font-semibold text-ai-700 mb-2">
                    Email address
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={formData.email}
                    onChange={handleChange}
                    className="block w-full px-4 py-3 border border-ai-200 rounded-xl shadow-sm placeholder-ai-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white/50 backdrop-blur-sm transition-all duration-200"
                    placeholder="Enter your email"
                  />
                </div>
                
                <div>
                  <label htmlFor="password" className="block text-sm font-semibold text-ai-700 mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      required
                      value={formData.password}
                      onChange={handleChange}
                      className="block w-full px-4 py-3 border border-ai-200 rounded-xl shadow-sm placeholder-ai-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white/50 backdrop-blur-sm transition-all duration-200 pr-12"
                      placeholder="Create a password"
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-4 flex items-center text-ai-400 hover:text-ai-600 transition-colors"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <EyeSlashIcon className="h-5 w-5" />
                      ) : (
                        <EyeIcon className="h-5 w-5" />
                      )}
                    </button>
                  </div>
                </div>
                
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-semibold text-ai-700 mb-2">
                    Confirm Password
                  </label>
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    required
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className="block w-full px-4 py-3 border border-ai-200 rounded-xl shadow-sm placeholder-ai-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white/50 backdrop-blur-sm transition-all duration-200"
                    placeholder="Confirm your password"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-semibold rounded-xl text-white bg-gradient-to-r from-primary-500 to-secondary-500 hover:from-primary-600 hover:to-secondary-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-xl transition-all duration-200 transform hover:scale-[1.02]"
              >
                {loading ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Creating your AI account...
                  </div>
                ) : (
                  <div className="flex items-center">
                    <RocketLaunchIcon className="w-5 h-5 mr-2" />
                    Launch My AI Journey
                  </div>
                )}
              </button>

              <div className="text-center pt-4">
                <p className="text-sm text-ai-600">
                  Already have an account?{' '}
                  <Link
                    to="/login"
                    className="font-semibold text-primary-600 hover:text-primary-500 transition-colors"
                  >
                    Sign in to continue
                  </Link>
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
