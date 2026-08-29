import React from 'react';
import { X, Sliders, Cpu, Database, Shield, Zap, Sparkles } from 'lucide-react';

export default function SettingsModal({ isOpen, onClose, health }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-dark/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-surface-lowest border border-neutral-border/60 rounded-2xl max-w-md w-full p-6 shadow-dropdown relative">
        <div className="flex items-center justify-between border-b border-neutral-border/40 pb-4 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary-fixed text-primary flex items-center justify-center">
              <Sliders className="w-4 h-4" />
            </div>
            <h3 className="font-display font-bold text-lg text-neutral-dark">
              Pipeline Settings
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-neutral-light hover:text-neutral-dark hover:bg-surface-container rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4 text-xs">
          {/* Active Generation Model */}
          <div className="p-3 bg-surface-low rounded-xl border border-neutral-border/40 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-neutral-dark flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-primary" />
                Generator LLM (Ollama)
              </span>
              <span className="font-mono text-primary font-bold">
                {health?.generator_model || 'qwen3.5:4b'}
              </span>
            </div>
            <p className="text-[11px] text-neutral-muted">
              Streaming conversational response generation.
            </p>
          </div>

          {/* Query Rewriter */}
          <div className="p-3 bg-surface-low rounded-xl border border-neutral-border/40 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-neutral-dark flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-primary" />
                Query Rewriter
              </span>
              <span className="font-mono text-neutral-dark font-bold">
                {health?.rewriter_model || 'qwen3:4b'}
              </span>
            </div>
            <p className="text-[11px] text-neutral-muted">
              Contextualizes follow-up questions before retrieval.
            </p>
          </div>

          {/* Hybrid Retrieval Stack */}
          <div className="p-3 bg-surface-low rounded-xl border border-neutral-border/40 space-y-2">
            <div className="font-semibold text-neutral-dark flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-grounding-emerald" />
              Hybrid Retrieval Architecture
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
              <div className="p-2 bg-white rounded border border-neutral-border/30">
                <div className="text-neutral-light text-[10px]">Vector Search</div>
                <div className="font-bold text-neutral-dark">FAISS FlatIP</div>
                <div className="text-[9px] text-neutral-muted">bge-small-en-v1.5</div>
              </div>
              <div className="p-2 bg-white rounded border border-neutral-border/30">
                <div className="text-neutral-light text-[10px]">Lexical Search</div>
                <div className="font-bold text-neutral-dark">BM25 Okapi</div>
                <div className="text-[9px] text-neutral-muted">Exact keywords</div>
              </div>
            </div>
            <div className="p-2 bg-white rounded border border-neutral-border/30 text-[11px] font-mono">
              <div className="text-neutral-light text-[10px]">Cross-Encoder Re-ranker</div>
              <div className="font-bold text-neutral-dark">FlashRank (ms-marco-MiniLM)</div>
            </div>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-neutral-border/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-xl hover:bg-primary-hover transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
