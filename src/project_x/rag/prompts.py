"""Grounding prompt templates for source-constrained LLM generation.

Formats retrieved document chunks into numbered, page-labeled reference blocks
and constructs strict system/user prompts that enforce inline citation behavior.
"""

from project_x.ingestion.models import DocumentChunk


GROUNDED_SYSTEM_PROMPT = """You are a precise research assistant that answers questions using the provided source documents.

Rules you must follow:
1. Base your answer on the source documents below whenever they are relevant to the user's query.
2. For greetings, polite pleasantries (e.g., "hello", "hi", "thanks"), or questions about your capabilities, respond politely and briefly introduce yourself as Project X and offer to assist with the uploaded documents.
3. For factual questions, cite your sources inline using bracketed numbers like [1], [2] immediately after each claim.
4. If multiple sources support a claim, cite all of them like [1, 2].
5. If the user asks a specific question and the sources do not contain enough information, say: "I could not find this information in the uploaded documents."
6. Never fabricate information. Never hallucinate facts not in the sources.
7. Keep your answer clear, well-structured, and directly relevant to the question.
8. Use markdown formatting (bold, lists, headers) when it improves readability."""


def format_sources_for_prompt(
    chunks: list[tuple[DocumentChunk, float]],
) -> str:
    """Serialize re-ranked chunks into numbered reference blocks for injection.

    Args:
        chunks: List of (DocumentChunk, rerank_score) tuples from the retriever.

    Returns:
        Formatted string with numbered source blocks including location metadata.
    """
    if not chunks:
        return ""

    blocks: list[str] = []
    for idx, (chunk, score) in enumerate(chunks, 1):
        meta = chunk.metadata
        if meta.page is not None:
            location = f"Page {meta.page}"
        elif meta.section:
            location = f"Section: {meta.section}"
        else:
            location = "Unknown location"

        block = (
            f"[{idx}] Source: {meta.source} ({location})\n"
            f'Content: "{chunk.text.strip()}"'
        )
        blocks.append(block)

    return "\n\n".join(blocks)


def format_grounded_user_prompt(
    query: str,
    formatted_sources: str,
    formatted_history: str = "",
) -> str:
    """Assemble the full user prompt with optional history and retrieved sources.

    Args:
        query: The user's current question (already contextualized by the rewriter).
        formatted_sources: Pre-formatted source reference blocks.
        formatted_history: Optional Human/Assistant formatted conversation history.

    Returns:
        Complete user prompt string ready for LLM invocation.
    """
    parts: list[str] = []

    if formatted_history:
        parts.append(f"Conversation history:\n{formatted_history}\n")

    parts.append(f"Source documents:\n{formatted_sources}\n")
    parts.append(f"Question: {query}")

    return "\n".join(parts)
