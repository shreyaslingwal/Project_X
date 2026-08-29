import React from 'react';

/**
 * Clickable citation chip embedded in assistant responses.
 * Highlights on hover and triggers the CitationInspector drawer.
 */
export default function CitationBadge({ index, citation, onClick }) {
  return (
    <button
      type="button"
      onClick={() => onClick(citation, index)}
      className="inline-flex items-center justify-center px-1.5 py-0.2 mx-0.5 text-[11px] font-mono font-semibold text-primary bg-primary-fixed hover:bg-primary hover:text-white border border-primary/20 rounded transition-all duration-150 cursor-pointer align-baseline shadow-xs group"
      title={`View citation [${index}] from ${citation?.source || 'document'}`}
    >
      <span>[{index}]</span>
    </button>
  );
}
