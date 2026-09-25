"""Document summarization engine for Studio capabilities.

Generates structured briefings from indexed document chunks using the local
Ollama model. Supports both synchronous and async streaming output for
real-time token delivery via FastAPI SSE endpoints.
"""

import logging
from collections.abc import AsyncIterator
from functools import lru_cache

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from project_x.core.config import settings
from project_x.ingestion.models import DocumentChunk
from project_x.rag.generator import StreamEvent

logger = logging.getLogger(__name__)


SUMMARY_SYSTEM_PROMPT = """You are a document analysis assistant that creates structured briefings from source documents.

Rules:
1. Base your summary strictly on the provided document content. Do not add external knowledge.
2. Use the following structure for your output:

## Executive Overview
Write 2-3 concise paragraphs capturing the document's core thesis, purpose, and scope.

## Key Topics & Themes
List the major concepts and themes as bullet points. Include page or section references where available.

## Core Takeaways
Summarize the most important findings, decisions, or data points as bullet points.

## Suggested Follow-up Questions
Provide exactly 3-4 specific questions a reader could ask to explore the document further. Prefix each with "Q: ".

3. Keep the language clear and direct. Avoid filler phrases.
4. Use markdown formatting (bold, bullet lists, headers) for readability.
5. If the document content is too short or fragmentary to produce a full briefing, summarize what is available and note the limitation."""


STUDY_GUIDE_SYSTEM_PROMPT = """You are an educational content creator that builds structured study guides from source documents.

Rules:
1. Base your study guide strictly on the provided document content. Do not add external knowledge.
2. Use the following structure for your output:

## Concept Overview
Write 2-3 paragraphs introducing the subject matter and its significance.

## Key Vocabulary & Definitions
Create a glossary of important terms found in the documents. Format each entry as:
- **Term**: Clear, concise definition based on how the term is used in the source material.

## Detailed Section Analysis
Break down the major sections or themes into subsections. For each:
- Summarize the core idea
- Highlight supporting details or evidence
- Note any relationships to other sections

## Practice Review Questions
Provide 5-6 review questions that test comprehension of the material. Format each as:
- **Q1**: [Question text]
  - **Answer**: [Concise answer grounded in the source content]

## Suggested Follow-up Questions
Provide exactly 3-4 deeper exploration questions. Prefix each with "Q: ".

3. Keep the language clear and instructional. Use markdown formatting.
4. If the document content is too short, produce what is possible and note the limitation."""


FAQ_SYSTEM_PROMPT = """You are a document analyst that generates comprehensive FAQ sections from source documents.

Rules:
1. Base your FAQ strictly on the provided document content. Do not add external knowledge.
2. Use the following structure for your output:

## Frequently Asked Questions

Generate 8-12 question-answer pairs that cover the most important topics in the documents. For each:

### Q: [Natural question a reader would ask]
[Clear, concise answer grounded in specific parts of the source material. Reference page numbers or sections where available.]

## Key Definitions
List 3-5 important terms with brief definitions as bullet points.

## Suggested Follow-up Questions
Provide exactly 3-4 questions for deeper exploration. Prefix each with "Q: ".

3. Questions should progress from foundational to more nuanced topics.
4. Keep answers concise but thorough. Use markdown formatting.
5. If the document content is too short, generate fewer Q&A pairs and note the limitation."""


TIMELINE_SYSTEM_PROMPT = """You are a document analyst that extracts chronological progressions, process stages, and key milestones from source documents.

Rules:
1. Base your timeline strictly on the provided document content. Do not add external knowledge.
2. Use the following structure for your output:

## Overview
Write 1-2 paragraphs summarizing the overall progression or process described in the documents.

## Key Milestones & Stages
Extract and list events, stages, decisions, or milestones in chronological or logical order. For each:
- **[Stage/Date/Phase]**: Description of what occurred or was decided. Reference the source page or section.

## Critical Dependencies & Relationships
Note any causal relationships, prerequisites, or dependencies between milestones.

## Current Status & Next Steps
Summarize where the process currently stands and what comes next, if described.

## Suggested Follow-up Questions
Provide exactly 3-4 questions. Prefix each with "Q: ".

3. If no clear chronological order exists, organize by logical progression or importance.
4. Keep the language clear and direct. Use markdown formatting.
5. If the document content lacks temporal or sequential information, note the limitation and extract what structure is available."""


