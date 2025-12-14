import React, { useState } from 'react';
import { AnswerEvaluation } from '../types';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  LightBulbIcon,
  DocumentTextIcon,
  ChartBarIcon,
  SparklesIcon,
  AcademicCapIcon,
  PresentationChartLineIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  BookOpenIcon,
  BeakerIcon,
  GlobeAltIcon,
  ArrowTrendingUpIcon,
} from '@heroicons/react/24/outline';
import { StarIcon } from '@heroicons/react/24/solid';

interface ActionableEvaluationCardProps {
  evaluation: AnswerEvaluation;
  questionNumber?: number;
  questionText?: string;
}

const getVerdictConfig = (verdict: string) => {
  switch (verdict) {
    case 'FULLY MET':
      return {
        icon: CheckCircleIcon,
        bg: 'bg-emerald-50',
        border: 'border-emerald-200',
        text: 'text-emerald-700',
        badge: 'bg-emerald-100 text-emerald-800',
        gradient: 'from-emerald-500 to-teal-500',
      };
    case 'PARTIALLY MET':
      return {
        icon: ExclamationTriangleIcon,
        bg: 'bg-amber-50',
        border: 'border-amber-200',
        text: 'text-amber-700',
        badge: 'bg-amber-100 text-amber-800',
        gradient: 'from-amber-500 to-orange-500',
      };
    default:
      return {
        icon: XCircleIcon,
        bg: 'bg-rose-50',
        border: 'border-rose-200',
        text: 'text-rose-700',
        badge: 'bg-rose-100 text-rose-800',
        gradient: 'from-rose-500 to-red-500',
      };
  }
};

const getScoreColor = (score: number) => {
  if (score >= 8) return 'text-emerald-600';
  if (score >= 6) return 'text-amber-600';
  return 'text-rose-600';
};

const getScoreGradient = (score: number) => {
  if (score >= 8) return 'from-emerald-500 to-teal-500';
  if (score >= 6) return 'from-amber-500 to-orange-500';
  return 'from-rose-500 to-red-500';
};

