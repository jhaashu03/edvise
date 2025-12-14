"""
Output Format Templates

Structured output instructions for consistent, parseable responses.
These ensure the AI produces well-organized, actionable content.
"""

# =============================================================================
# CHAT OUTPUT FORMAT - For conversational interactions
# =============================================================================

CHAT_OUTPUT_FORMAT = """OUTPUT FORMAT FOR RESPONSES:
- Use clear headings and bullet points for readability
- Bold key terms and concepts using **term**
- Keep paragraphs short (3-4 sentences max)
- Include relevant article numbers, case names, or dates where applicable
- End with a brief summary or next steps when appropriate

For concept explanations:
1. Start with a one-line definition
2. Explain the context/background
3. Give 2-3 relevant examples
4. Connect to UPSC relevance

For question discussions:
1. Identify the question type (analytical, factual, opinion-based)
2. Outline the key dimensions to cover
3. Suggest a structure for answering
4. Mention relevant sources/reading"""

# =============================================================================
# ANSWER EVALUATION OUTPUT FORMAT - For scoring and feedback
# =============================================================================

ANSWER_EVALUATION_OUTPUT_FORMAT = """OUTPUT FORMAT FOR ANSWER EVALUATION:

Provide your evaluation in the following structured format:

## Overall Score: X/10

## Dimension Scores:
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Content Accuracy | X/10 | 30% | X.X |
| Structure & Organization | X/10 | 20% | X.X |
| Analysis & Depth | X/10 | 25% | X.X |
| Examples & Evidence | X/10 | 15% | X.X |
| Language & Presentation | X/10 | 10% | X.X |

## Strengths (What Worked Well):
- [Specific strength 1 with quote/reference from answer]
- [Specific strength 2]

## Areas for Improvement:
- [Specific gap 1]: [How to improve]
- [Specific gap 2]: [How to improve]

## Missing Elements:
- [Key point/concept not covered]

## Model Answer Framework:
[Brief outline of an ideal answer structure]

## Action Items:
1. [Concrete step to improve]
2. [Resource/topic to study]
3. [Practice suggestion]"""

# =============================================================================
# STRUCTURED FEEDBACK FORMAT - For quick feedback
# =============================================================================

STRUCTURED_FEEDBACK_FORMAT = """QUICK FEEDBACK FORMAT:

**Score: X/10**

✅ **Did Well:**
- Point 1
- Point 2

⚠️ **Improve:**
- Point 1
- Point 2

📚 **Study:**
- Topic/Resource to review"""

# =============================================================================
# JSON OUTPUT FORMAT - For programmatic parsing
# =============================================================================

JSON_EVALUATION_FORMAT = """OUTPUT AS JSON:
{
    "overall_score": <number 0-10>,
    "dimension_scores": {
        "content_accuracy": <number>,
        "structure": <number>,
        "analysis": <number>,
        "examples": <number>,
        "language": <number>
    },
    "strengths": ["<string>", ...],
    "improvements": ["<string>", ...],
    "missing_elements": ["<string>", ...],
    "action_items": ["<string>", ...]
}"""

