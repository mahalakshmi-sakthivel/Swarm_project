import React, { useState, useEffect, useRef } from 'react';
import CursorOverlay from './CursorOverlay';

export default function PreviewPane({
  runId,
  files = [],
  tasks = [],
  activeEvents = [],
  reloadTrigger = 0,
  runStatus = 'idle',
}) {
  const [viewport, setViewport] = useState('desktop'); // desktop | tablet | mobile
  const [showCursors, setShowCursors] = useState(false);
  const [iframeKey, setIframeKey] = useState(Date.now());
  const iframeRef = useRef(null);

  // Trigger hot reload when reloadTrigger changes
  useEffect(() => {
    if (reloadTrigger > 0) {
      setIframeKey(Date.now());
    }
  }, [reloadTrigger]);

  const previewUrl = runId ? `/runs/${runId}/preview/index.html?v=${iframeKey}` : null;
  const hasIndexHtml = files.includes('index.html');

  const getViewportWidth = () => {
    switch (viewport) {
      case 'mobile':
        return '375px';
      case 'tablet':
        return '768px';
      default:
        return '100%';
    }
  };

  return (
    <div className="preview-pane-container">
      {/* Viewport & Controls Bar */}
      <div className="preview-toolbar">
        <div className="viewport-controls">
          <button
            className={`btn-viewport ${viewport === 'desktop' ? 'active' : ''}`}
            onClick={() => setViewport('desktop')}
            title="Desktop View (100%)"
          >
            🖥️ Desktop
          </button>
          <button
            className={`btn-viewport ${viewport === 'tablet' ? 'active' : ''}`}
            onClick={() => setViewport('tablet')}
            title="Tablet View (768px)"
          >
            📱 Tablet
          </button>
          <button
            className={`btn-viewport ${viewport === 'mobile' ? 'active' : ''}`}
            onClick={() => setViewport('mobile')}
            title="Mobile View (375px)"
          >
            📱 Mobile
          </button>
        </div>

        <div className="preview-actions">
          <button
            className={`btn-toggle-cursors ${showCursors ? 'active' : ''}`}
            onClick={() => setShowCursors(!showCursors)}
            title="Toggle Swarm Cursors"
          >
            {showCursors ? '👁️ Cursors ON' : '🙈 Cursors OFF'}
          </button>

          {previewUrl && hasIndexHtml && (
            <a
              href={`/runs/${runId}/preview/index.html`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-external"
              title="Open preview in new tab"
            >
              ↗ Open Tab
            </a>
          )}
        </div>
      </div>

      {/* Preview Frame Wrapper */}
      <div className="preview-frame-wrapper">
        <div
          className="preview-viewport-shell"
          style={{ width: getViewportWidth() }}
        >
          {runId && hasIndexHtml ? (
            <div className="iframe-container">
              <iframe
                ref={iframeRef}
                key={iframeKey}
                src={previewUrl}
                title="Live Sandbox Preview"
                className="preview-iframe"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"
              />
            </div>
          ) : (
            <div className="preview-placeholder">
              <div className="placeholder-icon">🌐</div>
              <h4>Sandbox Preview Staging</h4>
              <p>
                {!runId
                  ? 'Select or start a build to observe the decentralized swarm in action.'
                  : 'Agents are formulating structure and writing files. Preview will render automatically upon artifact completion.'}
              </p>
            </div>
          )}

          <CursorOverlay
            runId={runId}
            tasks={tasks}
            hasIndexHtml={hasIndexHtml}
            activeEvents={activeEvents}
            enabled={showCursors}
            runStatus={runStatus}
          />
        </div>
      </div>
    </div>
  );
}

