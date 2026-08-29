"""Interactive CLI Demo for the full RAG Pipeline (Milestones 1 -> 5).

Tests the complete end-to-end flow: Ingestion, Embeddings, FAISS,
FlashRank Re-ranking, Conversational Memory, Query Rewriting,
Grounded Generation with real-time token streaming, and Citation mapping.

Usage:
    # Test with a specific file:
    uv run python scripts/demo_pipeline.py --file "C:/path/to/your_document.pdf"

    # Ingest all files in data/uploads/ and start chat:
    uv run python scripts/demo_pipeline.py

    # Clear old index and start fresh:
    uv run python scripts/demo_pipeline.py --clear
"""

import argparse
import sys
import uuid
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from project_x.core.config import settings
from project_x.core.vector_store import FAISSVectorStore
from project_x.ingestion.loader import ingest_file
from project_x.rag.pipeline import RAGPipeline
from project_x.retrieval.retriever import TwoStageRetriever


def print_banner():
    print("=" * 70)
    print("Project X - Full RAG Pipeline Demo (Milestones 1-5)")
    print("=" * 70)
    print("1. Ingestion: PDF (PyMuPDF) / Markdown with exact page/section tracking")
    print("2. Embeddings: FastEmbed CPU (BAAI/bge-small-en-v1.5, 384-dim)")
    print("3. Vector Store: FAISS IndexFlatIP (Cosine Similarity)")
    print("4. Re-ranking: FlashRank CPU Cross-Encoder (ms-marco-MiniLM-L-12-v2)")
    print("5. Memory: Sliding-window conversation buffer (5 turns)")
    print(f"6. Rewriter: {settings.REWRITE_MODEL} (Query contextualization)")
    print(f"7. Generator: {settings.OLLAMA_MODEL} (Grounded streaming generation)")
    print("=" * 70)
    print()


def ingest_custom_file(file_path: Path, vector_store: FAISSVectorStore) -> None:
    """Ingest and index a specific custom file."""
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return

    print(f"\nIngesting custom document: {file_path.name}...")
    try:
        indexed_docs = vector_store.list_documents()
        already_indexed = any(d["source"] == file_path.name for d in indexed_docs)
        if already_indexed:
            print(f"Note: '{file_path.name}' is already indexed in the vector store.")
            choice = input("Do you want to re-index it? (y/n): ").strip().lower()
            if choice != "y":
                return
            for d in indexed_docs:
                if d["source"] == file_path.name:
                    vector_store.delete_document(d["doc_id"])

        target_path = file_path
        if not file_path.resolve().is_relative_to(settings.UPLOAD_DIR.resolve()):
            target_path = settings.UPLOAD_DIR / file_path.name
            import shutil
            shutil.copy2(file_path, target_path)
            print(f"Copied file to: {target_path}")

        result = ingest_file(target_path)
        added = vector_store.add_chunks(result.chunks)
        page_info = f"{result.total_pages} pages" if result.total_pages else "Markdown sections"
        print(f"Successfully processed {file_path.name}: {added} chunks created across {page_info} ({result.total_chars} characters).\n")
    except Exception as e:
        print(f"[ERROR] Failed to ingest {file_path.name}: {e}")


def ingest_all_uploads(vector_store: FAISSVectorStore) -> None:
    """Scan data/uploads/ and ingest any unindexed PDF or MD files."""
    indexed_docs = vector_store.list_documents()
    indexed_filenames = {d["source"] for d in indexed_docs}

    valid_extensions = {".pdf", ".md", ".markdown"}
    upload_files = [
        f for f in settings.UPLOAD_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in valid_extensions
    ]

    new_files = [f for f in upload_files if f.name not in indexed_filenames]

    if new_files:
        print(f"Found {len(new_files)} new document(s) in {settings.UPLOAD_DIR}:")
        for f in new_files:
            try:
                print(f" - Ingesting {f.name}...")
                result = ingest_file(f)
                added = vector_store.add_chunks(result.chunks)
                print(f"   Indexed {added} chunks.")
            except Exception as e:
                print(f"   Failed to ingest {f.name}: {e}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Full RAG Pipeline Demo with streaming generation.")
    parser.add_argument("--file", "-f", type=str, help="Path to a PDF or Markdown file to ingest and test.")
    parser.add_argument("--clear", "-c", action="store_true", help="Clear the existing vector store before starting.")
    args = parser.parse_args()

    print_banner()

    settings.ensure_directories()
    vector_store = FAISSVectorStore()

    if args.clear:
        print("Clearing existing vector store...")
        vector_store.clear_index()
        print("Vector store cleared.\n")

    if args.file:
        custom_file_path = Path(args.file)
        ingest_custom_file(custom_file_path, vector_store)

    ingest_all_uploads(vector_store)

    # Build pipeline with shared vector store
    retriever = TwoStageRetriever(vector_store=vector_store)
    pipeline = RAGPipeline(retriever=retriever)

    indexed_docs = vector_store.list_documents()
    print("=" * 70)
    print(f"Current Index Summary: {vector_store.total_chunks} total chunks across {len(indexed_docs)} document(s)")
    for i, d in enumerate(indexed_docs, 1):
        pages = f"{d['total_pages']} pages" if d['total_pages'] else "MD"
        print(f"  {i}. {d['source']} ({pages}, {d['total_chunks']} chunks, doc_id: {d['doc_id']})")
    print("=" * 70)

    if vector_store.total_chunks == 0:
        print("\nNo documents are currently indexed.")
        print(f"To add your own document, either:")
        print(f"  1. Copy your PDF/MD file into: {settings.UPLOAD_DIR.resolve()}")
        print(f"  2. Or run: uv run python scripts/demo_pipeline.py --file \"path/to/your_document.pdf\"\n")
        return

    # Generate a unique session ID for this demo run
    session_id = f"demo_{uuid.uuid4().hex[:8]}"
    print(f"\nSession: {session_id}")
    print("Ready for grounded chat! Responses stream in real-time with source citations.")
    print("Type 'exit' or 'quit' to stop. Type 'clear' to reset conversation.\n")

    while True:
        try:
            query = input("\nYou: ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit"):
                print("Exiting demo.")
                break
            if query.lower() == "clear":
                pipeline.memory.clear_session(session_id)
                print("[Session memory cleared]")
                continue

            print("\nAssistant: ", end="", flush=True)

            citations = []
            for event in pipeline.stream_query(session_id, query):
                if event.type == "token":
                    print(event.content, end="", flush=True)
                elif event.type == "citations":
                    citations = event.citations
                elif event.type == "error":
                    print(f"\n[ERROR] {event.content}")

            print()  # Newline after streamed response

            if citations:
                print(f"\n--- Sources ({len(citations)} cited) ---")
                for c in citations:
                    loc = f"Page {c.page}" if c.page else f"Section: {c.section}"
                    print(f"  [{c.citation_index}] {c.source} ({loc})")
                    print(f"      \"{c.snippet[:120]}...\"")

            print()

        except (KeyboardInterrupt, EOFError):
            print("\nExiting demo.")
            break


if __name__ == "__main__":
    main()
