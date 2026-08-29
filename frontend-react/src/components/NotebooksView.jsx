import React from 'react';
import { Plus, BookOpen, Clock, Users, ArrowRight, Layers, FileText, Sparkles } from 'lucide-react';

export default function NotebooksView({
  notebooks,
  activeNotebookId,
  onSelectNotebook,
  onCreateNotebook,
  documentsCount,
}) {
  return (
    <main className="flex-1 overflow-y-auto bg-background p-8 lg:p-12 w-full animate-in fade-in duration-200">
      <div className="max-w-5xl mx-auto">
        {/* Page Header */}
        <div className="flex justify-between items-end mb-8 border-b border-neutral-border/60 pb-6">
          <div>
            <h1 className="font-display text-4xl text-neutral-dark font-semibold tracking-tight">
              Notebooks Library
            </h1>
            <p className="font-body text-neutral-muted mt-2 text-sm max-w-lg">
              Curated workspaces for grounded synthesis, deep research, and provenance tracking.
            </p>
          </div>
          <button
            onClick={onCreateNotebook}
            className="px-4 py-2.5 bg-primary text-white font-medium text-sm rounded-xl hover:bg-primary-hover shadow-soft transition-all duration-200 flex items-center gap-2 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Notebook</span>
          </button>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Start Fresh Notebook Action Card */}
          <button
            onClick={onCreateNotebook}
            className="col-span-1 border-2 border-dashed border-neutral-border/80 rounded-2xl p-6 flex flex-col items-center justify-center text-neutral-muted hover:text-primary hover:border-primary/50 hover:bg-surface-low/50 transition-all duration-300 min-h-[260px] group cursor-pointer"
          >
            <div className="w-12 h-12 rounded-full bg-surface-container flex items-center justify-center mb-3 group-hover:bg-primary-fixed group-hover:scale-110 transition-all text-primary">
              <Plus className="w-6 h-6" />
            </div>
            <span className="font-display font-semibold text-lg text-neutral-dark group-hover:text-primary transition-colors">
              Start Fresh Notebook
            </span>
            <span className="text-xs text-neutral-light mt-1 font-body">
              Initialize a clean research space
            </span>
          </button>

          {/* Featured / Active Notebook (Spans 2 columns on md+) */}
          {notebooks.map((nb, idx) => {
            const isActive = nb.id === activeNotebookId;
            const isFeatured = idx === 0;

            return (
              <article
                key={nb.id}
                onClick={() => onSelectNotebook(nb.id)}
                className={`rounded-2xl p-6 md:p-8 border shadow-soft flex flex-col justify-between group transition-all duration-300 relative overflow-hidden cursor-pointer min-h-[260px] ${
                  isFeatured ? 'col-span-1 md:col-span-2 bg-surface-lowest' : 'col-span-1 bg-surface-lowest'
                } ${
                  isActive
                    ? 'border-primary/60 ring-2 ring-primary/20 bg-white'
                    : 'border-neutral-border/50 hover:border-primary/40 bg-surface-lowest'
                }`}
              >
                {/* Decorative background watermark */}
                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity text-primary">
                  <Sparkles className="w-24 h-24" />
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-3">
                    {isActive ? (
                      <span className="px-2.5 py-0.5 bg-grounding-badge text-grounding text-[11px] font-bold rounded-full font-mono uppercase tracking-wider border border-grounding/20">
                        Active Workspace
                      </span>
                    ) : (
                      <span className="px-2.5 py-0.5 bg-surface-container text-neutral-muted text-[11px] font-medium rounded-full font-mono">
                        Saved Session
                      </span>
                    )}
                    <span className="text-neutral-light text-xs font-body flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {nb.updatedAt || 'Recently updated'}
                    </span>
                  </div>

                  <h3 className="font-display text-2xl text-neutral-dark font-semibold leading-tight mb-2 group-hover:text-primary transition-colors">
                    {nb.title}
                  </h3>
                  <p className="font-body text-neutral-muted text-sm leading-relaxed max-w-xl line-clamp-3">
                    {nb.description}
                  </p>
                </div>

                {/* Footer stats */}
                <div className="mt-6 flex items-center justify-between border-t border-neutral-border/30 pt-4 text-xs text-neutral-muted">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1.5 font-mono">
                      <FileText className="w-3.5 h-3.5 text-primary" />
                      {nb.sourcesCount ?? documentsCount} Sources
                    </span>
                    <span className="flex items-center gap-1.5 font-mono">
                      <Layers className="w-3.5 h-3.5 text-neutral-light" />
                      {nb.turnsCount ?? 0} Turns
                    </span>
                  </div>

                  <div className="flex items-center gap-1 text-primary font-semibold group-hover:translate-x-1 transition-transform">
                    <span>Open Workspace</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </main>
  );
}
