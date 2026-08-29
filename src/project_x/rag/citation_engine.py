"""Inline citation extraction and metadata mapping engine.

Parses bracketed citation markers ([1], [2], [1, 2]) from LLM output and
resolves them back to the exact source document chunks with full metadata.
"""

import re

from pydantic import BaseModel, Field

from project_x.ingestion.models import DocumentChunk


class Citation(BaseModel):
    """A resolved citation linking a bracketed index to its source chunk."""

    citation_index: int = Field(description="1-based citation number as used in the response")
    source: str = Field(description="Original filename (e.g. 'invoice.pdf')")
    doc_id: str = Field(description="Document identifier")
    page: int | None = Field(default=None, description="Page number (PDF only)")
    section: str | None = Field(default=None, description="Section breadcrumb (Markdown only)")
    chunk_id: str = Field(description="Unique chunk identifier")
    snippet: str = Field(description="First 200 characters of the source chunk text")


# Regex to capture citation indices: [1], [2], [1, 2], [1][2], [1,2,3]
_CITATION_PATTERN = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


class CitationEngine:
    """Extracts inline citation markers from generated text and maps them to source chunks."""

    def extract_citations(
        self,
        text: str,
        source_chunks: list[tuple[DocumentChunk, float]],
    ) -> list[Citation]:
        """Parse all [N] citations from text and resolve to chunk metadata.

        Args:
            text: The generated LLM response containing inline citations.
            source_chunks: Ordered list of (DocumentChunk, score) tuples
                           that were provided as numbered sources to the LLM.

        Returns:
            Deduplicated list of Citation objects sorted by citation_index.
        """
        if not text or not source_chunks:
            return []

        # Extract all unique cited indices
        cited_indices: set[int] = set()
        for match in _CITATION_PATTERN.finditer(text):
            indices_str = match.group(1)
            for idx_str in indices_str.split(","):
                idx_str = idx_str.strip()
                if idx_str.isdigit():
                    cited_indices.add(int(idx_str))

        # Build citation objects for valid (in-bounds) indices
        citations: list[Citation] = []
        for idx in sorted(cited_indices):
            # Citations are 1-based, source_chunks is 0-based
            if 1 <= idx <= len(source_chunks):
                chunk, _score = source_chunks[idx - 1]
                meta = chunk.metadata
                snippet = chunk.text.strip()[:200]
                citations.append(
                    Citation(
                        citation_index=idx,
                        source=meta.source,
                        doc_id=meta.doc_id,
                        page=meta.page,
                        section=meta.section,
                        chunk_id=chunk.chunk_id,
                        snippet=snippet,
                    )
                )

        return citations

    def get_all_cited_indices(self, text: str) -> list[int]:
        """Return sorted list of all unique citation indices found in text."""
        indices: set[int] = set()
        for match in _CITATION_PATTERN.finditer(text):
            for idx_str in match.group(1).split(","):
                idx_str = idx_str.strip()
                if idx_str.isdigit():
                    indices.add(int(idx_str))
        return sorted(indices)