export const ActionableEvaluationCard: React.FC<ActionableEvaluationCardProps> = ({
  evaluation,
  questionNumber,
  questionText,
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['verdict', 'improvements']));

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const overallScore = evaluation.overall_score || evaluation.score;
  const maxScore = evaluation.maxScore || 10;
  const verdictConfig = getVerdictConfig(evaluation.demand_analysis?.verdict || 'PARTIALLY MET');
  const VerdictIcon = verdictConfig.icon;

  // Render score stars
  const renderStars = (score: number) => {
    const fullStars = Math.floor(score / 2);
    const hasHalfStar = score % 2 >= 1;
    return (
      <div className="flex items-center gap-0.5">
        {[...Array(5)].map((_, i) => (
          <StarIcon
            key={i}
            className={`w-4 h-4 ${
              i < fullStars
                ? 'text-amber-400'
                : i === fullStars && hasHalfStar
                ? 'text-amber-300'
                : 'text-gray-200'
            }`}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
      {/* Header with Quick Verdict */}
      <div className={`bg-gradient-to-r ${getScoreGradient(overallScore)} p-6`}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {questionNumber && (
              <div className="inline-flex items-center px-3 py-1 bg-white/20 backdrop-blur-sm rounded-full text-white text-sm font-medium mb-3">
                <DocumentTextIcon className="w-4 h-4 mr-1.5" />
                Question {questionNumber}
              </div>
            )}
            {questionText && (
              <p className="text-white/90 text-sm line-clamp-2 mb-3">
                {questionText.substring(0, 100)}...
              </p>
            )}
            {evaluation.quick_verdict && (
              <p className="text-white font-medium text-lg leading-relaxed">
                {evaluation.quick_verdict}
              </p>
            )}
          </div>
          <div className="ml-6 flex flex-col items-center">
            <div className="w-20 h-20 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <span className="text-3xl font-bold text-white">
                {overallScore?.toFixed(1) || 'N/A'}
              </span>
            </div>
            <span className="text-white/80 text-xs mt-2">out of {maxScore}</span>
          </div>
        </div>
      </div>

      {/* Top 3 Improvements - Always Visible */}
      {evaluation.top_3_improvements && evaluation.top_3_improvements.length > 0 && (
        <div className="p-6 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-indigo-100">
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 bg-indigo-100 rounded-lg">
              <ArrowTrendingUpIcon className="w-5 h-5 text-indigo-600" />
            </div>
            <h3 className="font-bold text-indigo-900 text-lg">🎯 Top 3 Priority Improvements</h3>
          </div>
          <div className="space-y-3">
            {evaluation.top_3_improvements.map((improvement, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 bg-white rounded-xl shadow-sm border border-indigo-100"
              >
                <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center font-bold text-white ${
                  index === 0 ? 'bg-gradient-to-r from-indigo-500 to-purple-500' :
                  index === 1 ? 'bg-gradient-to-r from-indigo-400 to-purple-400' :
                  'bg-gradient-to-r from-indigo-300 to-purple-300'
                }`}>
                  {index + 1}
                </div>
                <p className="text-gray-700 text-sm leading-relaxed flex-1">{improvement}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Demand Analysis */}
      {evaluation.demand_analysis && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('demand')}
            className={`w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors ${verdictConfig.bg}`}
          >
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${verdictConfig.badge}`}>
                <VerdictIcon className="w-5 h-5" />
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">Demand Analysis</h3>
                <span className={`text-sm ${verdictConfig.text}`}>
                  {evaluation.demand_analysis.verdict}
                </span>
              </div>
            </div>
            {expandedSections.has('demand') ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {expandedSections.has('demand') && (
            <div className="p-5 pt-0 space-y-4">
              {/* Question Demands */}
              {evaluation.demand_analysis.question_demands?.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-gray-500 mb-2">Question Asked For</h4>
                  <div className="flex flex-wrap gap-2">
                    {evaluation.demand_analysis.question_demands.map((demand, i) => (
                      <span key={i} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm">
                        {demand}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Demands Met */}
              {evaluation.demand_analysis.demands_met?.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-emerald-600 mb-2 flex items-center gap-1">
                    <CheckCircleIcon className="w-4 h-4" /> What You Covered Well
                  </h4>
                  <ul className="space-y-1.5">
                    {evaluation.demand_analysis.demands_met.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-emerald-700 bg-emerald-50 p-2 rounded-lg">
                        <CheckCircleIcon className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Demands Missed */}
              {evaluation.demand_analysis.demands_missed?.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-rose-600 mb-2 flex items-center gap-1">
                    <XCircleIcon className="w-4 h-4" /> What You Missed
                  </h4>
                  <ul className="space-y-1.5">
                    {evaluation.demand_analysis.demands_missed.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-rose-700 bg-rose-50 p-2 rounded-lg">
                        <ExclamationTriangleIcon className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Structure Analysis */}
      {evaluation.structure_analysis && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('structure')}
            className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <ChartBarIcon className="w-5 h-5 text-blue-600" />
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">Structure</h3>
                <span className={`text-sm ${getScoreColor(evaluation.structure_analysis.score)}`}>
                  {evaluation.structure_analysis.score}/10
                </span>
              </div>
            </div>
            {expandedSections.has('structure') ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {expandedSections.has('structure') && (
            <div className="px-5 pb-5 space-y-3">
              {evaluation.structure_analysis.ideal_structure && (
                <div className="p-4 bg-blue-50 rounded-xl">
                  <h4 className="text-xs uppercase tracking-wide text-blue-600 mb-2">💡 Ideal Structure</h4>
                  <p className="text-sm text-blue-800">{evaluation.structure_analysis.ideal_structure}</p>
                </div>
              )}
              {evaluation.structure_analysis.suggestion && (
                <div className="p-4 bg-gray-50 rounded-xl">
                  <h4 className="text-xs uppercase tracking-wide text-gray-600 mb-2">📝 Suggestion</h4>
                  <p className="text-sm text-gray-700">{evaluation.structure_analysis.suggestion}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Examples to Add */}
      {evaluation.examples && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('examples')}
            className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-violet-100 rounded-lg">
                <BookOpenIcon className="w-5 h-5 text-violet-600" />
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">Examples & References</h3>
                <span className="text-sm text-gray-500">
                  {(evaluation.examples.examples_to_add?.length || 0)} suggestions
                </span>
              </div>
            </div>
            {expandedSections.has('examples') ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {expandedSections.has('examples') && (
            <div className="px-5 pb-5 space-y-3">
              {evaluation.examples.examples_to_add?.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-violet-600 mb-2">📚 Examples to Add</h4>
                  <ul className="space-y-2">
                    {evaluation.examples.examples_to_add.map((example, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700 p-3 bg-violet-50 rounded-lg">
                        <SparklesIcon className="w-4 h-4 text-violet-500 mt-0.5 flex-shrink-0" />
                        {example}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {evaluation.examples.constitutional_legal_refs && (
                <div className="p-4 bg-amber-50 rounded-xl border border-amber-200">
                  <h4 className="text-xs uppercase tracking-wide text-amber-700 mb-2">⚖️ Legal/Constitutional Reference</h4>
                  <p className="text-sm text-amber-800 font-medium">{evaluation.examples.constitutional_legal_refs}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Diagram Suggestion */}
      {evaluation.diagram_suggestion && evaluation.diagram_suggestion.can_add_diagram && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('diagram')}
            className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-cyan-100 rounded-lg">
                <PresentationChartLineIcon className="w-5 h-5 text-cyan-600" />
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">📊 Diagram Suggestion</h3>
                <span className="text-sm text-cyan-600 capitalize">
                  {evaluation.diagram_suggestion.diagram_type}
                </span>
              </div>
            </div>
            {expandedSections.has('diagram') ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {expandedSections.has('diagram') && (
            <div className="px-5 pb-5">
              <div className="p-4 bg-gradient-to-r from-cyan-50 to-teal-50 rounded-xl border border-cyan-200">
                <div className="flex items-center gap-2 mb-3">
                  <span className="px-2 py-1 bg-cyan-100 text-cyan-700 rounded-full text-xs font-medium capitalize">
                    {evaluation.diagram_suggestion.diagram_type}
                  </span>
                  <span className="text-xs text-gray-500">
                    Place: {evaluation.diagram_suggestion.where_to_place}
                  </span>
                </div>
                <p className="text-sm text-gray-700">{evaluation.diagram_suggestion.diagram_description}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Value Additions - Topper Tips */}
      {evaluation.value_additions && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('value')}
            className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors bg-gradient-to-r from-amber-50/50 to-yellow-50/50"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-r from-amber-100 to-yellow-100 rounded-lg">
                <AcademicCapIcon className="w-5 h-5 text-amber-600" />
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">🏆 Value Additions & Topper Tips</h3>
                <span className={`text-sm ${getScoreColor(evaluation.value_additions.score)}`}>
                  {evaluation.value_additions.score}/10
                </span>
              </div>
            </div>
            {expandedSections.has('value') ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {expandedSections.has('value') && (
            <div className="px-5 pb-5 space-y-4">
              {/* Topper Tips */}
              {evaluation.value_additions.topper_tips?.length > 0 && (
                <div className="p-4 bg-gradient-to-r from-amber-50 to-yellow-50 rounded-xl border border-amber-200">
                  <h4 className="text-xs uppercase tracking-wide text-amber-700 mb-3 flex items-center gap-1">
                    <StarIcon className="w-4 h-4 text-amber-500" /> What Toppers Would Add
                  </h4>
                  <ul className="space-y-2">
                    {evaluation.value_additions.topper_tips.map((tip, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-amber-800">
                        <SparklesIcon className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                        {tip}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Committee Report */}
              {evaluation.value_additions.committee_report && (
                <div className="p-3 bg-gray-50 rounded-lg flex items-start gap-3">
                  <BeakerIcon className="w-5 h-5 text-gray-500 flex-shrink-0" />
                  <div>
                    <h4 className="text-xs uppercase tracking-wide text-gray-500 mb-1">Committee/Report to Cite</h4>
                    <p className="text-sm text-gray-800 font-medium">{evaluation.value_additions.committee_report}</p>
                  </div>
                </div>
              )}
              
              {/* International Comparison */}
              {evaluation.value_additions.international_comparison && (
                <div className="p-3 bg-blue-50 rounded-lg flex items-start gap-3">
                  <GlobeAltIcon className="w-5 h-5 text-blue-500 flex-shrink-0" />
                  <div>
                    <h4 className="text-xs uppercase tracking-wide text-blue-500 mb-1">International Example</h4>
                    <p className="text-sm text-blue-800">{evaluation.value_additions.international_comparison}</p>
                  </div>
                </div>
              )}
              
              {/* Way Forward */}
              {evaluation.value_additions.way_forward && (
                <div className="p-3 bg-emerald-50 rounded-lg flex items-start gap-3">
                  <ArrowTrendingUpIcon className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                  <div>
                    <h4 className="text-xs uppercase tracking-wide text-emerald-500 mb-1">Way Forward Points</h4>
                    <p className="text-sm text-emerald-800">{evaluation.value_additions.way_forward}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Presentation */}
      {evaluation.presentation && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('presentation')}
            className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-pink-100 rounded-lg">
                <DocumentTextIcon className="w-5 h-5 text-pink-600" />
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">Presentation & Formatting</h3>
                <span className={`text-sm ${getScoreColor(evaluation.presentation.score)}`}>
                  {evaluation.presentation.score}/10
                </span>
              </div>
            </div>
            {expandedSections.has('presentation') ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {expandedSections.has('presentation') && (
            <div className="px-5 pb-5 space-y-3">
              {evaluation.presentation.word_count_assessment && (
                <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                  <span className="text-xs uppercase tracking-wide text-gray-500">Word Count:</span>
                  <span className={`text-sm font-medium ${
                    evaluation.presentation.word_count_assessment.includes('Appropriate') 
                      ? 'text-emerald-600' 
                      : 'text-amber-600'
                  }`}>
                    {evaluation.presentation.word_count_assessment}
                  </span>
                </div>
              )}
              {evaluation.presentation.formatting_tips && (
                <div className="p-3 bg-pink-50 rounded-lg">
                  <h4 className="text-xs uppercase tracking-wide text-pink-600 mb-1">✨ Formatting Tips</h4>
                  <p className="text-sm text-pink-800">{evaluation.presentation.formatting_tips}</p>
                </div>
              )}
              {evaluation.presentation.conclusion_quality && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <h4 className="text-xs uppercase tracking-wide text-gray-500 mb-1">📌 Conclusion Quality</h4>
                  <p className="text-sm text-gray-700">{evaluation.presentation.conclusion_quality}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Content Quality - Missing Facts & Keywords */}
      {evaluation.content_quality && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => toggleSection('content')}
            className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <LightBulbIcon className="w-5 h-5 text-orange-600" />
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">Content Quality</h3>
                <span className="text-sm text-gray-500">
                  {(evaluation.content_quality.facts_missing?.length || 0) + (evaluation.content_quality.keywords_to_add?.length || 0)} suggestions
                </span>
              </div>
            </div>
            {expandedSections.has('content') ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {expandedSections.has('content') && (
            <div className="px-5 pb-5 space-y-4">
              {/* Missing Facts */}
              {evaluation.content_quality.facts_missing?.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-orange-600 mb-2">📊 Missing Facts/Data</h4>
                  <ul className="space-y-2">
                    {evaluation.content_quality.facts_missing.map((fact, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700 p-2 bg-orange-50 rounded-lg">
                        <span className="text-orange-500">•</span>
                        {fact}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Current Affairs Link */}
              {evaluation.content_quality.current_affairs_link && (
                <div className="p-3 bg-blue-50 rounded-lg">
                  <h4 className="text-xs uppercase tracking-wide text-blue-600 mb-1">📰 Current Affairs Link</h4>
                  <p className="text-sm text-blue-800">{evaluation.content_quality.current_affairs_link}</p>
                </div>
              )}
              
              {/* Keywords to Add */}
              {evaluation.content_quality.keywords_to_add?.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-gray-600 mb-2">🔑 UPSC Keywords to Integrate</h4>
                  <div className="flex flex-wrap gap-2">
                    {evaluation.content_quality.keywords_to_add.map((keyword, i) => (
                      <span key={i} className="px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Dimensional Scores Overview */}
      {evaluation.dimensional_scores && Object.keys(evaluation.dimensional_scores).length > 0 && (
        <div>
          <button
            onClick={() => toggleSection('dimensional')}
            className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gray-100 rounded-lg">
                <ChartBarIcon className="w-5 h-5 text-gray-600" />
              </div>
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">13-Dimensional Breakdown</h3>
                <span className="text-sm text-gray-500">Detailed scores across all dimensions</span>
              </div>
            </div>
            {expandedSections.has('dimensional') ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-400" />
            )}
          </button>
          
          {expandedSections.has('dimensional') && (
            <div className="px-5 pb-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(evaluation.dimensional_scores).map(([dimension, data]) => (
                  <div key={dimension} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        {dimension.replace(/_/g, ' ')}
                      </span>
                      <span className={`text-sm font-bold ${getScoreColor(data.score)}`}>
                        {data.score}/10
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                      <div
                        className={`h-2 rounded-full bg-gradient-to-r ${getScoreGradient(data.score)}`}
                        style={{ width: `${(data.score / 10) * 100}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-600 line-clamp-2">{data.feedback}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Subject Badge */}
      {evaluation.detected_subject && (
        <div className="p-4 bg-gray-50 flex items-center justify-between">
          <span className="text-xs text-gray-500">Subject Detected</span>
          <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-medium uppercase">
            {evaluation.detected_subject}
          </span>
        </div>
      )}
    </div>
  );
};

export default ActionableEvaluationCard;

