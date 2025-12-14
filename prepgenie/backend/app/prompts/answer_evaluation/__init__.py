"""
Answer Evaluation Prompts

Subject-specific evaluation prompts for UPSC Mains answer assessment.
Each subject has tailored rubrics, expectations, and evaluation criteria.
"""

from typing import Optional
from enum import Enum

from .base import EVALUATION_BASE_PROMPT, SCORING_RUBRIC, UPSC_MARKING_GUIDELINES
from .gs1 import GS1_PROMPT, GS1_TOPICS, GS1_RUBRIC
from .gs2 import GS2_PROMPT, GS2_TOPICS, GS2_RUBRIC
from .gs3 import GS3_PROMPT, GS3_TOPICS, GS3_RUBRIC
from .gs4 import GS4_PROMPT, GS4_TOPICS, GS4_RUBRIC
from .anthropology import ANTHROPOLOGY_PROMPT, ANTHROPOLOGY_TOPICS, ANTHROPOLOGY_RUBRIC


class SubjectType(str, Enum):
    """UPSC Mains subject types"""
    GS1 = "gs1"  # History, Geography, Society
    GS2 = "gs2"  # Polity, Governance, IR
    GS3 = "gs3"  # Economy, Environment, S&T, Security
    GS4 = "gs4"  # Ethics, Integrity, Aptitude
    ANTHROPOLOGY = "anthropology"  # Optional subject
    GENERAL = "general"  # Fallback


# Subject prompt mapping
SUBJECT_PROMPTS = {
    SubjectType.GS1: GS1_PROMPT,
    SubjectType.GS2: GS2_PROMPT,
    SubjectType.GS3: GS3_PROMPT,
    SubjectType.GS4: GS4_PROMPT,
    SubjectType.ANTHROPOLOGY: ANTHROPOLOGY_PROMPT,
    SubjectType.GENERAL: EVALUATION_BASE_PROMPT,
}

SUBJECT_RUBRICS = {
    SubjectType.GS1: GS1_RUBRIC,
    SubjectType.GS2: GS2_RUBRIC,
    SubjectType.GS3: GS3_RUBRIC,
    SubjectType.GS4: GS4_RUBRIC,
    SubjectType.ANTHROPOLOGY: ANTHROPOLOGY_RUBRIC,
    SubjectType.GENERAL: SCORING_RUBRIC,
}


def get_evaluation_prompt(
    subject: SubjectType = SubjectType.GENERAL,
    question: Optional[str] = None,
    word_limit: Optional[int] = None,
    include_rubric: bool = True,
    **kwargs
) -> str:
    """
    Get a subject-specific evaluation prompt.
    
    Args:
        subject: Subject type (gs1, gs2, gs3, gs4, anthropology, general)
        question: The specific question being evaluated
        word_limit: Expected word limit for the answer
        include_rubric: Whether to include detailed scoring rubric
    
    Returns:
        Complete evaluation prompt for the subject
    """
    parts = []
    
    # Base evaluation framework
    parts.append(EVALUATION_BASE_PROMPT)
    
    # Subject-specific prompt
    subject_prompt = SUBJECT_PROMPTS.get(subject, EVALUATION_BASE_PROMPT)
    if subject_prompt != EVALUATION_BASE_PROMPT:
        parts.append(subject_prompt)
    
    # UPSC marking guidelines
    parts.append(UPSC_MARKING_GUIDELINES)
    
    # Subject-specific rubric
    if include_rubric:
        rubric = SUBJECT_RUBRICS.get(subject, SCORING_RUBRIC)
        parts.append(rubric)
    
    # Question context
    if question:
        parts.append(f"\n## QUESTION BEING EVALUATED:\n{question}")
    
    if word_limit:
        parts.append(f"\nEXPECTED WORD LIMIT: {word_limit} words")
        parts.append("Evaluate whether the answer appropriately addresses the scope given this word limit.")
    
    return "\n\n".join(parts)