ARTIFACT_PROMPTS = {
    "briefing": SUMMARY_SYSTEM_PROMPT,
    "study_guide": STUDY_GUIDE_SYSTEM_PROMPT,
    "faq": FAQ_SYSTEM_PROMPT,
    "timeline": TIMELINE_SYSTEM_PROMPT,
}

ARTIFACT_LABELS = {
    "briefing": "a structured briefing",
    "study_guide": "a comprehensive study guide",
    "faq": "a frequently asked questions document",
    "timeline": "a timeline and milestones analysis",
}

STUDIO_NUM_CTX = 8000


CROSS_BRIEFING_SYSTEM_PROMPT = """You are a document analyst that creates unified cross-source briefings by synthesizing content from multiple distinct documents.

Rules:
1. Base your synthesis strictly on the provided document excerpts. Do not add external knowledge.
2. Each source is demarcated by a header like "=== SOURCE N: [filename] ===". Treat each as a separate document.
3. Use the following structure for your output:

## Executive Synthesis
Write 2-3 paragraphs connecting all sources into a unified narrative. Explain how the documents relate to each other and what picture they collectively paint.

## Cross-Cutting Themes & Consensus
Identify areas of agreement, shared principles, or complementary ideas across the sources. Use bullet points and cite the specific source filenames.

## Contrasts, Unique Perspectives & Discrepancies
Highlight specific ways the sources diverge, provide unique angles, or present conflicting information. Attribute each contrast to its source.

## Source-by-Source Breakdown
For each source document, provide a concise summary card:
### [Source: Filename]
- Core purpose and scope of this document
- Key findings or contributions unique to this source

## Cross-Source Exploration Questions
Provide exactly 3-4 questions that span multiple documents. Prefix each with "Q: ".

4. Keep the language clear and direct. Use markdown formatting.
5. If sources have minimal overlap, note that and focus on what each contributes independently."""


CROSS_STUDY_GUIDE_SYSTEM_PROMPT = """You are an educational content creator that builds unified study guides by synthesizing content from multiple distinct source documents.

Rules:
1. Base your study guide strictly on the provided document excerpts. Do not add external knowledge.
2. Each source is demarcated by a header like "=== SOURCE N: [filename] ===". Treat each as a separate document.
3. Use the following structure for your output:

## Comparative Overview
Write 2-3 paragraphs introducing how these sources collectively cover the subject matter and their combined significance.

## Unified Glossary
Create an aggregated glossary of important terms found across all sources. Format each entry as:
- **Term** *(Source: filename)*: Clear, concise definition based on how the term is used in the source material.

## Thematic Section Breakdown
Identify 3-5 major themes that span across sources. For each theme:
- Summarize how each source addresses or contributes to this theme
- Note agreements and differences between sources
- Highlight supporting details with source attribution

## Comprehensive Practice Review
Provide 5-6 review questions that test cross-source understanding. Format each as:
- **Q1**: [Question referencing multiple sources]
  - **Answer**: [Concise answer with source attribution]

## Cross-Source Exploration Questions
Provide exactly 3-4 deeper questions. Prefix each with "Q: ".

4. Keep the language clear and instructional. Use markdown formatting.
5. If sources cover different topics, organize by document grouping and note the limitation."""


CROSS_FAQ_SYSTEM_PROMPT = """You are a document analyst that generates comprehensive cross-source FAQ sections from multiple distinct documents.

Rules:
1. Base your FAQ strictly on the provided document excerpts. Do not add external knowledge.
2. Each source is demarcated by a header like "=== SOURCE N: [filename] ===". Treat each as a separate document.
3. Use the following structure for your output:

## Cross-Source Frequently Asked Questions

Generate 8-12 question-answer pairs that draw on multiple sources where possible. For each:

### Q: [Natural question a reader would ask about the combined material]
[Clear, concise answer with explicit source attribution. Example: "According to [filename A], ... while [filename B] adds that ..."]

## Key Concept Matrix
Compare how different sources define or treat 3-5 important concepts. Format as:
- **Concept**: [Source A] defines it as... | [Source B] presents it as...

## Cross-Source Exploration Questions
Provide exactly 3-4 questions for deeper exploration. Prefix each with "Q: ".

4. Questions should progress from foundational to more nuanced and cross-referencing.
5. Keep answers concise but thorough. Use markdown formatting."""


