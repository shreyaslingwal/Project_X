import React from 'react';
import { FileText, FileCode, Trash2, CheckSquare, Square, Layers, Bookmark } from 'lucide-react';

export default function DocumentCard({ doc, isSelected, onToggle, onDelete, isDeleting }) {
  const isPdf = doc.source.toLowerCase().endsWith('.pdf');

  return (
    <div
      className={`group relative flex items-start gap-2.5 p-3 rounded-lg border transition-all duration-200 ${
        isSelected
          ? 'bg-surface-highest/60 border-primary/40 shadow-xs'
          : 'bg-surface-low/50 border-neutral-border/50 opacity-70 hover:opacity-100 hover:bg-surface-low'
      }`}
    >
      {/* Selection Checkbox */}
      <button
        type="button"
        onClick={() => onToggle(doc.doc_id)}
        className="mt-0.5 text-neutral-light hover:text-primary transition-colors cursor-pointer"
        title={isSelected ? 'De-scope this document' : 'Include this document in search'}
      >
        {isSelected ? (
          <CheckSquare className="w-4 h-4 text-primary" />
        ) : (
          <Square className="w-4 h-4" />
        )}
      </button>

      {/* File Icon */}
      <div className="mt-0.5 flex-shrink-0 text-primary">
        {isPdf ? (
          <FileText className="w-4 h-4 text-primary" />
        ) : (
          <FileCode className="w-4 h-4 text-neutral-dark" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 pr-6">
        <h4
          className="text-xs font-semibold text-neutral-dark truncate leading-snug cursor-pointer"
          onClick={() => onToggle(doc.doc_id)}
          title={doc.source}
        >
          {doc.source}
        </h4>
        <div className="flex items-center gap-2 mt-1 text-[11px] text-neutral-light font-mono">
          {doc.total_pages && (
            <span className="flex items-center gap-0.5">
              <Bookmark className="w-3 h-3 text-neutral-muted" />
              {doc.total_pages} {doc.total_pages === 1 ? 'pg' : 'pgs'}
            </span>
          )}
          <span className="flex items-center gap-0.5">
            <Layers className="w-3 h-3 text-neutral-muted" />
            {doc.total_chunks} chunks
          </span>
        </div>
      </div>

      {/* Delete Button */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onDelete(doc.doc_id);
        }}
        disabled={isDeleting}
        className="absolute top-2.5 right-2 p-1 text-neutral-light hover:text-error opacity-0 group-hover:opacity-100 rounded transition-all duration-150 cursor-pointer disabled:opacity-50"
        title="Remove document from index"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