def _get_subject_keywords():
    """Get subject keywords for detection."""
    # GS1 keywords - History, Geography, Culture, Society
    gs1_keywords = ["history", "geography", "society", "culture", "art", "heritage", 
                    "ancient", "medieval", "modern india", "freedom movement",
                    "climate", "earthquake", "river", "monsoon", "population",
                    "women", "caste", "tribe", "urbanization", "social",
                    # Additional history terms
                    "colonial", "british", "mughal", "independence", "revolt", "reform",
                    # Additional geography terms
                    "physiography", "soil", "vegetation", "mineral", "ocean",
                    # Additional society terms
                    "diversity", "communalism", "regionalism", "secularism", "globalization"]
    
    # GS2 keywords - Polity, Governance, IR, Social Justice
    gs2_keywords = ["constitution", "polity", "governance", "parliament", "judiciary",
                    "fundamental rights", "dpsp", "president", "prime minister",
                    "federalism", "local government", "panchayat", "election",
                    "international relations", "foreign policy", "bilateral",
                    "ngo", "shg", "civil society", "pressure groups",
                    # Additional governance & policy terms
                    "statutory", "regulatory", "tribunal", "commission", "authority",
                    "welfare scheme", "social justice", "vulnerable section",
                    "e-governance", "transparency", "accountability", "rti",
                    "article", "amendment", "ordinance"]  # Removed 'act', 'bill' - too generic
    
    # GS3 keywords - Economy, S&T, Environment, Security
    gs3_keywords = ["economy", "growth", "development", "agriculture", "industry",
                    "infrastructure", "investment", "budget", "fiscal", "monetary",
                    "environment", "biodiversity", "pollution", "climate change",
                    "technology", "science", "cyber", "security", "terrorism",
                    "border", "naxalism", "money laundering",
                    # Land reforms (explicitly in GS3 syllabus)
                    "land reform", "land titling", "land title", "conclusive title", "presumptive",
                    "land acquisition", "land record",
                    # Food security & PDS
                    "food security", "pds", "buffer stock", "msp", "subsidy",
                    # Infrastructure & energy - STRONG GS3 indicators
                    "port", "port authority", "airport", "railway", "energy", "renewable", "solar", "nuclear",
                    # Circular/Green economy
                    "circular economy", "green budget", "green finance", "sustainable development",
                    # Disaster management
                    "disaster", "flood", "drought", "cyclone"]
    
    # GS4 keywords - Ethics
    gs4_keywords = ["ethics", "integrity", "aptitude", "moral", "value",
                    "attitude", "emotional intelligence", "conscience",
                    "civil service", "probity", "corruption", "conflict of interest",
                    "case study", "ethical dilemma", "decision making"]
    
    # Anthropology keywords
    anthro_keywords = ["anthropology", "tribe", "tribal", "kinship", "marriage",
                       "ethnography", "culture", "primitive", "evolution",
                       "race", "ethnicity", "religion", "totemism"]
    
    return {
        SubjectType.GS1: gs1_keywords,
        SubjectType.GS2: gs2_keywords,
        SubjectType.GS3: gs3_keywords,
        SubjectType.GS4: gs4_keywords,
        SubjectType.ANTHROPOLOGY: anthro_keywords,
    }


def detect_subject_tags(question: str) -> dict:
    """
    Detect all subject tags for a question with confidence scores.
    Useful for questions that span multiple subjects.
    
    Args:
        question: The question text
    
    Returns:
        Dict with subject tags and scores:
        {
            "primary_subject": SubjectType,
            "tags": [{"subject": SubjectType, "score": int, "confidence": str}],
            "is_multi_subject": bool,
            "detected_keywords": {SubjectType: [matched_keywords]}
        }
    """
    question_lower = question.lower()
    keywords_map = _get_subject_keywords()
    
    # Score each subject and track matched keywords
    scores = {}
    matched = {}
    
    for subject, keywords in keywords_map.items():
        matched_kw = [kw for kw in keywords if kw in question_lower]
        scores[subject] = len(matched_kw)
        if matched_kw:
            matched[subject] = matched_kw
    
    # Calculate total for confidence
    total = sum(scores.values())
    
    # Build tags list
    tags = []
    for subject, score in scores.items():
        if score > 0:
            confidence = "high" if score >= 3 else ("medium" if score >= 2 else "low")
            tags.append({
                "subject": subject,
                "score": score,
                "confidence": confidence,
                "keywords": matched.get(subject, [])
            })
    
    # Sort by score (descending)
    tags.sort(key=lambda x: x["score"], reverse=True)
    
    # Determine primary subject
    if not tags:
        primary = SubjectType.GENERAL
    else:
        primary = tags[0]["subject"]
    
    # Check if multi-subject (second subject has significant score)
    is_multi = len(tags) > 1 and tags[1]["score"] >= 2
    
    return {
        "primary_subject": primary,
        "tags": tags,
        "is_multi_subject": is_multi,
        "detected_keywords": matched
    }


def detect_subject_from_question(question: str) -> SubjectType:
    """
    Auto-detect primary subject type from question content.
    
    Args:
        question: The question text
    
    Returns:
        Detected SubjectType (primary subject)
    """
    result = detect_subject_tags(question)
    return result["primary_subject"]


__all__ = [
    "SubjectType",
    "get_evaluation_prompt",
    "detect_subject_from_question",
    "detect_subject_tags",  # Enhanced detection with multi-subject support
    "EVALUATION_BASE_PROMPT",
    "SCORING_RUBRIC",
    "UPSC_MARKING_GUIDELINES",
    "GS1_PROMPT",
    "GS2_PROMPT", 
    "GS3_PROMPT",
    "GS4_PROMPT",
    "ANTHROPOLOGY_PROMPT",
]

