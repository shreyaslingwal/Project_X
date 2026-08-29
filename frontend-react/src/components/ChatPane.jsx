import React, { useRef, useEffect } from 'react';
import { ArrowUp, Sparkles, Loader2, BookOpen, AlertCircle } from 'lucide-react';
import MessageBubble from './MessageBubble';

export default function ChatPane({
  messages,
  inputQuery,
  setInputQuery,
  onSubmit,
  isStreaming,
  onCitationClick,
  activeSourcesCount,
  errorMessage,
}) {
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Handle textarea keypress (Enter to submit, Shift+Enter for newline)
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && inputQuery.trim()) {
        onSubmit();
      }
    }
  };

  const handlePromptClick = (text) => {
    setInputQuery(text);
    textareaRef.current?.focus();
  };

  return (
    <main className="flex-1 flex flex-col min-w-0 bg-surface relative overflow-hidden">
      {/* Top Banner / Scoped Context Bar */}
      <div className="px-8 py-3.5 border-b border-neutral-border/40 flex justify-between items-center bg-surface/90 backdrop-blur z-10 sticky top-0">
        <div className="flex items-center gap-2 text-xs text-neutral-muted">
          <BookOpen className="w-3.5 h-3.5 text-primary" />
          <span>
            Grounding in <strong className="text-neutral-dark">{activeSourcesCount}</strong> active document{activeSourcesCount === 1 ? '' : 's'}
          </span>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 lg:px-16 py-6 space-y-6 scroll-smooth pb-36">
        {messages.length === 0 ? (
          /* Welcome State */
          <div className="max-w-2xl mx-auto py-12 text-center">
            <div className="w-12 h-12 rounded-2xl bg-primary-fixed text-primary flex items-center justify-center mx-auto mb-4 shadow-soft">
              <Sparkles className="w-6 h-6" />
            </div>
            <h2 className="font-display font-bold text-2xl text-neutral-dark mb-2">
              Research Synthesis & Grounded Chat
            </h2>
            <p className="text-sm text-neutral-muted leading-relaxed max-w-md mx-auto mb-8 font-body">
              Ask questions across your uploaded documents. Answers are strictly grounded with verbatim provenance citations.
            </p>

            {/* Quick Starters */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left max-w-lg mx-auto">
              <button
                onClick={() => handlePromptClick('Summarize the main themes and conclusions across the documents.')}
                className="p-3 bg-white border border-neutral-border/50 hover:border-primary/50 hover:bg-surface-low rounded-xl text-xs text-neutral-muted hover:text-neutral-dark transition-all duration-150 text-left shadow-xs cursor-pointer"
              >
                <span className="font-semibold block text-neutral-dark mb-0.5">Executive Summary</span>
                Summarize the main themes and conclusions.
              </button>
              <button
                onClick={() => handlePromptClick('Extract all key methodologies, metrics, and quantitative findings.')}
                className="p-3 bg-white border border-neutral-border/50 hover:border-primary/50 hover:bg-surface-low rounded-xl text-xs text-neutral-muted hover:text-neutral-dark transition-all duration-150 text-left shadow-xs cursor-pointer"
              >
                <span className="font-semibold block text-neutral-dark mb-0.5">Methodology & Metrics</span>
                Extract key methodologies and findings.
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <MessageBubble
              key={index}
              message={msg}
              onCitationClick={onCitationClick}
            />
          ))
        )}

        {/* Error Banner */}
        {errorMessage && (
          <div className="max-w-3xl mx-auto p-4 bg-error-container text-error rounded-xl border border-error/30 flex items-center gap-3 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Prompt Input Area */}
      <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-surface via-surface/95 to-transparent pt-8 pb-5 px-4 md:px-8 lg:px-16 z-20">
        <div className="max-w-3xl mx-auto relative shadow-soft rounded-2xl bg-white border border-neutral-border/70 focus-within:border-primary/60 focus-within:ring-2 focus-within:ring-primary/10 transition-all duration-200">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              activeSourcesCount === 0
                ? 'Upload and select at least one document to start...'
                : 'Ask a question grounded in your documents...'
            }
            disabled={isStreaming || activeSourcesCount === 0}
            className="w-full bg-transparent border-0 focus:outline-hidden focus:ring-0 resize-none py-3.5 pl-4 pr-14 text-neutral-dark placeholder:text-neutral-light text-sm max-h-36 min-h-[50px] font-body disabled:opacity-60"
          />

          <div className="absolute right-2.5 bottom-2 flex items-center gap-1.5">
            <button
              type="button"
              onClick={onSubmit}
              disabled={isStreaming || !inputQuery.trim() || activeSourcesCount === 0}
              className="p-2 bg-primary text-white rounded-xl hover:bg-primary-hover transition-colors shadow-xs cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              title="Send message"
            >
              {isStreaming ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowUp className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        <div className="text-center mt-2">
          <p className="text-[10px] text-neutral-light font-body">
            Responses are generated by local Ollama and grounded with FlashRank citations.
          </p>
        </div>
      </div>
    </main>
  );
}
