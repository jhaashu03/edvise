import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/api';
import { ProgressData, StudyPlan, UploadedAnswer } from '../types';
import {
  ChartBarIcon,
  DocumentTextIcon,
  CalendarDaysIcon,
  TrophyIcon,
  CheckCircleIcon,
  ClockIcon,
  SparklesIcon,
  FireIcon,
  AcademicCapIcon,
  RocketLaunchIcon,
  BoltIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [studyPlan, setStudyPlan] = useState<StudyPlan | null>(null);
  const [recentAnswers, setRecentAnswers] = useState<UploadedAnswer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [progressData, answersData] = await Promise.all([
        apiService.getProgress().catch(() => ({ 
          totalQuestions: 0, 
          answersSubmitted: 0, 
          averageScore: 0, 
          weakAreas: [], 
          strongAreas: [], 
          recentActivity: [] 
        })),
        apiService.getMyAnswers().catch(() => []),
      ]);

      setProgress(progressData);
      setRecentAnswers(answersData.slice(0, 5)); // Last 5 answers

      try {
        const planData = await apiService.getStudyPlan();
        setStudyPlan(planData);
      } catch (error) {
        // User might not have a study plan yet
        console.log('No study plan found:', error);
        setStudyPlan(null);
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const stats = [
    {
      name: 'Questions Answered',
      value: progress?.totalQuestions || 0,
      icon: DocumentTextIcon,
      gradient: 'from-blue-500 to-blue-600',
      bgGradient: 'from-blue-50 to-blue-100',
      iconBg: 'bg-blue-500',
    },
    {
      name: 'Average Score',
      value: progress?.averageScore ? `${progress.averageScore.toFixed(1)}%` : '0%',
      icon: TrophyIcon,
      gradient: 'from-amber-500 to-orange-600',
      bgGradient: 'from-amber-50 to-orange-100',
      iconBg: 'bg-amber-500',
    },
    {
      name: 'Study Streak',
      value: '7 days', // This would come from backend
      icon: FireIcon,
      gradient: 'from-red-500 to-pink-600',
      bgGradient: 'from-red-50 to-pink-100',
      iconBg: 'bg-red-500',
    },
    {
      name: 'Progress',
      value: studyPlan?.targets?.length ? `${Math.round(((studyPlan.targets?.filter(t => t.status === 'completed') || []).length / studyPlan.targets.length) * 100)}%` : '0%',
      icon: ChartBarIcon,
      gradient: 'from-green-500 to-emerald-600',
      bgGradient: 'from-green-50 to-emerald-100',
      iconBg: 'bg-green-500',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-ai-50 via-primary-50 to-secondary-50">
        <div className="text-center">
          <div className="relative">
            <div className="animate-spin rounded-full h-32 w-32 border-4 border-primary-200 border-t-primary-600 shadow-lg"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <SparklesIcon className="w-8 h-8 text-primary-600 animate-pulse" />
            </div>
          </div>
          <p className="mt-4 text-ai-600 font-medium">Loading your AI dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-ai-50 via-primary-50 to-secondary-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-2xl flex items-center justify-center shadow-lg mr-4">
              <SparklesIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-ai-900 via-primary-700 to-secondary-700 bg-clip-text text-transparent">
                Welcome back, {user?.first_name}!
              </h1>
              <p className="text-ai-600 mt-1 text-lg">
                Your AI-powered UPSC journey continues
              </p>
            </div>
          </div>
          
          {/* Quick action buttons */}
          <div className="flex flex-wrap gap-3">
            <button className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105">
              <RocketLaunchIcon className="w-4 h-4 mr-2" />
              Start Study Session
            </button>
            <button className="inline-flex items-center px-4 py-2 bg-white/70 backdrop-blur-sm text-ai-700 rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 border border-white/20">
              <EyeIcon className="w-4 h-4 mr-2" />
              View Analytics
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => (
            <div 
              key={stat.name} 
              className="group relative bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/20 p-6 hover:shadow-2xl transition-all duration-300 transform hover:scale-105"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-r ${stat.gradient} shadow-lg mb-4`}>
                    <stat.icon className="h-6 w-6 text-white" />
                  </div>
                  <p className="text-sm font-semibold text-ai-600 mb-2">{stat.name}</p>
                  <p className="text-3xl font-bold bg-gradient-to-r from-ai-900 to-ai-700 bg-clip-text text-transparent">
                    {stat.value}
                  </p>
                </div>
                <div className={`absolute top-0 right-0 w-24 h-24 rounded-full bg-gradient-to-br ${stat.bgGradient} opacity-10 transform translate-x-8 -translate-y-8`}></div>
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Activity */}
          <div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/20 overflow-hidden">
            <div className="px-6 py-5 bg-gradient-to-r from-primary-500/5 to-secondary-500/5 border-b border-gray-200/50">
              <div className="flex items-center">
                <DocumentTextIcon className="w-6 h-6 text-primary-600 mr-3" />
                <h2 className="text-xl font-bold text-ai-900">Recent AI Evaluations</h2>
                <div className="ml-auto">
                  <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse shadow-lg"></div>
                </div>
              </div>
            </div>
            <div className="p-6">
              {recentAnswers.length > 0 ? (
                <div className="space-y-4">
                  {recentAnswers.map((answer, index) => (
                    <div 
                      key={answer.id} 
                      className="group flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-gray-100/50 rounded-xl border border-gray-200/50 hover:shadow-md transition-all duration-200"
                      style={{ animationDelay: `${index * 0.1}s` }}
                    >
                      <div className="flex items-center flex-1">
                        <div className="w-10 h-10 bg-gradient-to-r from-accent-400 to-accent-500 rounded-lg flex items-center justify-center mr-4">
                          <AcademicCapIcon className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-ai-900">
                            AI Answer Evaluation
                          </p>
                          <p className="text-xs text-ai-500">
                            {new Date(answer.uploadedAt).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      {answer.evaluation && (
                        <div className="text-right">
                          <div className="inline-flex items-center px-3 py-1 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-full text-sm font-bold">
                            <SparklesIcon className="w-4 h-4 mr-1" />
                            {answer.evaluation.score}/{answer.evaluation.maxScore}
                          </div>
                          <p className="text-xs text-ai-500 mt-1">AI Score</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="w-20 h-20 bg-gradient-to-r from-gray-100 to-gray-200 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <DocumentTextIcon className="h-10 w-10 text-gray-400" />
                  </div>
                  <p className="text-ai-700 font-semibold text-lg mb-2">Ready to get started?</p>
                  <p className="text-ai-500 mb-6">Upload your first answer and let our AI evaluate it!</p>
                  <button className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105">
                    <BoltIcon className="w-5 h-5 mr-2" />
                    Upload Answer
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Study Plan Progress */}
          <div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/20 overflow-hidden">
            <div className="px-6 py-5 bg-gradient-to-r from-accent-500/5 to-green-500/5 border-b border-gray-200/50">
              <div className="flex items-center">
                <CalendarDaysIcon className="w-6 h-6 text-accent-600 mr-3" />
                <h2 className="text-xl font-bold text-ai-900">AI Study Plan</h2>
                <div className="ml-auto">
                  <div className="w-3 h-3 bg-accent-400 rounded-full animate-pulse shadow-lg"></div>
                </div>
              </div>
            </div>
            <div className="p-6">
              {studyPlan && studyPlan.targets?.length ? (
                <div className="space-y-4">
                  {studyPlan.targets?.slice(0, 5).map((target, index) => (
                    <div 
                      key={target.id} 
                      className="group flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-gray-100/50 rounded-xl border border-gray-200/50 hover:shadow-md transition-all duration-200"
                      style={{ animationDelay: `${index * 0.1}s` }}
                    >
                      <div className="flex items-center">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center mr-4 ${
                          target.status === 'completed' 
                            ? 'bg-gradient-to-r from-green-400 to-green-500' 
                            : 'bg-gradient-to-r from-amber-400 to-amber-500'
                        }`}>
                          {target.status === 'completed' ? (
                            <CheckCircleIcon className="h-5 w-5 text-white" />
                          ) : (
                            <ClockIcon className="h-5 w-5 text-white" />
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-ai-900">{target.topic}</p>
                          <p className="text-xs text-ai-500">{target.subject}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span
                          className={`inline-flex px-3 py-1 text-xs font-semibold rounded-full ${
                            target.status === 'completed'
                              ? 'bg-gradient-to-r from-green-100 to-green-200 text-green-800'
                              : target.status === 'in_progress'
                              ? 'bg-gradient-to-r from-amber-100 to-amber-200 text-amber-800'
                              : 'bg-gradient-to-r from-gray-100 to-gray-200 text-gray-800'
                          }`}
                        >
                          {target.status.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="w-20 h-20 bg-gradient-to-r from-primary-100 to-secondary-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <CalendarDaysIcon className="h-10 w-10 text-primary-500" />
                  </div>
                  <p className="text-ai-700 font-semibold text-lg mb-2">AI Study Plan Awaits</p>
                  <p className="text-ai-500 mb-6">Let our AI create a personalized study plan just for you!</p>
                  <button className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-accent-500 to-green-500 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105">
                    <SparklesIcon className="w-5 h-5 mr-2" />
                    Generate AI Plan
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Weak Areas */}
        {progress?.weakAreas && progress.weakAreas.length > 0 && (
          <div className="mt-8 bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/20 overflow-hidden">
            <div className="px-6 py-5 bg-gradient-to-r from-red-500/5 to-pink-500/5 border-b border-gray-200/50">
              <div className="flex items-center">
                <BoltIcon className="w-6 h-6 text-red-600 mr-3" />
                <h2 className="text-xl font-bold text-ai-900">AI Insights: Focus Areas</h2>
              </div>
            </div>
            <div className="p-6">
              <div className="flex flex-wrap gap-3 mb-4">
                {progress.weakAreas.map((area, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-4 py-2 text-sm font-medium bg-gradient-to-r from-red-100 to-pink-100 text-red-800 rounded-xl border border-red-200/50 shadow-sm"
                  >
                    <FireIcon className="w-4 h-4 mr-2" />
                    {area}
                  </span>
                ))}
              </div>
              <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-200/50">
                <p className="text-sm text-amber-800 font-medium flex items-center">
                  <SparklesIcon className="w-4 h-4 mr-2" />
                  AI Recommendation: Focus on these topics to boost your performance significantly.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;
