"""Markdown document loader with header-aware section extraction."""

from pathlib import Path

from project_x.ingestion.security import clean_text

HEADER_MARKERS = ("#", "##", "###", "####")


def _build_breadcrumb(header_stack: dict[int, str]) -> str:
    """Build a section breadcrumb from the current header hierarchy.

    Example: {"1": "Architecture", "2": "Attention"} -> "Architecture > Attention"
    """
    parts = [header_stack[level] for level in sorted(header_stack) if header_stack[level]]
    return " > ".join(parts) if parts else "Document Root"


def load_markdown(file_path: Path) -> list[tuple[str, str]]:
    """Extract text from a Markdown file, split by header sections.

    Splits on #, ##, ###, #### headers and tracks the section
    hierarchy as a breadcrumb trail for citation metadata.

    Args:
        file_path: Path to the Markdown file.

    Returns:
        List of (section_breadcrumb, cleaned_text) tuples.

    Raises:
        ValueError: If the file has no extractable text content.
    """
    raw_content = file_path.read_text(encoding="utf-8")
    cleaned_content = clean_text(raw_content)

    if not cleaned_content.strip():
        raise ValueError(
            f"No extractable text found in '{file_path.name}'. "
            f"The Markdown file appears to be empty."
        )

    lines = cleaned_content.split("\n")
    sections: list[tuple[str, str]] = []
    header_stack: dict[int, str] = {}
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        header_level = _detect_header_level(stripped)

        if header_level is not None:
            # Flush accumulated text before this header
            if current_lines:
                text_block = "\n".join(current_lines).strip()
                if text_block:
                    breadcrumb = _build_breadcrumb(header_stack)
                    sections.append((breadcrumb, text_block))
                current_lines = []

            # Update the header hierarchy
            header_text = stripped.lstrip("#").strip()
            header_stack[header_level] = header_text
            # Clear deeper levels when a higher-level header appears
            for level in list(header_stack):
                if level > header_level:
                    del header_stack[level]
        else:
            current_lines.append(line)

    # Flush remaining text
    if current_lines:
        text_block = "\n".join(current_lines).strip()
        if text_block:
            breadcrumb = _build_breadcrumb(header_stack)
            sections.append((breadcrumb, text_block))

    if not sections:
        # No headers found; treat the entire file as one section
        sections.append(("Document Root", cleaned_content))

    return sections


def _detect_header_level(line: str) -> int | None:
    """Detect the ATX header level of a line (1-4), or None if not a header."""
    if not line.startswith("#"):
        return None
    for level in range(4, 0, -1):
        prefix = "#" * level
        if line.startswith(prefix) and (len(line) == level or line[level] == " "):
            return level
    return None
