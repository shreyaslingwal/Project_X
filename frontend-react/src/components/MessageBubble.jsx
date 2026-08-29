import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Sparkles, User, FileText, ChevronRight } from 'lucide-react';
import CitationBadge from './CitationBadge';

export default function MessageBubble({ message, onCitationClick }) {
  const isUser = message.role === 'user';

  // Helper to render text with clickable citation badges
  const renderTextWithCitations = (text, citations = []) => {
    if (!text) return null;

    // Match patterns like [1], [2], [1, 2]
    const citationRegex = /\[(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(text)) !== null) {
      // Text before citation
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }

      const citNum = parseInt(match[1], 10);
      const cit = citations.find((c) => c.source_index === citNum) || citations[citNum - 1];

      parts.push(
        <CitationBadge
          key={`cit-${match.index}`}
          index={citNum}
          citation={cit}
          onClick={onCitationClick}
        />
      );

      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts;
  };

  // Custom components for ReactMarkdown
  const markdownComponents = {
    // Intercept paragraph text to render citation chips
    p: ({ children }) => {
      if (typeof children === 'string') {
        return <p className="mb-3 leading-relaxed">{renderTextWithCitations(children, message.citations)}</p>;
      }
      return <p className="mb-3 leading-relaxed">{children}</p>;
    },
    code: ({ node, inline, className, children, ...props }) => {
      if (inline) {
        return (
          <code className="px-1.5 py-0.5 bg-surface-container rounded font-mono text-xs text-neutral-dark border border-neutral-border/40" {...props}>
            {children}
          </code>
        );
      }
      return (
        <pre className="p-3 my-3 bg-neutral-dark text-surface rounded-xl overflow-x-auto font-mono text-xs border border-neutral-dark/80">
          <code {...props}>{children}</code>
        </pre>
      );
    },
  };

  if (isUser) {
    return (
      <div className="flex gap-4 max-w-3xl mx-auto flex-row-reverse">
        <div className="w-8 h-8 rounded-full bg-primary-fixed border border-neutral-border/60 flex items-center justify-center text-primary flex-shrink-0 shadow-xs">
          <User className="w-4 h-4" />
        </div>
        <div className="flex-1 pt-0.5 flex justify-end">
          <div className="bg-surface-low border border-neutral-border/50 rounded-2xl rounded-tr-sm px-5 py-3 shadow-soft max-w-[85%] text-sm leading-relaxed text-neutral-dark font-body">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4 max-w-3xl mx-auto">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center flex-shrink-0 shadow-xs mt-1">
        <Sparkles className="w-4 h-4" />
      </div>

      {/* Card Content */}
      <div className="flex-1 pt-0.5 min-w-0">
        <div className="bg-white border border-neutral-border/50 rounded-xl p-6 shadow-soft">
          {/* Main Markdown Text */}
          <div className="prose prose-stone max-w-none text-sm text-neutral-dark font-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Sources Cited Section */}
          {message.citations && message.citations.length > 0 && (
            <div className="mt-5 pt-4 border-t border-neutral-border/40">
              <h4 className="text-[11px] font-bold text-neutral-light uppercase tracking-wider mb-2">
                Sources Cited ({message.citations.length})
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {message.citations.map((cit, idx) => (
                  <button
                    key={idx}
                    onClick={() => onCitationClick(cit, cit.source_index || idx + 1)}
                    className="flex items-center gap-2 p-2 bg-surface-low/60 hover:bg-surface-high border border-neutral-border/40 rounded-lg text-left text-xs transition-colors cursor-pointer group"
                  >
                    <span className="w-4 text-center font-mono font-bold text-primary text-[11px]">
                      [{cit.source_index || idx + 1}]
                    </span>
                    <span className="truncate flex-1 text-neutral-muted group-hover:text-neutral-dark font-medium">
                      {cit.source}
                      {cit.page ? ` (pg. ${cit.page})` : ''}
                    </span>
                    <ChevronRight className="w-3 h-3 text-neutral-light group-hover:text-primary transition-transform group-hover:translate-x-0.5" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
