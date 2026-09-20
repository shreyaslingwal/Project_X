import React, { useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, CheckCheck, XSquare, Plus, FileUp, Loader2, Search } from 'lucide-react';
import DocumentCard from './DocumentCard';

export default function SourceSidebar({
  documents,
  selectedDocIds,
  onToggleDoc,
  onSelectAll,
  onClearAll,
  onUploadMultiple,
  onDeleteDoc,
  onSummarize,
  uploadProgress,
  isUploading,
  isCollapsed,
  onToggleCollapse,
  searchQuery,
}) {
  const fileInputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUploadMultiple(Array.from(files));
      e.target.value = '';
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      onUploadMultiple(Array.from(files));
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  // Filter documents by search query if provided
  const filteredDocuments = documents.filter((doc) => {
    if (!searchQuery || !searchQuery.trim()) return true;
    return doc.source.toLowerCase().includes(searchQuery.toLowerCase());
  });

  return (
    <aside
      className={`bg-surface-low border-r border-neutral-border/60 flex flex-col h-full relative transition-all duration-300 z-20 ${
        isCollapsed ? 'w-14' : 'w-72'
      }`}
    >
      {/* Collapse Toggle Button */}
      <button
        onClick={onToggleCollapse}
        className="absolute -right-3.5 top-4.5 bg-primary text-white hover:bg-primary-hover border border-primary/20 rounded-full p-1.5 shadow-md transition-all z-30 cursor-pointer flex items-center justify-center hover:scale-105 active:scale-95"
        title={isCollapsed ? 'Expand sources panel' : 'Collapse sources panel'}
      >
        {isCollapsed ? (
          <ChevronRight className="w-3.5 h-3.5" />
        ) : (
          <ChevronLeft className="w-3.5 h-3.5" />
        )}
      </button>

      {/* Expanded Content */}
      {!isCollapsed ? (
        <div className="flex flex-col h-full p-4 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="font-display font-bold text-base text-neutral-dark">
                Sources
              </h2>
              <p className="text-[11px] text-neutral-light">
                {documents.length} {documents.length === 1 ? 'document' : 'documents'} indexed
              </p>
            </div>

            {documents.length > 0 && (
              <div className="flex items-center gap-1">
                <button
                  onClick={onSelectAll}
                  className="p-1 text-neutral-light hover:text-primary hover:bg-surface-container rounded transition-colors text-xs"
                  title="Select all documents"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={onClearAll}
                  className="p-1 text-neutral-light hover:text-error hover:bg-surface-container rounded transition-colors text-xs"
                  title="Deselect all documents"
                >
                  <XSquare className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>

          {/* Multiple File Upload Drop Zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all duration-200 mb-4 ${
              isDragOver
                ? 'border-primary bg-primary-fixed/40'
                : 'border-neutral-border/80 hover:border-primary/60 hover:bg-surface-container/60 bg-white/70'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.md,.markdown"
              onChange={handleFileChange}
              className="hidden"
            />
            {isUploading ? (
              <div className="flex flex-col items-center justify-center py-2 text-primary">
                <Loader2 className="w-5 h-5 animate-spin mb-1" />
                <span className="text-xs font-semibold">
                  {uploadProgress
                    ? `Ingesting ${uploadProgress.completed} of ${uploadProgress.total} files...`
                    : 'Ingesting documents...'}
                </span>
                <span className="text-[10px] text-neutral-light mt-0.5">Chunking & embedding in parallel</span>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-1">
                <div className="w-8 h-8 rounded-full bg-primary-fixed flex items-center justify-center text-primary mb-1.5 shadow-xs">
                  <FileUp className="w-4 h-4" />
                </div>
                <span className="text-xs font-semibold text-neutral-dark">
                  Upload PDF or Markdown
                </span>
                <span className="text-[10px] text-neutral-light mt-0.5">
                  Select or drag multiple files
                </span>
              </div>
            )}
          </div>

          {/* Document List */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {filteredDocuments.length === 0 ? (
              <div className="text-center py-8 px-2 text-neutral-light">
                <p className="text-xs">
                  {searchQuery ? 'No matching documents found.' : 'No documents uploaded yet.'}
                </p>
                <p className="text-[11px] mt-1 text-neutral-light/80">
                  {searchQuery ? 'Try another search term.' : 'Add files to ground your research sessions.'}
                </p>
              </div>
            ) : (
              filteredDocuments.map((doc) => (
                <DocumentCard
                  key={doc.doc_id}
                  doc={doc}
                  isSelected={selectedDocIds.has(doc.doc_id)}
                  onToggle={onToggleDoc}
                  onDelete={onDeleteDoc}
                  onSummarize={onSummarize}
                />
              ))
            )}
          </div>
        </div>
      ) : (
        /* Collapsed Rail */
        <div className="flex flex-col items-center py-4 h-full gap-4">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center hover:bg-primary-hover shadow-soft transition-colors cursor-pointer"
            title="Upload source files"
          >
            <Plus className="w-4 h-4" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.md,.markdown"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="text-[10px] font-bold text-neutral-light rotate-90 mt-8 tracking-widest uppercase">
            Sources ({documents.length})
          </div>
        </div>
      )}
    </aside>
  );
}
