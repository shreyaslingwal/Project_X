"""Session-based sliding-window conversation memory manager.

Stores chat history per session using Pydantic models and provides
formatted context windows for query rewriting and grounded generation.
"""

import time
from functools import lru_cache

from pydantic import BaseModel, Field

from project_x.core.config import settings


class ChatMessage(BaseModel):
    """Single message in a conversation turn."""

    role: str = Field(description="One of: user, assistant, system")
    content: str = Field(description="Message text")
    timestamp: float = Field(default_factory=time.time)
    citations: list[dict] = Field(default_factory=list)


class ConversationMemory:
    """In-memory session store with sliding-window eviction.

    Each session_id maps to an independent message list.
    Only the most recent `MEMORY_WINDOW_TURNS` user-assistant pairs
    are retained to keep context concise for the rewriter and generator.
    """

    def __init__(self, max_turns: int | None = None) -> None:
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._max_turns = max_turns or settings.MEMORY_WINDOW_TURNS

    def _ensure_session(self, session_id: str) -> list[ChatMessage]:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        return self._sessions[session_id]

    def _evict(self, history: list[ChatMessage]) -> None:
        """Trim history to the most recent `_max_turns` user-assistant pairs.

        A turn is one user message followed by one assistant message (2 messages).
        We keep at most `_max_turns * 2` messages from the tail.
        """
        max_messages = self._max_turns * 2
        while len(history) > max_messages:
            history.pop(0)

    def add_user_message(self, session_id: str, content: str) -> ChatMessage:
        """Append a user message and apply sliding-window eviction."""
        history = self._ensure_session(session_id)
        msg = ChatMessage(role="user", content=content)
        history.append(msg)
        self._evict(history)
        return msg

    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        citations: list[dict] | None = None,
    ) -> ChatMessage:
        """Append an assistant message and apply sliding-window eviction."""
        history = self._ensure_session(session_id)
        msg = ChatMessage(
            role="assistant",
            content=content,
            citations=citations or [],
        )
        history.append(msg)
        self._evict(history)
        return msg

    def get_history(
        self, session_id: str, max_turns: int | None = None
    ) -> list[ChatMessage]:
        """Return the most recent messages up to `max_turns` pairs.

        If max_turns is None, returns the full (already-evicted) history.
        """
        history = self._ensure_session(session_id)
        if max_turns is None:
            return list(history)
        limit = max_turns * 2
        return list(history[-limit:])

    def get_formatted_history(
        self, session_id: str, max_turns: int | None = None
    ) -> str:
        """Return chat history as a Human/Assistant formatted string.

        Suitable for injecting into the query rewriter prompt.
        """
        messages = self.get_history(session_id, max_turns)
        if not messages:
            return ""
        lines: list[str] = []
        for msg in messages:
            label = "Human" if msg.role == "user" else "Assistant"
            lines.append(f"{label}: {msg.content}")
        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        """Delete all messages for a session."""
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        """Return all active session IDs."""
        return list(self._sessions.keys())


@lru_cache
def get_conversation_memory() -> ConversationMemory:
    """Singleton getter for the conversation memory manager."""
    return ConversationMemory()
