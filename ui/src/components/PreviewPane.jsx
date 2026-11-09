import React, { useState, useEffect, useRef } from 'react';
import CursorOverlay from './CursorOverlay';

export default function PreviewPane({
  runId,
  files = [],
  tasks = [],
  activeEvents = [],
  reloadTrigger = 0,
  runStatus = 'idle',
  isFocusMode = false,
  onToggleFocusMode = () => {},
}) {
  const [viewport, setViewport] = useState('desktop'); // desktop | tablet | mobile
  const [showCursors, setShowCursors] = useState(false);
  const [hasRenderedIframe, setHasRenderedIframe] = useState(false);
  const iframeRef = useRef(null);
  const lastReloadRef = useRef(reloadTrigger);

  const hasIndexHtml = files.includes('index.html');
  const directSiteUrl = runId ? `/runs/${runId}/preview/index.html` : null;

  useEffect(() => {
    // Reset when runId changes
    setHasRenderedIframe(false);
  }, [runId]);

  useEffect(() => {
    if (hasIndexHtml) {
      setHasRenderedIframe(true);
    }
  }, [hasIndexHtml]);

  // Smooth reload without tearing down or remounting the iframe element
  useEffect(() => {
    if (!runId || (!hasIndexHtml && !hasRenderedIframe)) return;
    if (runStatus === 'converged' || runStatus === 'completed') return;

    if (reloadTrigger > lastReloadRef.current && iframeRef.current) {
      lastReloadRef.current = reloadTrigger;
      iframeRef.current.src = `/runs/${runId}/preview/index.html?v=${Date.now()}`;
    }
  }, [reloadTrigger, runId, hasIndexHtml, hasRenderedIframe, runStatus]);

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
    <div className={`preview-pane-container ${isFocusMode ? 'focus-mode-active' : ''}`}>
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
          {/* Focus Mode: Hide all sidebars and logs to focus solely on the website */}
          <button
            className={`btn-focus-mode ${isFocusMode ? 'active' : ''}`}
            onClick={() => onToggleFocusMode(!isFocusMode)}
            title={isFocusMode ? 'Show Swarm Panels' : 'Full Screen Website View'}
          >
            {isFocusMode ? '🗂️ Split View' : '🔍 Full Website View'}
          </button>

          <button
            className={`btn-toggle-cursors ${showCursors ? 'active' : ''}`}
            onClick={() => setShowCursors(!showCursors)}
            title="Toggle Swarm Cursors"
          >
            {showCursors ? '👁️ Cursors ON' : '🙈 Cursors OFF'}
          </button>

          {directSiteUrl && (hasIndexHtml || hasRenderedIframe) && (
            <a
              href={directSiteUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-external highlight"
              title="Open the pure generated website in a new tab without any dashboard UI"
            >
              🌐 Open Full Page ↗
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
          {runId && (hasIndexHtml || hasRenderedIframe) ? (
            <div className="iframe-container">
              <iframe
                ref={iframeRef}
                key={runId || 'preview-frame'}
                src={directSiteUrl ? `${directSiteUrl}?v=${runId}` : ''}
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

