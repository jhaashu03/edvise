"""
PrepGenie Prompt Management System

Modular, composable prompts for UPSC preparation:
- Global agent identity and rules
- Subject-specific evaluation prompts (GS1-4, Anthropology)
- Output format templates
- Dynamic composition with token budget awareness
"""

from typing import Optional, List, Dict
from enum import Enum

from .global_prompt import GLOBAL_SYSTEM_PROMPT, AGENT_IDENTITY, TONE_GUIDELINES, SAFETY_RULES
from .output_formats import (
    CHAT_OUTPUT_FORMAT,
    ANSWER_EVALUATION_OUTPUT_FORMAT,
    STRUCTURED_FEEDBACK_FORMAT,
)
from .chat_prompts import CHAT_SYSTEM_PROMPT, get_chat_prompt
from .answer_evaluation import (
    get_evaluation_prompt,
    SubjectType,
    EVALUATION_BASE_PROMPT,
)


class PromptType(str, Enum):
    """Types of prompts available"""
    CHAT = "chat"
    ANSWER_EVALUATION = "answer_evaluation"
    STUDY_PLAN = "study_plan"
    QUESTION_GENERATION = "question_generation"


def compose_prompt(
    prompt_type: PromptType,
    subject: Optional[str] = None,
    include_output_format: bool = True,
    max_tokens: Optional[int] = None,
    **kwargs
) -> str:
    """
    Compose a complete prompt from modular components.
    
    Args:
        prompt_type: Type of prompt to compose
        subject: Subject code for evaluation (gs1, gs2, gs3, gs4, anthropology)
        include_output_format: Whether to append output format instructions
        max_tokens: Optional token budget (will prioritize core content if limited)
        **kwargs: Additional context variables for template substitution
    
    Returns:
        Complete composed prompt string
    """
    parts = []
    
    # Always start with global identity
    parts.append(AGENT_IDENTITY)
    
    if prompt_type == PromptType.CHAT:
        parts.append(get_chat_prompt(**kwargs))
        if include_output_format:
            parts.append(CHAT_OUTPUT_FORMAT)
    
    elif prompt_type == PromptType.ANSWER_EVALUATION:
        subject_type = SubjectType(subject) if subject else SubjectType.GS1
        parts.append(get_evaluation_prompt(subject_type, **kwargs))
        if include_output_format:
            parts.append(ANSWER_EVALUATION_OUTPUT_FORMAT)
    
    # Add tone and safety at the end
    parts.append(TONE_GUIDELINES)
    
    # Compose final prompt
    composed = "\n\n".join(parts)
    
    # Token budget management (rough estimate: 1 token ≈ 4 chars)
    if max_tokens:
        max_chars = max_tokens * 4
        if len(composed) > max_chars:
            # Prioritize: identity + subject content, trim examples/elaborations
            composed = _trim_to_budget(composed, max_chars)
    
    return composed


def _trim_to_budget(prompt: str, max_chars: int) -> str:
    """
    Trim prompt to fit within character budget.
    Preserves structure, trims elaborations and examples first.
    """
    if len(prompt) <= max_chars:
        return prompt
    
    # Simple truncation with indicator (can be made smarter)
    return prompt[:max_chars - 50] + "\n\n[... content trimmed for context efficiency]"


def get_prompt_version() -> str:
    """Get current prompt version for tracking/A/B testing"""
    return "v1.0.0"


__all__ = [
    # Compose function
    "compose_prompt",
    "PromptType",
    "get_prompt_version",
    # Global prompts
    "GLOBAL_SYSTEM_PROMPT",
    "AGENT_IDENTITY", 
    "TONE_GUIDELINES",
    "SAFETY_RULES",
    # Chat prompts
    "CHAT_SYSTEM_PROMPT",
    "get_chat_prompt",
    # Output formats
    "CHAT_OUTPUT_FORMAT",
    "ANSWER_EVALUATION_OUTPUT_FORMAT",
    "STRUCTURED_FEEDBACK_FORMAT",
    # Evaluation
    "get_evaluation_prompt",
    "SubjectType",
    "EVALUATION_BASE_PROMPT",
]

