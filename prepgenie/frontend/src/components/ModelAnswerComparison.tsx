import React, { useState } from 'react';
import { 
  SparklesIcon, 
  DocumentArrowDownIcon,
  ArrowsRightLeftIcon,
  CheckCircleIcon,
  LightBulbIcon,
  XMarkIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';
import { ModelAnswerResponse, QuestionModelAnswer } from '../types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ModelAnswerComparisonProps {
  modelAnswerData: ModelAnswerResponse;
  onClose: () => void;
  onDownloadPDF: () => void;
}

export const ModelAnswerComparison: React.FC<ModelAnswerComparisonProps> = ({
  modelAnswerData,
  onClose,
  onDownloadPDF
}) => {
  const [selectedQuestion, setSelectedQuestion] = useState(0);
  const [viewMode, setViewMode] = useState<'side-by-side' | 'model-only'>('side-by-side');
  
  const currentQuestion = modelAnswerData.questions[selectedQuestion];
  
  if (!currentQuestion) {
    return (
      <div className="p-8 text-center text-gray-500">
        No model answer available
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 overflow-y-auto">
      <div className="min-h-screen py-8 px-4">
        <div className="max-w-7xl mx-auto bg-white rounded-2xl shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 px-6 py-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-white/20 rounded-xl">
                  <SparklesIcon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">AI-Enhanced Model Answer</h2>
                  <p className="text-emerald-100 text-sm">
                    Your answer transformed into topper-quality
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={onDownloadPDF}
                  className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-white transition-colors"
                >
                  <DocumentArrowDownIcon className="h-5 w-5" />
                  <span className="hidden sm:inline">Download PDF</span>
                </button>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-white/20 rounded-lg text-white transition-colors"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>
            </div>
            
            {/* Question Tabs */}
            {modelAnswerData.questions.length > 1 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {modelAnswerData.questions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedQuestion(idx)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      selectedQuestion === idx
                        ? 'bg-white text-emerald-700 shadow-lg'
                        : 'bg-white/20 text-white hover:bg-white/30'
                    }`}
                  >
                    Q{q.question_number}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* View Mode Toggle */}
          <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <DocumentTextIcon className="h-5 w-5 text-gray-500" />
              <span className="text-sm text-gray-600 font-medium">
                {currentQuestion.question_text}
              </span>
            </div>
            <div className="flex items-center gap-2 bg-gray-200 rounded-lg p-1">
              <button
                onClick={() => setViewMode('side-by-side')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'side-by-side'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <ArrowsRightLeftIcon className="h-4 w-4" />
                Compare
              </button>
              <button
                onClick={() => setViewMode('model-only')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  viewMode === 'model-only'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <SparklesIcon className="h-4 w-4" />
                Model Only
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {viewMode === 'side-by-side' ? (
              <div className="grid lg:grid-cols-2 gap-6">
                {/* Original Answer */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 pb-3 border-b border-gray-200">
                    <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                    <h3 className="font-semibold text-gray-800">Your Original Answer</h3>
                  </div>
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 min-h-[400px]">
                    <div className="prose prose-sm max-w-none text-gray-700">
                      {currentQuestion.original_answer_preview || (
                        <p className="text-gray-500 italic">
                          Original answer preview not available
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Model Answer */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 pb-3 border-b border-emerald-200">
                    <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                    <h3 className="font-semibold text-emerald-800">AI-Enhanced Model Answer</h3>
                    <span className="ml-auto px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">
                      Topper Quality
                    </span>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 min-h-[400px]">
                    <div className="prose prose-sm max-w-none text-gray-700 
                      prose-headings:text-emerald-800 prose-headings:font-semibold
                      prose-strong:text-emerald-900
                      prose-ul:text-gray-700 prose-li:text-gray-700">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {currentQuestion.model_answer}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* Model Only View */
              <div className="max-w-4xl mx-auto">
                <div className="bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-8">
                  <div className="prose prose-lg max-w-none text-gray-700 
                    prose-headings:text-emerald-800 prose-headings:font-semibold
                    prose-strong:text-emerald-900
                    prose-ul:text-gray-700 prose-li:text-gray-700
                    prose-p:leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {currentQuestion.model_answer}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            )}

            {/* Improvements Applied */}
            <div className="mt-8 grid md:grid-cols-2 gap-6">
              {/* Improvements Applied */}
              {currentQuestion.improvements_applied && currentQuestion.improvements_applied.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <CheckCircleIcon className="h-5 w-5 text-blue-600" />
                    <h4 className="font-semibold text-blue-800">Improvements Applied</h4>
                  </div>
                  <ul className="space-y-2">
                    {currentQuestion.improvements_applied.map((imp, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-blue-700">
                        <span className="text-blue-400 mt-1">✓</span>
                        <span>{imp}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Key Additions */}
              {currentQuestion.key_additions && currentQuestion.key_additions.length > 0 && (
                <div className="bg-purple-50 border border-purple-200 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <LightBulbIcon className="h-5 w-5 text-purple-600" />
                    <h4 className="font-semibold text-purple-800">Key Additions</h4>
                  </div>
                  <ul className="space-y-2">
                    {currentQuestion.key_additions.map((addition, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-purple-700">
                        <span className="text-purple-400 mt-1">+</span>
                        <span>{addition}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="mt-8 pt-6 border-t border-gray-200 flex items-center justify-between text-sm text-gray-500">
              <span>
                Generated: {new Date(modelAnswerData.generated_at).toLocaleString()}
              </span>
              {modelAnswerData.cached && (
                <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                  Cached result
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelAnswerComparison;

