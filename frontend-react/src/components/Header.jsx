import React from 'react';
import { Sparkles, Trash2, Search, Settings, HelpCircle, BookOpen, Layers } from 'lucide-react';

export default function Header({
  activeTab,
  onTabChange,
  searchQuery,
  onSearchChange,
  onOpenSettings,
  onOpenHelp,
  onClearChat,
  isClearing,
  activeSourcesCount,
  totalSourcesCount,
}) {
  return (
    <header className="flex justify-between items-center px-6 w-full border-b border-neutral-border/60 bg-surface h-16 flex-shrink-0 z-30 shadow-soft">
      {/* Brand & Tabs */}
      <div className="flex items-center gap-8 h-full">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center shadow-xs">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="font-display font-bold text-primary text-2xl tracking-tight leading-none">
            Project X
          </span>
        </div>

        {/* Centered Navigation Tabs (Stitch Style) */}
        <nav className="hidden md:flex items-center gap-6 h-full pt-1">
          <button
            onClick={() => onTabChange('chat')}
            className={`h-full flex items-center font-body text-sm font-medium transition-all px-1 cursor-pointer ${
              activeTab === 'chat'
                ? 'text-primary border-b-2 border-primary font-bold'
                : 'text-neutral-muted hover:text-primary'
            }`}
          >
            Chat & Workspace
          </button>
          <button
            onClick={() => onTabChange('notebooks')}
            className={`h-full flex items-center font-body text-sm font-medium transition-all px-1 cursor-pointer ${
              activeTab === 'notebooks'
                ? 'text-primary border-b-2 border-primary font-bold'
                : 'text-neutral-muted hover:text-primary'
            }`}
          >
            Notebooks Library
          </button>
        </nav>
      </div>

      {/* Right Controls (Search, Settings, Help, User Avatar, Clear Chat) */}
      <div className="flex items-center gap-3">
        {/* Document Search Bar */}
        <div className="relative hidden sm:block">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-light" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search documents..."
            className="pl-8 pr-3 py-1.5 bg-surface-low border border-neutral-border/60 rounded-full text-xs w-48 focus:outline-hidden focus:border-primary focus:ring-1 focus:ring-primary/20 text-neutral-dark placeholder:text-neutral-light font-body transition-all"
          />
        </div>

        {/* Clear Chat */}
        {activeTab === 'chat' && (
          <button
            onClick={onClearChat}
            disabled={isClearing}
            className="p-2 text-neutral-muted hover:text-error hover:bg-error-container/40 rounded-full transition-all cursor-pointer disabled:opacity-50"
            title="Clear Chat Session"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          className="p-2 text-neutral-muted hover:text-primary hover:bg-surface-container rounded-full transition-all cursor-pointer"
          title="Pipeline Settings"
        >
          <Settings className="w-4 h-4" />
        </button>

        {/* Help Button */}
        <button
          onClick={onOpenHelp}
          className="p-2 text-neutral-muted hover:text-primary hover:bg-surface-container rounded-full transition-all cursor-pointer"
          title="Architecture & Help"
        >
          <HelpCircle className="w-4 h-4" />
        </button>

        {/* Researcher Avatar (from Stitch) */}
        <div className="w-8 h-8 rounded-full overflow-hidden border border-neutral-border/60 ml-1 flex-shrink-0 bg-primary-fixed text-primary flex items-center justify-center font-bold text-xs font-mono">
          PX
        </div>
      </div>
    </header>
  );
}
