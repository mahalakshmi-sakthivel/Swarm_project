import React, { useState, useEffect } from 'react';
import { getRunVersions } from '../services/api';

export default function VersionHistoryModal({ runId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!runId) return;
    getRunVersions(runId)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load version history:', err);
        setLoading(false);
      });
  }, [runId]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content version-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h4>📜 Version History & Artifacts: {runId}</h4>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {loading ? (
            <p>Loading artifact audit history...</p>
          ) : !data || (data.artifacts?.length === 0 && data.history?.length === 0) ? (
            <p>No recorded artifact versions yet.</p>
          ) : (
            <div className="version-history-lists">
              <div className="version-column">
                <h5>Current Sandbox Artifacts</h5>
                <div className="artifact-cards-list">
                  {data.artifacts?.map((a) => (
                    <div key={a.id || a.path} className="artifact-version-card">
                      <div className="artifact-path">📄 {a.path}</div>
                      <div className="artifact-meta">
                        <span>v{a.version}</span>
                        <span>@{a.author_agent}</span>
                        <code title={a.content_hash}>{a.content_hash?.slice(0, 8)}</code>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="version-column">
                <h5>Modification Events</h5>
                <div className="events-timeline-list">
                  {data.history?.map((ev, i) => (
                    <div key={ev.id || i} className="history-event-card">
                      <div className="event-type-badge">{ev.event_type}</div>
                      <div className="event-details">
                        <span className="event-target">{ev.target}</span>
                        <p className="event-summary">{ev.payload?.summary || 'File modified'}</p>
                      </div>
                      <span className="event-author">@{ev.agent_id}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <a
            href={`/runs/${runId}/export/zip`}
            download
            className="btn-download-zip"
          >
            📦 Download ZIP
          </a>
          <button className="btn-close" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

