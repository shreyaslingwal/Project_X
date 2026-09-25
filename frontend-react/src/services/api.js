/**
 * API service client for Project X FastAPI backend.
 * Provides REST endpoints and SSE stream parsing for real-time grounded generation.
 */

const API_BASE = '/api';

/**
 * Fetch backend health and active model names.
 */
export async function fetchHealth() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch all indexed documents with page and chunk metadata.
 */
export async function fetchDocuments() {
  const response = await fetch(`${API_BASE}/documents`);
  if (!response.ok) {
    throw new Error(`Failed to list documents: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Upload a single PDF or Markdown document for ingestion and chunk indexing.
 * @param {File} file
 */
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed for ${file.name}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Upload multiple PDF or Markdown documents simultaneously.
 * @param {File[]} files
 * @param {function(number, number): void} [onProgress] - (completedCount, totalCount)
 */
export async function uploadDocuments(files, onProgress = () => {}) {
  const results = [];
  const errors = [];
  let completed = 0;

  // Execute concurrent uploads
  const uploadPromises = Array.from(files).map(async (file) => {
    try {
      const res = await uploadDocument(file);
      completed += 1;
      onProgress(completed, files.length);
      results.push(res);
      return res;
    } catch (err) {
      completed += 1;
      onProgress(completed, files.length);
      errors.push({ file: file.name, error: err.message });
      throw err;
    }
  });

  const settled = await Promise.allSettled(uploadPromises);
  return {
    results,
    errors,
    successCount: settled.filter((s) => s.status === 'fulfilled').length,
    failureCount: settled.filter((s) => s.status === 'rejected').length,
  };
}

/**
 * Delete a document from the vector store and disk.
 * @param {string} docId
 */
export async function deleteDocument(docId) {
  const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(docId)}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Delete failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Stream a chat question via Server-Sent Events (SSE).
 *
 * @param {Object} params
 * @param {string} params.query - User question text
 * @param {string[]} [params.docIds] - Optional active doc_id filters
 * @param {string} [params.sessionId="default"] - Session ID
 * @param {function(string): void} params.onToken - Called for each emitted token
 * @param {function(Array): void} params.onCitations - Called when citations are emitted
 * @param {function(string): void} params.onError - Called on error
 * @param {function(): void} params.onDone - Called when streaming completes
 * @returns {AbortController} - Controller to cancel the stream
 */
export function streamChat({
  query,
  docIds = null,
  sessionId = 'default',
  onToken = () => {},
  onCitations = () => {},
  onError = () => {},
  onDone = () => {},
}) {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          query,
          session_id: sessionId,
          doc_ids: docIds && docIds.length > 0 ? docIds : null,
          stream: true,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Chat request failed: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last incomplete fragment in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;

          const dataStr = trimmed.replace(/^data:\s*/, '');
          try {
            const event = JSON.parse(dataStr);
            if (event.type === 'token') {
              onToken(event.content);
            } else if (event.type === 'citations') {
              onCitations(event.citations || []);
            } else if (event.type === 'error') {
              onError(event.content);
            } else if (event.type === 'done') {
              onDone();
            }
          } catch (jsonErr) {
            console.warn('Failed to parse SSE payload:', dataStr, jsonErr);
          }
        }
      }

      onDone();
    } catch (err) {
      if (err.name !== 'AbortError') {
        onError(err.message || 'Stream connection failed');
      }
    }
  })();

  return controller;
}

/**
 * Clear the conversation history for a session.
 * @param {string} [sessionId="default"]
 */
export async function clearChat(sessionId = 'default') {
  const response = await fetch(`${API_BASE}/chat/clear`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error(`Failed to clear chat: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Stream a document summary via Server-Sent Events (SSE).
 *
 * @param {Object} params
 * @param {string[]|null} [params.docIds=null] - Document IDs to summarize (null = all)
 * @param {string} [params.artifactType='briefing'] - Artifact type to generate (briefing, study_guide, faq, timeline)
 * @param {function(string): void} params.onToken - Called for each emitted token
 * @param {function(string): void} params.onError - Called on error
 * @param {function(): void} params.onDone - Called when streaming completes
 * @returns {AbortController} - Controller to cancel the stream
 */
export function streamSummary({
  docIds = null,
  artifactType = 'briefing',
  onToken = () => {},
  onError = () => {},
  onDone = () => {},
}) {
  const controller = new AbortController();
  const safeArtifactType = typeof artifactType === 'string' ? artifactType : 'briefing';

  (async () => {
    try {
      const response = await fetch(`${API_BASE}/studio/summary`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          doc_ids: docIds && docIds.length > 0 ? docIds : null,
          artifact_type: safeArtifactType,
          stream: true,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Summary request failed: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;

          const dataStr = trimmed.replace(/^data:\s*/, '');
          try {
            const event = JSON.parse(dataStr);
            if (event.type === 'token') {
              onToken(event.content);
            } else if (event.type === 'error') {
              onError(event.content);
            } else if (event.type === 'done') {
              onDone();
            }
          } catch (jsonErr) {
            console.warn('Failed to parse summary SSE payload:', dataStr, jsonErr);
          }
        }
      }

      onDone();
    } catch (err) {
      if (err.name !== 'AbortError') {
        onError(err.message || 'Summary stream connection failed');
      }
    }
  })();

  return controller;
}
