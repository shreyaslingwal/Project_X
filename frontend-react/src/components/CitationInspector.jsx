import React from 'react';
import { X, FileText, Bookmark, Hash, CheckCircle2, ShieldCheck, Quote } from 'lucide-react';

export default function CitationInspector({ citation, index, onClose }) {
  if (!citation) return null;

  return (
    <aside className="w-80 bg-surface-lowest border-l border-neutral-border/60 flex flex-col h-full z-10 shadow-soft animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-4 border-b border-neutral-border/40 flex items-center justify-between bg-surface-low/50">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-primary-fixed text-primary flex items-center justify-center font-mono font-bold text-xs">
            [{index}]
          </div>
          <h3 className="font-display font-bold text-sm text-neutral-dark">
            Citation Provenance
          </h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-neutral-light hover:text-neutral-dark hover:bg-surface-container rounded transition-colors cursor-pointer"
          title="Close inspector"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Metadata Overview */}
      <div className="p-4 space-y-4 overflow-y-auto flex-1 text-xs">
        {/* Source File Card */}
        <div className="p-3 bg-surface-low rounded-xl border border-neutral-border/50">
          <div className="flex items-center gap-2 text-primary font-semibold mb-1">
            <FileText className="w-4 h-4" />
            <span className="truncate">{citation.source}</span>
          </div>
          <div className="flex flex-wrap gap-2 mt-2 text-[11px] text-neutral-muted font-mono">
            {citation.page && (
              <span className="px-2 py-0.5 bg-white rounded border border-neutral-border/40 flex items-center gap-1">
                <Bookmark className="w-3 h-3 text-primary" />
                Page {citation.page}
              </span>
            )}
            {citation.section && (
              <span className="px-2 py-0.5 bg-white rounded border border-neutral-border/40 truncate max-w-[200px]">
                {citation.section}
              </span>
            )}
            {citation.chunk_id && (
              <span className="px-2 py-0.5 bg-white rounded border border-neutral-border/40 flex items-center gap-1">
                <Hash className="w-3 h-3 text-neutral-light" />
                {citation.chunk_id}
              </span>
            )}
          </div>
        </div>

        {/* Grounding Status */}
        <div className="flex items-center gap-2 px-3 py-2 bg-grounding-badge border border-grounding/20 rounded-lg text-grounding">
          <ShieldCheck className="w-4 h-4 text-grounding-emerald" />
          <span className="font-medium text-[11px]">
            Verified Source Chunk (FastEmbed + FlashRank)
          </span>
        </div>

        {/* Verbatim Excerpt */}
        <div>
          <div className="flex items-center gap-1.5 font-bold text-neutral-dark mb-2 uppercase text-[10px] tracking-wider">
            <Quote className="w-3.5 h-3.5 text-primary" />
            Verbatim Chunk Text
          </div>
          <div className="p-3.5 bg-surface-container/60 border border-neutral-border/60 rounded-xl text-neutral-dark font-body text-xs leading-relaxed whitespace-pre-wrap selection:bg-primary-fixed">
            {citation.snippet || citation.text || 'No text snippet available.'}
          </div>
        </div>
      </div>
    </aside>
  );
}
