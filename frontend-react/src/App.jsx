import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SourceSidebar from './components/SourceSidebar';
import ChatPane from './components/ChatPane';
import CitationInspector from './components/CitationInspector';
import NotebooksView from './components/NotebooksView';
import SettingsModal from './components/SettingsModal';
import HelpModal from './components/HelpModal';
import {
  fetchHealth,
  fetchDocuments,
  uploadDocuments,
  deleteDocument,
  streamChat,
  clearChat,
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'notebooks'
  const [searchQuery, setSearchQuery] = useState('');
  const [health, setHealth] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState(new Set());
  const [messages, setMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [isClearing, setIsClearing] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);
  const [activeCitationIndex, setActiveCitationIndex] = useState(1);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  // Notebooks state (Stitch Screen 2 alignment)
  const [notebooks, setNotebooks] = useState([
    {
      id: 'default',
      title: 'Main Research Workspace',
      description: 'Grounded conversational analysis, multi-document cross-referencing, and verifiable provenance tracking.',
      updatedAt: 'Active now',
      turnsCount: 0,
    },
    {
      id: 'clinical_synthesis',
      title: 'Clinical & Hospital Review',
      description: 'Systematic analysis of healthcare agent architectures, inpatient pathways, and clinical decision workflows.',
      updatedAt: '2 hours ago',
      sourcesCount: 1,
      turnsCount: 6,
    },
  ]);
  const [activeNotebookId, setActiveNotebookId] = useState('default');

  // Load initial health and documents
  useEffect(() => {
    loadHealth();
    loadDocuments();
  }, []);

  const loadHealth = async () => {
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (err) {
      console.error('Failed to load health:', err);
    }
  };

  const loadDocuments = async () => {
    try {
      const data = await fetchDocuments();
      const docs = data.documents || [];
      setDocuments(docs);
      // Auto-select all documents on initial load
      setSelectedDocIds(new Set(docs.map((d) => d.doc_id)));
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  // Upload multiple files concurrently
  const handleUploadMultiple = async (files) => {
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setErrorMessage(null);
    setUploadProgress({ completed: 0, total: files.length });

    try {
      const result = await uploadDocuments(files, (completed, total) => {
        setUploadProgress({ completed, total });
      });

      await loadDocuments();

      // Auto-select newly added documents
      if (result.results && result.results.length > 0) {
        const newIds = result.results.map((r) => r.doc_id);
        setSelectedDocIds((prev) => new Set([...prev, ...newIds]));
      }

      if (result.errors && result.errors.length > 0) {
        setErrorMessage(`Some files failed: ${result.errors.map((e) => e.file).join(', ')}`);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Batch upload failed');
    } finally {
      setIsUploading(false);
      setUploadProgress(null);
    }
  };

  const handleDeleteDoc = async (docId) => {
    setErrorMessage(null);
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
      setSelectedDocIds((prev) => {
        const next = new Set(prev);
        next.delete(docId);
        return next;
      });
      if (activeCitation?.doc_id === docId) {
        setActiveCitation(null);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to delete document');
    }
  };

  const handleToggleDoc = (docId) => {
    setSelectedDocIds((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.add(docId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    setSelectedDocIds(new Set(documents.map((d) => d.doc_id)));
  };

  const handleClearAll = () => {
    setSelectedDocIds(new Set());
  };

  const handleClearChat = async () => {
    setIsClearing(true);
    try {
      await clearChat(activeNotebookId);
      setMessages([]);
      setActiveCitation(null);
      setErrorMessage(null);
    } catch (err) {
      setErrorMessage('Failed to clear chat session');
    } finally {
      setIsClearing(false);
    }
  };

  const handleCitationClick = (citation, index) => {
    setActiveCitation(citation);
    setActiveCitationIndex(index || 1);
  };

  const handleSelectNotebook = (nbId) => {
    setActiveNotebookId(nbId);
    setActiveTab('chat');
  };

  const handleCreateNotebook = () => {
    const title = prompt('Enter Notebook Title:');
    if (!title || !title.trim()) return;

    const newNb = {
      id: `nb_${Date.now()}`,
      title: title.trim(),
      description: 'Newly initialized research workspace.',
      updatedAt: 'Just now',
      sourcesCount: documents.length,
      turnsCount: 0,
    };

    setNotebooks((prev) => [newNb, ...prev]);
    setActiveNotebookId(newNb.id);
    setActiveTab('chat');
  };

  const handleSubmit = () => {
    const query = inputQuery.trim();
    if (!query || isStreaming) return;

    setErrorMessage(null);
    setInputQuery('');

    // Add user message
    const userMsg = { role: 'user', content: query };
    const initialAssistantMsg = { role: 'assistant', content: '', citations: [] };

    setMessages((prev) => [...prev, userMsg, initialAssistantMsg]);
    setIsStreaming(true);

    const docIdsList = Array.from(selectedDocIds);

    streamChat({
      query,
      docIds: docIdsList,
      sessionId: activeNotebookId,
      onToken: (token) => {
        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: updated[lastIdx].content + token,
            };
          }
          return updated;
        });
      },
      onCitations: (citations) => {
        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
            updated[lastIdx] = {
              ...updated[lastIdx],
              citations: citations,
            };
          }
          return updated;
        });
      },
      onError: (err) => {
        setErrorMessage(err);
        setIsStreaming(false);
      },
      onDone: () => {
        setIsStreaming(false);
        // Update notebook turn count
        setNotebooks((prev) =>
          prev.map((nb) =>
            nb.id === activeNotebookId
              ? { ...nb, turnsCount: (nb.turnsCount || 0) + 1, updatedAt: 'Just now' }
              : nb
          )
        );
      },
    });
  };

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background text-neutral-dark font-body">
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenHelp={() => setIsHelpOpen(true)}
        onClearChat={handleClearChat}
        isClearing={isClearing}
        activeSourcesCount={selectedDocIds.size}
        totalSourcesCount={documents.length}
      />

      {/* Main Content Body */}
      {activeTab === 'notebooks' ? (
        <NotebooksView
          notebooks={notebooks}
          activeNotebookId={activeNotebookId}
          onSelectNotebook={handleSelectNotebook}
          onCreateNotebook={handleCreateNotebook}
          documentsCount={documents.length}
        />
      ) : (
        <div className="flex-1 flex overflow-hidden relative">
          {/* Left Sidebar: Sources */}
          <SourceSidebar
            documents={documents}
            selectedDocIds={selectedDocIds}
            onToggleDoc={handleToggleDoc}
            onSelectAll={handleSelectAll}
            onClearAll={handleClearAll}
            onUploadMultiple={handleUploadMultiple}
            onDeleteDoc={handleDeleteDoc}
            uploadProgress={uploadProgress}
            isUploading={isUploading}
            isCollapsed={isSidebarCollapsed}
            onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            searchQuery={searchQuery}
          />

          {/* Center Main: Grounded Chat */}
          <ChatPane
            messages={messages}
            inputQuery={inputQuery}
            setInputQuery={setInputQuery}
            onSubmit={handleSubmit}
            isStreaming={isStreaming}
            onCitationClick={handleCitationClick}
            activeSourcesCount={selectedDocIds.size}
            errorMessage={errorMessage}
          />

          {/* Right Drawer: Citation Inspector */}
          {activeCitation && (
            <CitationInspector
              citation={activeCitation}
              index={activeCitationIndex}
              onClose={() => setActiveCitation(null)}
            />
          )}
        </div>
      )}

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        health={health}
      />

      {/* Help Modal */}
      <HelpModal
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
      />
    </div>
  );
}