CROSS_TIMELINE_SYSTEM_PROMPT = """You are a document analyst that extracts and merges chronological progressions, process stages, and key milestones from multiple distinct source documents.

Rules:
1. Base your timeline strictly on the provided document excerpts. Do not add external knowledge.
2. Each source is demarcated by a header like "=== SOURCE N: [filename] ===". Treat each as a separate document.
3. Use the following structure for your output:

## Unified Chronology & Workflow Stages
Write 1-2 paragraphs summarizing the macro-level lifecycle or progression described across all sources combined.

## Source-Attributed Milestones
Extract events, stages, decisions, or milestones from all sources and present them in chronological or logical order. For each:
- **[Stage/Date/Phase]** *(Source: filename)*: Description of what occurred or was decided.

## Inter-Document Dependencies
Identify how findings, stages, or events in one document relate to, depend on, or feed into content from another document.

## Current Status & Next Steps
Synthesize where the collective process stands and what comes next across all sources.

## Cross-Source Exploration Questions
Provide exactly 3-4 questions. Prefix each with "Q: ".

4. If no clear chronological order exists, organize by logical progression.
5. Keep the language clear and direct. Use markdown formatting."""


CROSS_ARTIFACT_PROMPTS = {
    "briefing": CROSS_BRIEFING_SYSTEM_PROMPT,
    "study_guide": CROSS_STUDY_GUIDE_SYSTEM_PROMPT,
    "faq": CROSS_FAQ_SYSTEM_PROMPT,
    "timeline": CROSS_TIMELINE_SYSTEM_PROMPT,
}

CROSS_ARTIFACT_LABELS = {
    "briefing": "a cross-source executive briefing synthesizing all active documents",
    "study_guide": "a cross-source study guide synthesizing all active documents",
    "faq": "a cross-source FAQ synthesizing all active documents",
    "timeline": "a cross-source timeline and milestones analysis synthesizing all active documents",
}


def _format_chunks_for_summary(chunks: list[DocumentChunk]) -> str:
    """Assemble document chunks into a sequential text block for summarization.

    Chunks are sorted by page number and chunk index to preserve document flow.
    Each block is labeled with its source location for the LLM's reference.
    """
    if not chunks:
        return ""

    sorted_chunks = sorted(
        chunks,
        key=lambda c: (c.metadata.page or 0, c.metadata.chunk_index),
    )

    blocks: list[str] = []
    for chunk in sorted_chunks:
        meta = chunk.metadata
        if meta.page is not None:
            location = f"Page {meta.page}"
        elif meta.section:
            location = f"Section: {meta.section}"
        else:
            location = "Document content"

        block = f"[{location}]\n{chunk.text.strip()}"
        blocks.append(block)

    return "\n\n".join(blocks)


def _build_summary_user_prompt(
    formatted_content: str,
    source_name: str = "the selected documents",
    artifact_type: str = "briefing",
) -> str:
    """Construct the user prompt for single-document summarization."""
    artifact_label = ARTIFACT_LABELS.get(artifact_type, "a structured briefing")
    return (
        f"Analyze the following content from {source_name} and produce "
        f"{artifact_label}.\n\n"
        f"Document content:\n{formatted_content}"
    )


