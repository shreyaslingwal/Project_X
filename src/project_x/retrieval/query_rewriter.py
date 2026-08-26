"""History-aware query rewriter using a lightweight local LLM.

Takes ambiguous follow-up queries containing pronouns (it, that, the seller)
and resolves them into standalone search queries using conversation context.
Uses the fast 4B model via Ollama for sub-250ms latency.
"""

import logging
import re
from functools import lru_cache

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from project_x.core.config import settings
from project_x.rag.memory import ChatMessage

logger = logging.getLogger(__name__)

REWRITE_SYSTEM_PROMPT = """You are a query rewriting assistant. Your ONLY job is to rewrite the user's latest question so it is fully self-contained (no pronouns like "it", "that", "they", or references like "the seller" that depend on prior context).

Rules:
1. Use the conversation history to resolve all ambiguous references.
2. Output ONLY the rewritten query. No explanation, no preamble, no quotes.
3. If the query is already self-contained, return it unchanged.
4. Never answer the question. Only rewrite it."""

REWRITE_USER_TEMPLATE = """Conversation history:
{history}

Latest user query: {query}

Rewritten query:"""


class QueryRewriter:
    """Rewrites context-dependent queries into standalone search queries.

    Uses a lightweight 4B model through Ollama for fast inference.
    Falls back gracefully to the raw query if Ollama is unreachable.
    """

    def __init__(self) -> None:
        self._llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.REWRITE_MODEL,
            temperature=0.0,
        )

    def _clean_output(self, raw: str) -> str:
        """Strip conversational filler, labels, and surrounding quotes."""
        text = raw.strip()

        # Remove thinking tags that Qwen 3 sometimes emits
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        # Remove leading labels like "Rewritten query:" or "Here is..."
        text = re.sub(
            r"^(rewritten\s+query\s*[:;]\s*|here\s+is\s+.*?:\s*)",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        # Remove surrounding quotes (single or double)
        if len(text) >= 2 and text[0] in ('"', "'") and text[-1] == text[0]:
            text = text[1:-1].strip()

        return text

    def _format_history(self, chat_history: list[ChatMessage] | str) -> str:
        """Accept either a pre-formatted string or a list of ChatMessages."""
        if isinstance(chat_history, str):
            return chat_history
        lines: list[str] = []
        for msg in chat_history:
            label = "Human" if msg.role == "user" else "Assistant"
            lines.append(f"{label}: {msg.content}")
        return "\n".join(lines)

    def rewrite_query(
        self, query: str, chat_history: list[ChatMessage] | str
    ) -> str:
        """Rewrite a query using conversation context for pronoun resolution.

        Returns the rewritten standalone query, or the original query
        if the LLM is unreachable or the history is empty.
        """
        history_text = self._format_history(chat_history)

        if not history_text.strip():
            logger.debug("No history provided, returning original query")
            return query

        # Build prompt from template
        user_prompt = REWRITE_USER_TEMPLATE.format(
            history=history_text, query=query
        )

        try:
            response = self._llm.invoke([
                SystemMessage(content=REWRITE_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ])
            rewritten = self._clean_output(response.content)

            if not rewritten:
                logger.warning("Rewriter returned empty output, using original")
                return query

            logger.info(
                "Query rewritten: '%s' -> '%s'", query, rewritten
            )
            return rewritten

        except Exception as exc:
            logger.error(
                "Query rewriter failed (falling back to raw query): %s", exc
            )
            return query


@lru_cache
def get_query_rewriter() -> QueryRewriter:
    """Singleton getter for the query rewriter."""
    return QueryRewriter()
