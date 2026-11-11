import React from 'react';

export default function Header({
  runs,
  currentRunId,
  onSelectRun,
  onNewRunClick,
  runStatus,
  qaScore,
  qaPassed,
  isConnected,
  onRefreshPreview
}) {
  const getStatusBadge = () => {
    if (!currentRunId) {
      return <span className="status-badge idle">Ready</span>;
    }
    if (runStatus === 'running') {
      return (
        <span className="status-badge running">
          <span className="pulse-dot"></span> Running
        </span>
      );
    }
    if (runStatus === 'converged') {
      return <span className="status-badge converged">✓ Converged</span>;
    }
    if (runStatus === 'failed') {
      return <span className="status-badge failed">✕ Failed</span>;
    }
    return <span className="status-badge">{runStatus || 'Active'}</span>;
  };

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="brand">
          <div className="brand-icon">⚡</div>
          <div className="brand-text">
            <h1>Swarm Website Builder</h1>
            <span className="brand-subtitle">Decentralized Multi-Agent Framework</span>
          </div>
        </div>

        <div className="run-selector-group">
          <label htmlFor="run-select">Run:</label>
          <select
            id="run-select"
            value={currentRunId || ''}
            onChange={(e) => onSelectRun(e.target.value)}
            className="run-select"
          >
            {runs.length === 0 && <option value="">No runs available</option>}
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id} {r.status ? `(${r.status})` : ''} - {r.goal_prompt ? r.goal_prompt.slice(0, 32) + '...' : ''}
              </option>
            ))}
          </select>
          <button className="btn-secondary btn-sm" onClick={onNewRunClick}>
            + New Build
          </button>
        </div>
      </div>

      <div className="header-right">
        {currentRunId && (
          <>
            <div className="header-metric">
              <span className="metric-label">Status:</span>
              {getStatusBadge()}
            </div>

            {qaScore !== null && (
              <div className="header-metric">
                <span className="metric-label">QA Score:</span>
                <span className={`qa-badge ${qaPassed ? 'qa-pass' : 'qa-fail'}`}>
                  {qaScore.toFixed(0)}/100 {qaPassed ? 'PASSED' : 'AUDIT'}
                </span>
              </div>
            )}

            <div className="header-metric">
              <span className="metric-label">Stream:</span>
              <span className={`ws-badge ${isConnected ? 'ws-connected' : 'ws-disconnected'}`}>
                {isConnected ? '● Live WS' : '○ Polling'}
              </span>
            </div>

            <button
              className="btn-icon"
              title="Refresh Preview"
              onClick={onRefreshPreview}
            >
              🔄
            </button>

            <a
              href={`/runs/${currentRunId}/export/zip`}
              download
              className="btn-download-zip"
              title="Download Full Website as ZIP Archive"
            >
              📦 Download ZIP
            </a>
          </>
        )}
      </div>
    </header>
  );
}

