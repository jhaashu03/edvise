"""
Enhanced PYQ Scoring System
Intelligent multi-factor scoring for better PYQ search results
"""
from typing import List, Dict, Any, Optional
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedPYQScorer:
    """Advanced scoring system for PYQ search results"""
    
    def __init__(self):
        # UPSC topic importance weights
        self.topic_importance = {
            'constitution': 1.2,
            'governance': 1.15,
            'freedom struggle': 1.1,
            'polity': 1.15,
            'economy': 1.1,
            'history': 1.05,
            'geography': 1.0,
            'current affairs': 1.3,  # Very important for UPSC
            'ethics': 1.2,
            'international relations': 1.15,
            'environment': 1.1,
            'science technology': 1.05
        }
        
        # Subject priority for UPSC
        self.subject_weights = {
            'General Studies Paper 1': 1.1,
            'General Studies Paper 2': 1.15,  # Governance focus
            'General Studies Paper 3': 1.05,
            'General Studies Paper 4': 1.2,   # Ethics - very important
            'Essay': 1.25,  # Essay questions are gold
            'Optional': 0.9
        }
        
        # Recent years get higher weight
        current_year = datetime.now().year
        self.year_weights = {
            year: max(0.8, 1.0 - (current_year - year) * 0.02) 
            for year in range(2013, current_year + 1)
        }
        
        # Query specificity patterns
        self.specific_patterns = [
            r'\b\d{4}\b',  # Years
            r'\barticle\s+\d+\b',  # Article numbers
            r'\bact\b',  # Specific acts
            r'\bcommittee\b',  # Committee names
            r'\bscheme\b',  # Government schemes
            r'\bpolicy\b'  # Specific policies
        ]
        
    def calculate_enhanced_score(
        self, 
        base_similarity: float,
        query: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate enhanced score using multiple factors
        
        Args:
            base_similarity: Original cosine similarity score
            query: Search query text
            result: PYQ result with metadata
            
        Returns:
            Enhanced result with improved scoring
        """
        try:
            # Start with base similarity
            enhanced_score = base_similarity
            score_factors = {
                'base_similarity': base_similarity,
                'topic_boost': 0.0,
                'subject_boost': 0.0,
                'year_boost': 0.0,
                'query_specificity_boost': 0.0,
                'exact_match_boost': 0.0
            }
            
            # 1. Topic Importance Boost
            topic_boost = self._calculate_topic_boost(query, result)
            enhanced_score += topic_boost
            score_factors['topic_boost'] = topic_boost
            
            # 2. Subject Area Boost
            subject_boost = self._calculate_subject_boost(result)
            enhanced_score += subject_boost
            score_factors['subject_boost'] = subject_boost
            
            # 3. Year Relevance Boost
            year_boost = self._calculate_year_boost(result)
            enhanced_score += year_boost
            score_factors['year_boost'] = year_boost
            
            # 4. Query Specificity Adjustment
            specificity_boost = self._calculate_query_specificity_boost(query, base_similarity)
            enhanced_score += specificity_boost
            score_factors['query_specificity_boost'] = specificity_boost
            
            # 5. Exact Match Bonus
            exact_match_boost = self._calculate_exact_match_boost(query, result)
            enhanced_score += exact_match_boost
            score_factors['exact_match_boost'] = exact_match_boost
            
            # Normalize to reasonable range (0-1)
            enhanced_score = min(1.0, max(0.0, enhanced_score))
            
            # Add scoring details to result
            result_copy = result.copy()
            result_copy['similarity_score'] = enhanced_score
            result_copy['original_similarity'] = base_similarity
            result_copy['score_factors'] = score_factors
            result_copy['score_explanation'] = self._generate_score_explanation(score_factors)
            
            return result_copy
            
        except Exception as e:
            logger.error(f"Error calculating enhanced score: {e}")
            # Return original result if scoring fails
            return result
    
    def _calculate_topic_boost(self, query: str, result: Dict[str, Any]) -> float:
        """Calculate boost based on topic importance"""
        query_lower = query.lower()
        question_lower = result.get('question', '').lower()
        
        boost = 0.0
        for topic, weight in self.topic_importance.items():
            if topic in query_lower:
                # Topic mentioned in query
                if topic in question_lower:
                    # Topic also in question - strong match
                    boost += (weight - 1.0) * 0.15  # Convert weight to boost
                else:
                    # Topic in query but not question - smaller boost
                    boost += (weight - 1.0) * 0.05
                    
        return min(boost, 0.2)  # Cap boost at 0.2
    
    def _calculate_subject_boost(self, result: Dict[str, Any]) -> float:
        """Calculate boost based on subject importance"""
        subject = result.get('subject', '')
        paper = result.get('paper', '')
        
        # Combine subject and paper for full subject identification
        full_subject = f"{subject} {paper}".strip()
        
        for subject_pattern, weight in self.subject_weights.items():
            if subject_pattern.lower() in full_subject.lower():
                return (weight - 1.0) * 0.1  # Convert weight to boost
                
        return 0.0
    
    def _calculate_year_boost(self, result: Dict[str, Any]) -> float:
        """Calculate boost based on year relevance"""
        year = result.get('year')
        if not year:
            return 0.0
            
        weight = self.year_weights.get(year, 0.8)
        return (weight - 1.0) * 0.1  # Convert weight to boost
    
    def _calculate_query_specificity_boost(self, query: str, base_similarity: float) -> float:
        """Adjust score based on query specificity"""
        specificity_score = 0
        
        # Check for specific patterns
        for pattern in self.specific_patterns:
            if re.search(pattern, query.lower()):
                specificity_score += 1
                
        # Specific queries should have higher thresholds, broad queries get boost
        if specificity_score == 0:  # Broad query
            # Boost broad queries with lower similarity
            if base_similarity < 0.25:
                return 0.1  # Give broad queries a chance
        else:  # Specific query
            # Specific queries should meet higher standards
            if base_similarity < 0.3:
                return -0.05  # Slight penalty for low similarity on specific queries
                
        return 0.0
    
    def _calculate_exact_match_boost(self, query: str, result: Dict[str, Any]) -> float:
        """Calculate boost for exact phrase matches"""
        query_lower = query.lower()
        question_lower = result.get('question', '').lower()
        
        # Exact phrase match
        if query_lower in question_lower:
            return 0.15
            
        # Multiple word matches
        query_words = set(query_lower.split())
        question_words = set(question_lower.split())
        
        if len(query_words) > 1:
            common_words = query_words.intersection(question_words)
            match_ratio = len(common_words) / len(query_words)
            
            if match_ratio > 0.7:  # More than 70% words match
                return 0.1
            elif match_ratio > 0.5:  # More than 50% words match
                return 0.05
                
        return 0.0
    
    def _generate_score_explanation(self, score_factors: Dict[str, float]) -> str:
        """Generate human-readable explanation of scoring"""
        explanations = []
        
        if score_factors['topic_boost'] > 0:
            explanations.append(f"Topic relevance: +{score_factors['topic_boost']:.2f}")
            
        if score_factors['subject_boost'] > 0:
            explanations.append(f"Subject importance: +{score_factors['subject_boost']:.2f}")
            
        if score_factors['year_boost'] > 0:
            explanations.append(f"Recent year: +{score_factors['year_boost']:.2f}")
        elif score_factors['year_boost'] < 0:
            explanations.append(f"Older year: {score_factors['year_boost']:.2f}")
            
        if score_factors['query_specificity_boost'] > 0:
            explanations.append(f"Broad query boost: +{score_factors['query_specificity_boost']:.2f}")
        elif score_factors['query_specificity_boost'] < 0:
            explanations.append(f"Specific query penalty: {score_factors['query_specificity_boost']:.2f}")
            
        if score_factors['exact_match_boost'] > 0:
            explanations.append(f"Exact match: +{score_factors['exact_match_boost']:.2f}")
            
        return "; ".join(explanations) if explanations else "Base similarity only"
    
    def rank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Rank results using enhanced scoring
        
        Args:
            results: List of PYQ results with base similarity scores
            query: Search query
            
        Returns:
            Ranked results with enhanced scores
        """
        enhanced_results = []
        
        for result in results:
            base_similarity = result.get('similarity_score', 0.0)
            enhanced_result = self.calculate_enhanced_score(base_similarity, query, result)
            enhanced_results.append(enhanced_result)
        
        # Sort by enhanced similarity score
        enhanced_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        # Log enhanced scoring results with safety check for empty results
        if enhanced_results:
            logger.info(f"Enhanced scoring: {len(results)} results processed, "
                       f"top score: {enhanced_results[0]['similarity_score']:.3f} "
                       f"(was {enhanced_results[0]['original_similarity']:.3f})")
        else:
            logger.info(f"Enhanced scoring: {len(results)} results processed, but no results returned")
        
        return enhanced_results

# Global instance
enhanced_scorer = EnhancedPYQScorer()
