import React from 'react';
import { X, HelpCircle, ShieldCheck, Cpu, Search, Sparkles, Layers } from 'lucide-react';

export default function HelpModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-dark/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-surface-lowest border border-neutral-border/60 rounded-2xl max-w-lg w-full p-6 shadow-dropdown relative max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-neutral-border/40 pb-4 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary-fixed text-primary flex items-center justify-center">
              <HelpCircle className="w-4 h-4" />
            </div>
            <h3 className="font-display font-bold text-lg text-neutral-dark">
              How Project X Works
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-neutral-light hover:text-neutral-dark hover:bg-surface-container rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4 text-xs font-body text-neutral-muted leading-relaxed">
          <p>
            Project X is a local, privacy-first research synthesis platform that processes documents and answers questions with strict provenance grounding.
          </p>

          <div className="space-y-3">
            <div className="flex gap-3 items-start p-3 bg-surface-low rounded-xl border border-neutral-border/30">
              <Layers className="w-4 h-4 text-primary shrink-0 mt-0.5" />
              <div>
                <strong className="text-neutral-dark block font-semibold">1. Multi-Document Ingestion</strong>
                PDF and Markdown files are chunked into 700-character semantic segments with page/header preservation.
              </div>
            </div>

            <div className="flex gap-3 items-start p-3 bg-surface-low rounded-xl border border-neutral-border/30">
              <Search className="w-4 h-4 text-grounding-emerald shrink-0 mt-0.5" />
              <div>
                <strong className="text-neutral-dark block font-semibold">2. Hybrid Retrieval & RRF</strong>
                FAISS dense vector search and BM25 sparse keyword search run concurrently and fuse via Reciprocal Rank Fusion (RRF).
              </div>
            </div>

            <div className="flex gap-3 items-start p-3 bg-surface-low rounded-xl border border-neutral-border/30">
              <ShieldCheck className="w-4 h-4 text-primary shrink-0 mt-0.5" />
              <div>
                <strong className="text-neutral-dark block font-semibold">3. FlashRank Cross-Encoder Re-ranking</strong>
                Top candidates are scored with cross-attention to deliver the top-4 most discriminative chunks.
              </div>
            </div>

            <div className="flex gap-3 items-start p-3 bg-surface-low rounded-xl border border-neutral-border/30">
              <Sparkles className="w-4 h-4 text-primary shrink-0 mt-0.5" />
              <div>
                <strong className="text-neutral-dark block font-semibold">4. Grounded Token Streaming</strong>
                Qwen streams verified citations formatted as clickable chips <span className="font-mono text-primary font-bold">[1]</span> linking directly to verbatim excerpts.
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-neutral-border/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-xl hover:bg-primary-hover transition-colors cursor-pointer"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
