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
  const [activePage, setActivePage] = useState('index.html');
  const iframeRef = useRef(null);
  const lastReloadRef = useRef(reloadTrigger);

  // Discover all HTML pages in sandbox
  const htmlFiles = files.filter((f) => f.endsWith('.html'));
  if (htmlFiles.length === 0 && (files.includes('index.html') || hasRenderedIframe)) {
    htmlFiles.push('index.html');
  }

  // Ensure activePage points to a valid page if available
  useEffect(() => {
    if (htmlFiles.length > 0 && !htmlFiles.includes(activePage)) {
      setActivePage(htmlFiles.includes('index.html') ? 'index.html' : htmlFiles[0]);
    }
  }, [htmlFiles, activePage]);

  const hasIndexHtml = files.includes('index.html') || htmlFiles.length > 0;
  const currentPreviewUrl = runId ? `/runs/${runId}/preview/${activePage}` : null;
  const directSiteUrl = currentPreviewUrl;

  const activeTask = tasks.find((t) => t.status === 'in_progress') || tasks.find((t) => t.status === 'open');

  useEffect(() => {
    // Reset when runId changes
    setHasRenderedIframe(false);
    setActivePage('index.html');
  }, [runId]);

  useEffect(() => {
    if (hasIndexHtml) {
      setHasRenderedIframe(true);
    }
  }, [hasIndexHtml]);

  // Handle active page switch and smooth reloads
  useEffect(() => {
    if (!runId || !iframeRef.current || (!hasIndexHtml && !hasRenderedIframe)) return;
    const targetSrc = `/runs/${runId}/preview/${activePage}?v=${Date.now()}`;
    if (iframeRef.current.src !== targetSrc) {
      iframeRef.current.src = targetSrc;
    }
  }, [activePage, runId]);

  // Smooth reload on live file edits
  useEffect(() => {
    if (!runId || (!hasIndexHtml && !hasRenderedIframe)) return;
    if (runStatus === 'converged' || runStatus === 'completed') return;

    if (reloadTrigger > lastReloadRef.current && iframeRef.current) {
      lastReloadRef.current = reloadTrigger;
      iframeRef.current.src = `/runs/${runId}/preview/${activePage}?v=${Date.now()}`;
    }
  }, [reloadTrigger, runId, hasIndexHtml, hasRenderedIframe, runStatus, activePage]);

  // Intercept in-iframe link navigation to switch active page tab seamlessly
  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const handleIframeLoad = () => {
      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
        if (!iframeDoc) return;

        const handleClick = (e) => {
          const anchor = e.target.closest('a');
          if (!anchor) return;
          const href = anchor.getAttribute('href');
          if (!href) return;

          // Ignore same-page anchors and external protocols
          if (href.startsWith('#') || href.startsWith('http://') || href.startsWith('https://') || href.startsWith('mailto:') || href.startsWith('tel:')) {
            return;
          }

          // Relative page link
          const cleanHref = href.split('#')[0].replace(/^\.\//, '');
          if (cleanHref.endsWith('.html')) {
            e.preventDefault();
            setActivePage(cleanHref);
          }
        };

        iframeDoc.addEventListener('click', handleClick);
      } catch (err) {
        // Cross-origin restriction fallback
      }
    };

    iframe.addEventListener('load', handleIframeLoad);
    return () => {
      iframe.removeEventListener('load', handleIframeLoad);
    };
  }, [runId, activePage]);

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

  const handleManualRefresh = () => {
    if (iframeRef.current && directSiteUrl) {
      iframeRef.current.src = `${directSiteUrl}?v=${Date.now()}`;
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

      {/* Preview Frame Wrapper with Browser Device Frame */}
      <div className="preview-frame-wrapper">
        <div
          className="preview-viewport-shell"
          style={{ width: getViewportWidth() }}
        >
          {/* Browser Chrome Bar */}
          <div className="browser-chrome-bar">
            <div className="browser-traffic-lights">
              <span className="traffic-dot dot-red" />
              <span className="traffic-dot dot-yellow" />
              <span className="traffic-dot dot-green" />
            </div>

            <div className="browser-nav-buttons">
              <span className="nav-arrow" title="Back">‹</span>
              <span className="nav-arrow" title="Forward">›</span>
              <span
                className="nav-refresh"
                title="Reload Sandbox"
                onClick={handleManualRefresh}
              >
                ↻
              </span>
            </div>

            <div className="browser-address-bar">
              <span className="address-lock-icon">🔒</span>
              <span className="address-url-text">
                {directSiteUrl ? `http://localhost:8000${directSiteUrl}` : 'http://localhost:8000/sandbox/staging'}
              </span>
              <span
                className={`address-badge ${
                  hasIndexHtml || hasRenderedIframe
                    ? 'badge-live'
                    : runStatus === 'running'
                    ? 'badge-building'
                    : 'badge-staging'
                }`}
              >
                {hasIndexHtml || hasRenderedIframe
                  ? 'LIVE'
                  : runStatus === 'running'
                  ? 'BUILDING'
                  : 'STAGING'}
              </span>
            </div>

            <div className="browser-viewport-indicator">
              <span className="viewport-pill">{viewport.toUpperCase()}</span>
            </div>
          </div>

          {/* Page Tabs Bar (Phase 2 Multi-Page Navigation) */}
          {runId && htmlFiles.length > 0 && (
            <div className="browser-page-tabs-bar">
              <div className="browser-page-tabs-list">
                {htmlFiles.map((pageFile) => (
                  <button
                    key={pageFile}
                    type="button"
                    className={`browser-page-tab ${activePage === pageFile ? 'active' : ''}`}
                    onClick={() => setActivePage(pageFile)}
                    title={`Switch preview to ${pageFile}`}
                  >
                    <span className="page-tab-icon">📄</span>
                    <span className="page-tab-name">{pageFile}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Browser Window Body: Live Iframe OR Dedicated Blueprint Staging Canvas */}
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
            <div className="browser-staging-canvas">
              {/* Background Architectural Wireframe Skeleton */}
              <div className="staging-wireframe-nav">
                <div className="wireframe-skeleton-element wireframe-logo" />
                <div className="staging-wireframe-links">
                  <div className="wireframe-skeleton-element wireframe-link" />
                  <div className="wireframe-skeleton-element wireframe-link" />
                  <div className="wireframe-skeleton-element wireframe-link" />
                </div>
                <div className="wireframe-skeleton-element wireframe-btn" />
              </div>

              <div className="staging-wireframe-hero">
                <div className="wireframe-skeleton-element wireframe-badge" />
                <div className="wireframe-skeleton-element wireframe-headline" />
                <div className="wireframe-skeleton-element wireframe-subheadline" />
                <div className="staging-wireframe-hero-btns">
                  <div className="wireframe-skeleton-element wireframe-cta-primary" />
                  <div className="wireframe-skeleton-element wireframe-cta-secondary" />
                </div>
              </div>

              <div className="staging-wireframe-grid">
                <div className="wireframe-skeleton-card">
                  <div className="wireframe-skeleton-element wireframe-card-icon" />
                  <div className="wireframe-skeleton-element wireframe-card-title" />
                  <div className="wireframe-skeleton-element wireframe-card-line" />
                  <div className="wireframe-skeleton-element wireframe-card-line short" />
                </div>
                <div className="wireframe-skeleton-card">
                  <div className="wireframe-skeleton-element wireframe-card-icon" />
                  <div className="wireframe-skeleton-element wireframe-card-title" />
                  <div className="wireframe-skeleton-element wireframe-card-line" />
                  <div className="wireframe-skeleton-element wireframe-card-line short" />
                </div>
                <div className="wireframe-skeleton-card">
                  <div className="wireframe-skeleton-element wireframe-card-icon" />
                  <div className="wireframe-skeleton-element wireframe-card-title" />
                  <div className="wireframe-skeleton-element wireframe-card-line" />
                  <div className="wireframe-skeleton-element wireframe-card-line short" />
                </div>
              </div>

              {/* Floating High-Contrast Staging Status Card */}
              <div className="staging-center-card">
                <div className="staging-radar-pulse">
                  <div className="radar-circle" />
                  <span className="radar-icon">⚡</span>
                </div>
                <h4>{runId ? 'Autonomous Swarm Generating Website' : 'Sandbox Canvas Ready'}</h4>
                <p className="staging-subtext">
                  {activeTask
                    ? `${activeTask.title} (${activeTask.role_hint})`
                    : runId
                    ? 'Structure & Style Specialists are drafting semantic layout, rich theme & colors...'
                    : 'Click "+ New Build" to launch decentralized swarm agents.'}
                </p>
                {runId && (
                  <div className="staging-active-tags">
                    <span className="staging-tag tag-structure">HTML5 Structure</span>
                    <span className="staging-tag tag-style">Vibrant Theme</span>
                    <span className="staging-tag tag-script">Interactive JS</span>
                    <span className="staging-tag tag-qa">QA Audit</span>
                  </div>
                )}
              </div>
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

