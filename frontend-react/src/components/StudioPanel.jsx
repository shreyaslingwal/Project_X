import React, { useRef, useEffect, useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Sparkles,
  ShieldCheck,
  ChevronRight,
  ChevronLeft,
  FileText,
  Bookmark,
  Hash,
  CheckCircle2,
  Quote,
  X,
  Copy,
  Check,
  RefreshCw,
  Loader2,
  Zap,
  BookOpen,
  Layers,
} from 'lucide-react';

export default function StudioPanel({
  // Panel state
  isOpen,
  onToggleOpen,
  panelMode,        // 'studio' | 'inspector'
  onSetPanelMode,

  // Studio state
  documents,
  selectedDocIds,
  studioSelectedDocId,  // 'all' | specific doc_id
  onStudioDocChange,
  summaryText,
  isSummarizing,
  onGenerateSummary,
  onRegenerateSummary,
  summaryError,

  // Inspector state (from CitationInspector)
  activeCitation,
  activeCitationIndex,
  onCloseInspector,

  // Chat integration for suggested queries
  onSuggestedQuery,
}) {
  const [copied, setCopied] = useState(false);
  const contentRef = useRef(null);

  // Panel resizing state
  const [panelWidth, setPanelWidth] = useState(384);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartXRef = useRef(0);
  const dragStartWidthRef = useRef(384);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartXRef.current = e.clientX;
    dragStartWidthRef.current = panelWidth;

    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    const handleMouseMove = (moveEvent) => {
      const delta = dragStartXRef.current - moveEvent.clientX;
      const rawNewWidth = dragStartWidthRef.current + delta;
      const minWidth = 320;
      const maxWidth = Math.min(window.innerWidth * 0.75, Math.max(minWidth, window.innerWidth - 380));
      const clampedWidth = Math.max(minWidth, Math.min(maxWidth, rawNewWidth));
      setPanelWidth(clampedWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  }, [panelWidth]);

  // Clean up global cursor and user-select if unmounted while dragging
  useEffect(() => {
    return () => {
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, []);

  // Auto-scroll during streaming
  useEffect(() => {
    if (isSummarizing && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [summaryText, isSummarizing]);

  // Copy summary to clipboard
  const handleCopy = async () => {
    if (!summaryText) return;
    try {
      await navigator.clipboard.writeText(summaryText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.warn('Clipboard write failed');
    }
  };

  // Extract suggested questions from summary text (lines starting with "Q: ")
  const suggestedQuestions = React.useMemo(() => {
    if (!summaryText) return [];
    const lines = summaryText.split('\n');
    return lines
      .map((line) => line.trim())
      .filter((line) => line.startsWith('Q: ') || line.startsWith('- Q: '))
      .map((line) => line.replace(/^-\s*/, '').replace(/^Q:\s*/, '').trim())
      .filter((q) => q.length > 10)
      .slice(0, 4);
  }, [summaryText]);

  // Build the scope label for display
  const scopeLabel = React.useMemo(() => {
    if (studioSelectedDocId === 'all') {
      const count = selectedDocIds ? selectedDocIds.size : 0;
      return `All Active Sources (${count})`;
    }
    const doc = documents.find((d) => d.doc_id === studioSelectedDocId);
    return doc ? doc.source : 'Selected Document';
  }, [studioSelectedDocId, selectedDocIds, documents]);

  if (!isOpen) {
    return (
      <button
        onClick={onToggleOpen}
        className="absolute right-0 top-4.5 bg-primary text-white hover:bg-primary-hover border border-primary/20 rounded-l-full pl-2 pr-1.5 py-1.5 shadow-md transition-all z-30 cursor-pointer flex items-center gap-1 hover:scale-105 active:scale-95"
        title="Open Studio panel"
      >
        <Sparkles className="w-3.5 h-3.5" />
        <ChevronLeft className="w-3.5 h-3.5" />
      </button>
    );
  }

  return (
    <aside
      style={{ width: `${panelWidth}px` }}
      className={`relative flex-shrink-0 bg-surface-lowest border-l flex flex-col h-full z-10 shadow-soft animate-in slide-in-from-right duration-200 ${
        isDragging ? 'border-primary/50' : 'border-neutral-border/60'
      }`}
    >
      {/* Left Border Drag Handle with Double-Arrow Cursor */}
      <div
        onMouseDown={handleMouseDown}
        className="absolute left-0 top-0 bottom-0 w-2 -translate-x-1/2 cursor-col-resize z-30 group flex items-center justify-center select-none"
        title="Drag to resize panel"
      >
        <div
          className={`w-1 h-8 rounded-full transition-colors duration-150 ${
            isDragging ? 'bg-primary' : 'bg-transparent group-hover:bg-primary/50'
          }`}
        />
      </div>

      {/* Header with Mode Tabs */}
      <div className="border-b border-neutral-border/40 bg-surface-low/50 flex-shrink-0">
        <div className="flex items-center justify-between px-4 pt-3 pb-0">
          {/* Mode Tabs */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => onSetPanelMode('studio')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-xs font-medium transition-all cursor-pointer border-b-2 ${
                panelMode === 'studio'
                  ? 'text-primary border-primary bg-surface-lowest font-bold'
                  : 'text-neutral-muted border-transparent hover:text-primary hover:bg-surface-container/50'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Studio
            </button>
            <button
              onClick={() => onSetPanelMode('inspector')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-xs font-medium transition-all cursor-pointer border-b-2 ${
                panelMode === 'inspector'
                  ? 'text-primary border-primary bg-surface-lowest font-bold'
                  : 'text-neutral-muted border-transparent hover:text-primary hover:bg-surface-container/50'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Inspector
              {activeCitation && (
                <span className="ml-1 w-4 h-4 rounded bg-primary-fixed text-primary flex items-center justify-center font-mono font-bold text-[10px]">
                  {activeCitationIndex}
                </span>
              )}
            </button>
          </div>

          {/* Collapse Button */}
          <button
            onClick={onToggleOpen}
            className="p-1 text-neutral-light hover:text-neutral-dark hover:bg-surface-container rounded transition-colors cursor-pointer"
            title="Collapse panel"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Panel Content */}
      {panelMode === 'studio' ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Scope Selector */}
          <div className="p-4 border-b border-neutral-border/40 flex-shrink-0">
            <label className="text-[10px] uppercase tracking-wider text-neutral-muted font-bold mb-1.5 block">
              Summarize Scope
            </label>
            <select
              value={studioSelectedDocId}
              onChange={(e) => onStudioDocChange(e.target.value)}
              className="w-full px-3 py-2 bg-surface-low border border-neutral-border/60 rounded-lg text-xs text-neutral-dark font-body focus:outline-hidden focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all cursor-pointer"
            >
              <option value="all">All Active Sources ({selectedDocIds ? selectedDocIds.size : 0})</option>
              {documents.map((doc) => (
                <option key={doc.doc_id} value={doc.doc_id}>
                  {doc.source}
                </option>
              ))}
            </select>
          </div>

          {/* Summary Content Area */}
          <div ref={contentRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {!summaryText && !isSummarizing && !summaryError ? (
              /* Generate Action Card */
              <div className="flex flex-col items-center justify-center text-center py-10 px-4">
                <div className="w-14 h-14 rounded-2xl bg-primary-fixed/60 flex items-center justify-center mb-4">
                  <BookOpen className="w-7 h-7 text-primary" />
                </div>
                <h3 className="font-display font-bold text-base text-neutral-dark mb-2">
                  Document Briefing
                </h3>
                <p className="text-xs text-neutral-muted leading-relaxed mb-5 max-w-[260px]">
                  Generate a structured summary with key topics, core takeaways,
                  and follow-up questions from your sources.
                </p>
                <p className="text-[11px] text-neutral-light mb-4 font-mono">
                  {scopeLabel}
                </p>
                <button
                  onClick={onGenerateSummary}
                  disabled={!documents || documents.length === 0}
                  className="flex items-center gap-2 px-5 py-2.5 bg-primary text-white rounded-xl font-medium text-sm hover:bg-primary-hover shadow-sm transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-md active:scale-[0.98]"
                >
                  <Zap className="w-4 h-4" />
                  Generate Briefing
                </button>
              </div>
            ) : (
              <>
                {/* Streaming or Complete Summary */}
                {summaryError && (
                  <div className="p-3 bg-error-container/40 border border-error/20 rounded-lg text-error text-xs">
                    {summaryError}
                  </div>
                )}

                {(summaryText || isSummarizing) && (
                  <div className="prose prose-sm max-w-none text-neutral-dark font-body text-xs leading-relaxed">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h2: ({ children }) => (
                          <h2 className="font-display font-bold text-sm text-primary mt-5 mb-2 pb-1 border-b border-neutral-border/30">
                            {children}
                          </h2>
                        ),
                        h3: ({ children }) => (
                          <h3 className="font-display font-bold text-xs text-neutral-dark mt-3 mb-1">
                            {children}
                          </h3>
                        ),
                        ul: ({ children }) => (
                          <ul className="space-y-1 ml-3 list-disc marker:text-primary/40">
                            {children}
                          </ul>
                        ),
                        li: ({ children }) => (
                          <li className="text-xs leading-relaxed text-neutral-dark/90">
                            {children}
                          </li>
                        ),
                        strong: ({ children }) => (
                          <strong className="font-semibold text-neutral-dark">{children}</strong>
                        ),
                        p: ({ children }) => (
                          <p className="text-xs leading-relaxed mb-2">{children}</p>
                        ),
                      }}
                    >
                      {summaryText}
                    </ReactMarkdown>

                    {isSummarizing && (
                      <div className="flex items-center gap-2 mt-3 text-primary text-[11px]">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span className="font-medium">Generating briefing...</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Suggested Follow-up Questions */}
                {!isSummarizing && suggestedQuestions.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-neutral-border/30">
                    <p className="text-[10px] uppercase tracking-wider text-neutral-muted font-bold mb-2">
                      Explore Further
                    </p>
                    <div className="space-y-1.5">
                      {suggestedQuestions.map((q, idx) => (
                        <button
                          key={idx}
                          onClick={() => onSuggestedQuery(q)}
                          className="w-full text-left px-3 py-2 bg-surface-low/60 hover:bg-primary-fixed/40 border border-neutral-border/40 hover:border-primary/30 rounded-lg text-xs text-neutral-dark transition-all cursor-pointer group"
                        >
                          <span className="text-primary font-mono text-[10px] mr-1.5 opacity-60 group-hover:opacity-100">
                            Q{idx + 1}
                          </span>
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Toolbar */}
                {!isSummarizing && summaryText && (
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-neutral-border/30">
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-low border border-neutral-border/50 rounded-lg text-[11px] text-neutral-muted hover:text-primary hover:border-primary/30 transition-all cursor-pointer"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3 h-3 text-grounding-emerald" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          Copy
                        </>
                      )}
                    </button>
                    <button
                      onClick={onRegenerateSummary}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-low border border-neutral-border/50 rounded-lg text-[11px] text-neutral-muted hover:text-primary hover:border-primary/30 transition-all cursor-pointer"
                    >
                      <RefreshCw className="w-3 h-3" />
                      Regenerate
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      ) : (
        /* Inspector Mode (refactored from CitationInspector) */
        <div className="flex-1 flex flex-col overflow-hidden">
          {activeCitation ? (
            <>
              {/* Inspector Header */}
              <div className="p-4 border-b border-neutral-border/40 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded bg-primary-fixed text-primary flex items-center justify-center font-mono font-bold text-xs">
                    [{activeCitationIndex}]
                  </div>
                  <h3 className="font-display font-bold text-sm text-neutral-dark">
                    Citation Provenance
                  </h3>
                </div>
              </div>

              {/* Inspector Content */}
              <div className="p-4 space-y-4 overflow-y-auto flex-1 text-xs">
                {/* Source File Card */}
                <div className="p-3 bg-surface-low rounded-xl border border-neutral-border/50">
                  <div className="flex items-center gap-2 text-primary font-semibold mb-1">
                    <FileText className="w-4 h-4" />
                    <span className="truncate">{activeCitation.source}</span>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2 text-[11px] text-neutral-muted font-mono">
                    {activeCitation.page && (
                      <span className="px-2 py-0.5 bg-white rounded border border-neutral-border/40 flex items-center gap-1">
                        <Bookmark className="w-3 h-3 text-primary" />
                        Page {activeCitation.page}
                      </span>
                    )}
                    {activeCitation.section && (
                      <span className="px-2 py-0.5 bg-white rounded border border-neutral-border/40 truncate max-w-[200px]">
                        {activeCitation.section}
                      </span>
                    )}
                    {activeCitation.chunk_id && (
                      <span className="px-2 py-0.5 bg-white rounded border border-neutral-border/40 flex items-center gap-1">
                        <Hash className="w-3 h-3 text-neutral-light" />
                        {activeCitation.chunk_id}
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
                    {activeCitation.snippet || activeCitation.text || 'No text snippet available.'}
                  </div>
                </div>
              </div>
            </>
          ) : (
            /* No Citation Selected */
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
              <ShieldCheck className="w-10 h-10 text-neutral-light/40 mb-3" />
              <p className="text-xs text-neutral-muted leading-relaxed max-w-[220px]">
                Click a citation badge <span className="font-mono text-primary">[1]</span> in the
                chat to inspect its source provenance here.
              </p>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