def _select_stratified_chunks(
    chunks: list[DocumentChunk], char_budget: int
) -> list[DocumentChunk]:
    """Pick representative opening, middle, and closing chunks within a budget.

    Selection strategy:
    - Opening chunks capture title, abstract, introduction material.
    - Closing chunks capture conclusions, summaries, next steps.
    - Middle chunks fill remaining budget with evenly-spaced samples.
    """
    if not chunks:
        return []

    sorted_chunks = sorted(
        chunks, key=lambda c: (c.metadata.page or 0, c.metadata.chunk_index)
    )

    total_chars = sum(len(c.text) for c in sorted_chunks)
    if total_chars <= char_budget:
        return sorted_chunks

    selected: list[DocumentChunk] = []
    remaining_budget = char_budget

    opening = sorted_chunks[0]
    selected.append(opening)
    remaining_budget -= len(opening.text)

    if len(sorted_chunks) > 1 and remaining_budget > 0:
        closing = sorted_chunks[-1]
        selected.append(closing)
        remaining_budget -= len(closing.text)

    if remaining_budget > 0 and len(sorted_chunks) > 2:
        middle_pool = sorted_chunks[1:-1]
        step = max(1, len(middle_pool) // 3)
        for i in range(0, len(middle_pool), step):
            candidate = middle_pool[i]
            if remaining_budget - len(candidate.text) < 0:
                break
            selected.append(candidate)
            remaining_budget -= len(candidate.text)

    selected.sort(key=lambda c: (c.metadata.page or 0, c.metadata.chunk_index))
    return selected


def _format_multi_doc_content(
    chunks_by_doc: dict[str, list[DocumentChunk]],
    id_to_name: dict[str, str],
    total_budget_chars: int = 12000,
) -> str:
    """Format multiple documents with stratified chunk sampling and source headers.

    Divides the total character budget equally across all active documents,
    selects representative chunks (opening, middle, closing) from each,
    and wraps them with explicit source demarcation headers.
    """
    if not chunks_by_doc:
        return ""

    doc_count = len(chunks_by_doc)
    per_doc_budget = total_budget_chars // doc_count

    sections: list[str] = []
    for idx, (doc_id, doc_chunks) in enumerate(chunks_by_doc.items(), start=1):
        filename = id_to_name.get(doc_id, f"Document {idx}")

        selected = _select_stratified_chunks(doc_chunks, per_doc_budget)

        page_nums = [c.metadata.page for c in doc_chunks if c.metadata.page is not None]
        if page_nums:
            page_range = f"Pages {min(page_nums)}-{max(page_nums)}"
        else:
            page_range = f"{len(doc_chunks)} chunks"

        header = f"=== SOURCE {idx}: {filename} ({page_range}) ==="

        chunk_blocks: list[str] = []
        for chunk in selected:
            meta = chunk.metadata
            if meta.page is not None:
                location = f"Page {meta.page}"
            elif meta.section:
                location = f"Section: {meta.section}"
            else:
                location = "Document content"
            chunk_blocks.append(f"[{location}]\n{chunk.text.strip()}")

        sections.append(header + "\n" + "\n\n".join(chunk_blocks))

    return "\n\n".join(sections)


def _build_cross_source_user_prompt(
    formatted_content: str,
    doc_count: int,
    artifact_type: str = "briefing",
) -> str:
    """Construct the user prompt for cross-source multi-document synthesis."""
    artifact_label = CROSS_ARTIFACT_LABELS.get(
        artifact_type, "a cross-source executive briefing"
    )
    return (
        f"Analyze the following excerpts from {doc_count} distinct source documents "
        f"and produce {artifact_label}.\n\n"
        f"Source material:\n{formatted_content}"
    )



class DocumentSummarizer:
    """Generates structured document artifacts using a local Ollama model.

    Produces executive briefings, study guides, FAQs, and timeline analyses
    from indexed document chunks. Supports both single-document and
    cross-source multi-document synthesis modes.
    """

    def __init__(self) -> None:
        self._llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.3,
            num_ctx=settings.OLLAMA_NUM_CTX,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )
        self._studio_llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.3,
            num_ctx=STUDIO_NUM_CTX,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )

    def _build_messages(
        self,
        chunks: list[DocumentChunk],
        source_name: str = "the selected documents",
        artifact_type: str = "briefing",
    ) -> list:
        """Construct the system + user message pair for single-document artifacts."""
        system_prompt = ARTIFACT_PROMPTS.get(artifact_type, SUMMARY_SYSTEM_PROMPT)
        formatted_content = _format_chunks_for_summary(chunks)
        user_prompt = _build_summary_user_prompt(
            formatted_content, source_name, artifact_type
        )
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

    def _build_cross_source_messages(
        self,
        chunks_by_doc: dict[str, list[DocumentChunk]],
        id_to_name: dict[str, str],
        artifact_type: str = "briefing",
    ) -> list:
        """Construct the system + user message pair for cross-source synthesis."""
        system_prompt = CROSS_ARTIFACT_PROMPTS.get(
            artifact_type, CROSS_BRIEFING_SYSTEM_PROMPT
        )
        formatted_content = _format_multi_doc_content(chunks_by_doc, id_to_name)
        user_prompt = _build_cross_source_user_prompt(
            formatted_content, len(chunks_by_doc), artifact_type
        )
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

    def _resolve_messages_and_llm(
        self,
        chunks: list[DocumentChunk],
        source_name: str,
        artifact_type: str,
        chunks_by_doc: dict[str, list[DocumentChunk]] | None = None,
        id_to_name: dict[str, str] | None = None,
    ) -> tuple[list, ChatOllama]:
        """Route to single-doc or cross-source mode based on arguments.

        Returns the constructed messages and the appropriate LLM instance.
        Cross-source mode activates when chunks_by_doc has more than one document.
        """
        is_multi_doc = chunks_by_doc is not None and len(chunks_by_doc) > 1
        if is_multi_doc and id_to_name is not None:
            messages = self._build_cross_source_messages(
                chunks_by_doc, id_to_name, artifact_type
            )
            return messages, self._studio_llm

        messages = self._build_messages(chunks, source_name, artifact_type)
        return messages, self._llm

    def summarize(
        self,
        chunks: list[DocumentChunk],
        source_name: str = "the selected documents",
        artifact_type: str = "briefing",
        chunks_by_doc: dict[str, list[DocumentChunk]] | None = None,
        id_to_name: dict[str, str] | None = None,
    ) -> str:
        """Generate a complete artifact (blocking, non-streaming).

        Args:
            chunks: Document chunks for single-doc mode.
            source_name: Display name for the source scope.
            artifact_type: Type of artifact to generate.
            chunks_by_doc: Grouped chunks keyed by doc_id for cross-source mode.
            id_to_name: Mapping of doc_id to display filename.

        Returns:
            Full generated text with structured sections.
        """
        if not chunks:
            return "No document content available to summarize."

        messages, llm = self._resolve_messages_and_llm(
            chunks, source_name, artifact_type, chunks_by_doc, id_to_name
        )

        try:
            response = llm.invoke(messages)
            return response.content.strip()
        except Exception as exc:
            logger.error("Artifact generation failed (%s): %s", artifact_type, exc)
            return f"Generation failed: {exc}"

    async def astream_summary(
        self,
        chunks: list[DocumentChunk],
        source_name: str = "the selected documents",
        artifact_type: str = "briefing",
        chunks_by_doc: dict[str, list[DocumentChunk]] | None = None,
        id_to_name: dict[str, str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Async stream artifact tokens for FastAPI SSE endpoints.

        Yields StreamEvent objects with type 'token' for each text fragment,
        and type 'done' when generation completes. On failure, yields an
        'error' event.

        Args:
            chunks: Document chunks for single-doc mode.
            source_name: Display name for the source scope.
            artifact_type: Type of artifact to generate.
            chunks_by_doc: Grouped chunks keyed by doc_id for cross-source mode.
            id_to_name: Mapping of doc_id to display filename.
        """
        if not chunks:
            yield StreamEvent(
                type="token",
                content="No document content available to summarize.",
            )
            yield StreamEvent(type="done")
            return

        messages, llm = self._resolve_messages_and_llm(
            chunks, source_name, artifact_type, chunks_by_doc, id_to_name
        )

        try:
            async for chunk in llm.astream(messages):
                token = chunk.content
                if token:
                    yield StreamEvent(type="token", content=token)
        except Exception as exc:
            logger.error("Async artifact streaming failed (%s): %s", artifact_type, exc)
            yield StreamEvent(type="error", content=str(exc))
            return

        yield StreamEvent(type="done")


@lru_cache
def get_document_summarizer() -> DocumentSummarizer:
    """Singleton getter for the document summarizer."""
    return DocumentSummarizer()


