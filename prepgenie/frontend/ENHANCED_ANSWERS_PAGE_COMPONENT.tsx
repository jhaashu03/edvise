// Enhanced AnswersPage.tsx with Markdown Support
// Add this to your frontend/src/pages/AnswersPage.tsx

import ReactMarkdown from 'react-markdown';

// Add this component for better evaluation display
const EnhancedEvaluationDisplay = ({ evaluation }: { evaluation: AnswerEvaluation }) => {
  return (
    <div className="bg-white rounded-lg shadow-lg p-6 mt-4">
      <div className="prose max-w-none">
        <ReactMarkdown
          className="markdown-content"
          components={{
            h1: ({ children }) => <h1 className="text-2xl font-bold text-blue-800 mb-4">{children}</h1>,
            h2: ({ children }) => <h2 className="text-xl font-semibold text-blue-700 mb-3 mt-6">{children}</h2>,
            h3: ({ children }) => <h3 className="text-lg font-medium text-blue-600 mb-2 mt-4">{children}</h3>,
            p: ({ children }) => <p className="text-gray-700 mb-3 leading-relaxed">{children}</p>,
            ul: ({ children }) => <ul className="list-disc pl-6 mb-4 space-y-1">{children}</ul>,
            li: ({ children }) => <li className="text-gray-700">{children}</li>,
            strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
            code: ({ children }) => (
              <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-blue-800">
                {children}
              </code>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-600 my-4">
                {children}
              </blockquote>
            ),
          }}
        >
          {evaluation.feedback}
        </ReactMarkdown>
      </div>
      
      {/* Score Summary */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-800">
              {evaluation.score.toFixed(1)}/{evaluation.maxScore}
            </div>
            <div className="text-sm text-gray-600">Overall Score</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {evaluation.structure.toFixed(1)}/10
            </div>
            <div className="text-sm text-gray-600">Structure</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {evaluation.coverage.toFixed(1)}/10
            </div>
            <div className="text-sm text-gray-600">Coverage</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {evaluation.tone.toFixed(1)}/10
            </div>
            <div className="text-sm text-gray-600">Tone</div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Replace the existing evaluation display in your AnswersPage with:
{answer.evaluation ? (
  <EnhancedEvaluationDisplay evaluation={answer.evaluation} />
) : (
  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4">
    <div className="flex items-center">
      <ClockIcon className="w-5 h-5 text-yellow-600 mr-2" />
      <span className="text-yellow-800">Evaluation in progress...</span>
    </div>
  </div>
)}

// Add CSS for better markdown styling (add to your CSS file):
.markdown-content {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.markdown-content h1 {
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 0.5rem;
}

.markdown-content h2 {
  border-bottom: 1px solid #f3f4f6;
  padding-bottom: 0.25rem;
}

.markdown-content code {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
}

.markdown-content pre {
  background-color: #1a202c;
  color: #f7fafc;
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
}

.markdown-content blockquote {
  background-color: #f7fafc;
}
