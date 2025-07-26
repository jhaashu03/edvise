import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { UploadedAnswer, AnswerEvaluation } from '../types';
import {
  DocumentArrowUpIcon,
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { ProgressModal } from '../components/ProgressModal';
import { useProgressTracker } from '../hooks/useProgressTracker';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const AnswersPage: React.FC = () => {
  const [answers, setAnswers] = useState<UploadedAnswer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    questionId: '',
    content: '',
    file: null as File | null,
  });
  const [uploadLoading, setUploadLoading] = useState(false);
  const [expandedEvaluations, setExpandedEvaluations] = useState<Set<string>>(new Set());
  
  // Progress tracking for modal
  const { isVisible, taskId, showProgress, hideProgress, handleComplete, handleError } = useProgressTracker({
    onComplete: (taskId, success) => {
      console.log(`Processing ${success ? 'completed' : 'failed'} for task ${taskId}`);
      if (success) {
        loadAnswers(); // Reload answers after successful processing
      }
    },
    onError: (taskId, error) => {
      console.error(`Processing error for task ${taskId}:`, error);
    }
  });

  useEffect(() => {
    loadAnswers();
  }, []);

  const loadAnswers = async () => {
    try {
      const data = await apiService.getMyAnswers();
      // Parse JSON strings for strengths and improvements
      const processedAnswers = data.map(answer => {
        if (answer.evaluation) {
          return {
            ...answer,
            evaluation: {
              ...answer.evaluation,
              strengths: typeof answer.evaluation.strengths === 'string' 
                ? JSON.parse(answer.evaluation.strengths) 
                : answer.evaluation.strengths,
              improvements: typeof answer.evaluation.improvements === 'string'
                ? JSON.parse(answer.evaluation.improvements)
                : answer.evaluation.improvements
            }
          };
        }
        return answer;
      });
      setAnswers(processedAnswers);
    } catch (error) {
      console.error('Failed to load answers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadForm({ ...uploadForm, file });
    }
  };

  const toggleEvaluationExpanded = (answerId: string) => {
    const newExpanded = new Set(expandedEvaluations);
    if (newExpanded.has(answerId)) {
      newExpanded.delete(answerId);
    } else {
      newExpanded.add(answerId);
    }
    setExpandedEvaluations(newExpanded);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadForm.content && !uploadForm.file) return;

    setUploadLoading(true);
    try {
      // For PDF uploads, provide a default content if none is provided
      const contentToSend = uploadForm.content || 
        (uploadForm.file ? `Answer uploaded via PDF file: ${uploadForm.file.name}` : '');
      
      const response = await apiService.uploadAnswer(
        uploadForm.questionId || 'sample-question-id', // In real app, this would be selected
        contentToSend,
        uploadForm.file || undefined
      );

      console.log('🚀 Upload response:', response);
      console.log('🎯 Upload form file:', uploadForm.file);
      console.log('🔍 Task ID from response:', response.task_id);

      // Show modal progress if we have a task_id
      if (response.task_id && uploadForm.file) {
        console.log('✅ Calling showProgress with task_id:', response.task_id);
        showProgress(response.task_id);
        console.log('📊 Progress state after showProgress call - isVisible:', isVisible, 'taskId:', taskId);
      } else {
        console.log('❌ Not showing progress modal - task_id:', response.task_id, 'file:', uploadForm.file);
      }

      setUploadForm({ questionId: '', content: '', file: null });
      setShowUploadForm(false);
      
      // Reload answers to show the new upload
      loadAnswers();
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploadLoading(false);
    }
  };

  const getStatusColor = (evaluation: AnswerEvaluation | undefined) => {
    if (!evaluation) return 'text-yellow-600';
    const percentage = (evaluation.score / evaluation.maxScore) * 100;
    if (percentage >= 80) return 'text-green-600';
    if (percentage >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getStatusIcon = (evaluation: AnswerEvaluation | undefined) => {
    if (!evaluation) return ClockIcon;
    const percentage = (evaluation.score / evaluation.maxScore) * 100;
    if (percentage >= 60) return CheckCircleIcon;
    return ExclamationCircleIcon;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="p-6 max-h-screen overflow-y-auto">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">My Answers</h1>
              <p className="text-gray-600 mt-2">
                Upload and track your answer evaluations
              </p>
            </div>
            <button
              onClick={() => setShowUploadForm(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
              Upload Answer
            </button>
          </div>

        {/* Upload Form Modal */}
        {showUploadForm && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
              <div className="mt-3">
                <h3 className="text-lg font-medium text-gray-900 text-center mb-4">
                  Upload Answer
                </h3>
                <form onSubmit={handleUpload} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Answer Content
                    </label>
                    <textarea
                      value={uploadForm.content}
                      onChange={(e) => setUploadForm({ ...uploadForm, content: e.target.value })}
                      rows={6}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                      placeholder="Type your answer here or leave empty if uploading PDF file..."
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Or Upload File (PDF/Image)
                    </label>
                    <div className="space-y-2">
                      <input
                        type="file"
                        onChange={handleFileChange}
                        accept=".pdf,.jpg,.jpeg,.png"
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                      />
                      {uploadForm.file && (
                        <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                          <div className="flex items-center">
                            <DocumentTextIcon className="h-5 w-5 text-blue-600 mr-2" />
                            <div className="flex-1">
                              <p className="text-sm font-medium text-blue-900">
                                {uploadForm.file.name}
                              </p>
                              <p className="text-xs text-blue-600">
                                {(uploadForm.file.size / (1024 * 1024)).toFixed(2)} MB
                                {uploadForm.file.type === 'application/pdf' && (
                                  <span className="ml-2 bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                                    PDF will be processed with AI
                                  </span>
                                )}
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={() => setUploadForm({ ...uploadForm, file: null })}
                              className="ml-2 text-blue-400 hover:text-blue-600"
                            >
                              <XMarkIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex space-x-3">
                    <button
                      type="button"
                      onClick={() => setShowUploadForm(false)}
                      className="flex-1 inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={uploadLoading || (!uploadForm.content && !uploadForm.file)}
                      className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                    >
                      {uploadLoading ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          {uploadForm.file?.type === 'application/pdf' ? 'Processing PDF...' : 'Uploading...'}
                        </>
                      ) : (
                        <>
                          <DocumentArrowUpIcon className="h-4 w-4 mr-2" />
                          Upload {uploadForm.file ? (uploadForm.file.type === 'application/pdf' ? 'PDF' : 'File') : 'Answer'}
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Answers List */}
        <div className="space-y-6">
          {answers.length > 0 ? (
            answers.map((answer) => {
              const StatusIcon = getStatusIcon(answer.evaluation);
              return (
                <div key={answer.id} className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center mb-3">
                        <DocumentTextIcon className="h-5 w-5 text-gray-400 mr-2" />
                        <span className="text-sm text-gray-600">
                          {answer.fileName ? (
                            <>
                              Uploaded <span className="font-medium text-primary-600">{answer.fileName}</span> on{' '}
                              <span className="font-medium">
                                {answer.uploadedAt ? new Date(answer.uploadedAt).toLocaleString() : 'Recently'}
                              </span>
                            </>
                          ) : (
                            <>
                              Uploaded on{' '}
                              <span className="font-medium">
                                {answer.uploadedAt ? new Date(answer.uploadedAt).toLocaleString() : 'Recently'}
                              </span>
                            </>
                          )}
                        </span>
                      </div>
                      
                      <div className="prose max-w-none mb-4">
                        <p className="text-gray-900 whitespace-pre-wrap">
                          {answer.content ? (
                            <>
                              {answer.content.substring(0, 200)}
                              {answer.content.length > 200 && '...'}
                            </>
                          ) : (
                            <span className="text-gray-500 italic">
                              Content will be extracted from uploaded file
                            </span>
                          )}
                        </p>
                      </div>

                      {answer.filePath && (
                        <div className="mb-4">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            File uploaded
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="ml-6 flex flex-col items-end">
                      <div className={`flex items-center ${getStatusColor(answer.evaluation)}`}>
                        <StatusIcon className="h-5 w-5 mr-1" />
                        {answer.evaluation ? (
                          <span className="text-sm font-medium">
                            {Number(answer.evaluation.score).toFixed(1)}/{answer.evaluation.maxScore}
                          </span>
                        ) : (
                          <div className="flex flex-col items-end">
                            <span className="text-sm font-medium text-yellow-600 mb-2">Processing...</span>
                            <div className="w-32">
                              <div className="bg-gray-200 rounded-full h-2">
                                <div className="bg-gradient-to-r from-blue-500 to-green-500 h-2 rounded-full animate-pulse" style={{width: '60%'}}></div>
                              </div>
                              <span className="text-xs text-gray-500 mt-1 block text-right">~2-3 minutes</span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Enhanced Evaluation Section */}
                  {answer.evaluation ? (
                    <div className="mt-6 pt-6 border-t border-gray-200">
                      {/* Evaluation Summary Card */}
                      <div className="bg-gradient-to-r from-blue-50 to-green-50 rounded-lg p-4 mb-4">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="text-lg font-semibold text-gray-900 flex items-center">
                            <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
                            Evaluation Complete
                          </h4>
                          <button
                            onClick={() => toggleEvaluationExpanded(answer.id)}
                            className="inline-flex items-center px-3 py-1 bg-white rounded-full text-sm font-medium text-primary-600 hover:bg-primary-50 transition-colors border border-primary-200"
                          >
                            <span>{expandedEvaluations.has(answer.id) ? 'Hide Details' : 'View Details'}</span>
                            {expandedEvaluations.has(answer.id) ? (
                              <ChevronUpIcon className="h-4 w-4 ml-1" />
                            ) : (
                              <ChevronDownIcon className="h-4 w-4 ml-1" />
                            )}
                          </button>
                        </div>
                        
                        {/* Score Summary */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="text-center">
                            <div className="text-2xl font-bold text-primary-600">
                              {Number(answer.evaluation.score).toFixed(1)}/{answer.evaluation.maxScore}
                            </div>
                            <div className="text-xs text-gray-600">Total Score</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-blue-600">
                              {Number(answer.evaluation.structure).toFixed(1)}/10
                            </div>
                            <div className="text-xs text-gray-600">Structure</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-green-600">
                              {Number(answer.evaluation.coverage).toFixed(1)}/10
                            </div>
                            <div className="text-xs text-gray-600">Coverage</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-purple-600">
                              {Number(answer.evaluation.tone).toFixed(1)}/10
                            </div>
                            <div className="text-xs text-gray-600">Tone</div>
                          </div>
                        </div>
                      </div>

                      {/* Expandable Detailed Evaluation */}
                      {expandedEvaluations.has(answer.id) && (
                        <div className="space-y-6 animate-in slide-in-from-top duration-300">
                          {/* Detailed Feedback */}
                          <div className="bg-white border border-gray-200 rounded-lg p-6">
                            <h5 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                              <DocumentTextIcon className="h-5 w-5 text-blue-500 mr-2" />
                              � Detailed Analysis
                            </h5>
                            <div className="prose max-w-none">
                              <div className="bg-gray-50 p-4 rounded-lg">
                                <div className="text-sm text-gray-700 leading-relaxed prose prose-sm prose-gray max-w-none
                                    prose-headings:text-gray-900 prose-headings:font-semibold
                                    prose-p:text-gray-700 prose-p:leading-relaxed
                                    prose-strong:text-gray-900 prose-strong:font-semibold
                                    prose-ul:text-gray-700 prose-li:text-gray-700
                                    prose-code:text-indigo-600 prose-code:bg-indigo-50 prose-code:px-1 prose-code:rounded">
                                  <ReactMarkdown 
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                      // Ensure proper line breaks and spacing with white-space preservation
                                      p: ({children}) => <p className="mb-3 whitespace-pre-wrap">{children}</p>,
                                      h1: ({children}) => <h1 className="text-lg font-semibold mb-3 mt-4 whitespace-pre-wrap">{children}</h1>,
                                      h2: ({children}) => <h2 className="text-md font-semibold mb-2 mt-3 whitespace-pre-wrap">{children}</h2>,
                                      h3: ({children}) => <h3 className="text-sm font-semibold mb-2 mt-3 whitespace-pre-wrap">{children}</h3>,
                                      strong: ({children}) => <strong className="font-semibold text-gray-900">{children}</strong>,
                                      ul: ({children}) => <ul className="list-disc pl-6 mb-3 space-y-1">{children}</ul>,
                                      li: ({children}) => <li className="text-gray-700 whitespace-pre-wrap">{children}</li>,
                                      br: () => <br />,
                                      text: ({children}) => <span className="whitespace-pre-wrap">{children}</span>,
                                    }}
                                  >
                                    {answer.evaluation.feedback}
                                  </ReactMarkdown>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Strengths and Improvements */}
                          <div className="grid md:grid-cols-2 gap-6">
                            {/* Strengths */}
                            {Array.isArray(answer.evaluation.strengths) && answer.evaluation.strengths.length > 0 && (
                              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                                <h5 className="text-lg font-semibold text-green-800 mb-4 flex items-center">
                                  <CheckCircleIcon className="h-5 w-5 mr-2" />
                                  ✅ Strengths Identified
                                </h5>
                                <ul className="space-y-3">
                                  {answer.evaluation.strengths.map((strength, index) => (
                                    <li key={index} className="text-sm text-green-700 flex items-start">
                                      <span className="text-green-500 mr-3 mt-1">•</span>
                                      <span className="flex-1">{strength}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Areas for Improvement */}
                            {Array.isArray(answer.evaluation.improvements) && answer.evaluation.improvements.length > 0 && (
                              <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
                                <h5 className="text-lg font-semibold text-amber-800 mb-4 flex items-center">
                                  <ExclamationCircleIcon className="h-5 w-5 mr-2" />
                                  💡 Areas for Improvement
                                </h5>
                                <ul className="space-y-3">
                                  {answer.evaluation.improvements.map((improvement, index) => (
                                    <li key={index} className="text-sm text-amber-700 flex items-start">
                                      <span className="text-amber-500 mr-3 mt-1">•</span>
                                      <span className="flex-1">{improvement}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="mt-6 pt-6 border-t border-gray-200">
                      {/* Processing State with Real-time Progress */}
                      <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border border-yellow-200 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center">
                            <ClockIcon className="h-6 w-6 text-yellow-600 mr-3 animate-spin" />
                            <div>
                              <h4 className="text-lg font-semibold text-yellow-800">AI Evaluation in Progress</h4>
                              <p className="text-sm text-yellow-700">Processing your answer with advanced AI analysis...</p>
                            </div>
                          </div>
                        </div>
                        
                        {/* Enhanced Progress Bar */}
                        <div className="space-y-3">
                          <div className="flex justify-between text-sm text-yellow-700">
                            <span>Processing Status</span>
                            <span>Estimated: 2-3 minutes</span>
                          </div>
                          <div className="w-full bg-yellow-200 rounded-full h-3">
                            <div className="bg-gradient-to-r from-yellow-500 to-orange-500 h-3 rounded-full animate-pulse transition-all duration-1000" style={{width: '45%'}}></div>
                          </div>
                          <div className="text-xs text-yellow-600 italic">
                            📄 Analyzing content with AI vision • 🔍 Extracting questions • ⭐ Comprehensive evaluation
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <DocumentTextIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No answers uploaded yet</h3>
              <p className="text-gray-600 mb-4">
                Start by uploading your first answer to get AI-powered feedback and evaluation.
              </p>
              <button
                onClick={() => setShowUploadForm(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <DocumentArrowUpIcon className="h-5 w-5 mr-2" />
                Upload Your First Answer
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Progress Modal */}
      {isVisible && taskId && (
        <ProgressModal
          isOpen={isVisible}
          taskId={taskId}
          onClose={hideProgress}
          onComplete={handleComplete}
          onError={handleError}
        />
      )}
    </div>
    </div>
  );
};

export default AnswersPage;
