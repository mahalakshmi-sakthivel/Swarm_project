import React, { useState, useRef, useEffect } from 'react';

const EVENT_TYPE_COLORS = {
  agent_spawned: '#60a5fa',
  task_claimed: '#fbbf24',
  file_edit: '#4ade80',
  task_done: '#38bdf8',
  qa_audit: '#fb923c',
  swarm_converged: '#a855f7',
  task_seed: '#94a3b8',
};

export default function EventFeed({ events = [] }) {
  const [roleFilter, setRoleFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(true);
  const terminalRef = useRef(null);

  // Auto-scroll inside the terminal container ONLY (never hijacks main window scroll)
  useEffect(() => {
    if (!isCollapsed && autoScroll && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [events, autoScroll, isCollapsed]);

  // Filter events
  const filteredEvents = events.filter((ev) => {
    const agent = ev.agent || ev.agent_id || '';
    const eventType = ev.type || ev.event_type || '';

    // Role filter
    if (roleFilter !== 'all') {
      if (!agent.includes(roleFilter)) return false;
    }

    // Type filter
    if (typeFilter !== 'all' && eventType !== typeFilter) {
      return false;
    }

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchAgent = agent.toLowerCase().includes(q);
      const matchType = eventType.toLowerCase().includes(q);
      const matchTarget = ev.target?.toLowerCase().includes(q);
      const matchPayload = JSON.stringify(ev.payload || {}).toLowerCase().includes(q);
      if (!matchAgent && !matchType && !matchTarget && !matchPayload) {
        return false;
      }
    }

    return true;
  });

  const formatTime = (ts) => {
    if (!ts) return '';
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString();
  };

  return (
    <div className={`event-feed-container ${isCollapsed ? 'is-collapsed' : ''}`}>
      {/* Header and Controls */}
      <div className="feed-header" onClick={() => setIsCollapsed(!isCollapsed)} style={{ cursor: 'pointer' }}>
        <div className="feed-title-group">
          <h3>⚡ Live Swarm Event Log ({filteredEvents.length})</h3>
          <span className="feed-subtitle">
            {isCollapsed ? '▶ Click to expand logs' : '▼ Click to minimize logs'}
          </span>
        </div>

        <div className="feed-header-actions" onClick={(e) => e.stopPropagation()}>
          <button
            className="btn-feed-collapse"
            onClick={() => setIsCollapsed(!isCollapsed)}
            title={isCollapsed ? 'Expand Log' : 'Minimize Log'}
          >
            {isCollapsed ? 'Expand Log ▾' : 'Minimize Log ▴'}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          <div className="feed-controls">
            <input
              type="text"
              className="feed-search-input"
              placeholder="Search events..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />

            <select
              className="feed-select"
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
            >
              <option value="all">All Roles</option>
              <option value="structure">Structure</option>
              <option value="style">Style</option>
              <option value="script">Script</option>
              <option value="qa">QA</option>
              <option value="integration">Integration</option>
            </select>

            <select
              className="feed-select"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="all">All Event Types</option>
              <option value="file_edit">file_edit</option>
              <option value="task_claimed">task_claimed</option>
              <option value="task_done">task_done</option>
              <option value="qa_audit">qa_audit</option>
              <option value="agent_spawned">agent_spawned</option>
              <option value="swarm_converged">swarm_converged</option>
            </select>

            <label className="feed-autoscroll-toggle">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
          </div>

          {/* Terminal Rows */}
          <div className="feed-terminal" ref={terminalRef}>
            {filteredEvents.length === 0 ? (
              <div className="empty-terminal-hint">
                Waiting for swarm events to stream over WebSocket...
              </div>
            ) : (
              filteredEvents.map((ev, idx) => {
                const eventType = ev.type || ev.event_type || 'event';
                const agent = ev.agent || ev.agent_id || 'system';
                const timestamp = ev.timestamp || ev.ts;
                const typeColor = EVENT_TYPE_COLORS[eventType] || '#94a3b8';
                return (
                  <div key={ev.id || idx} className="terminal-row">
                    <span className="terminal-time">{formatTime(timestamp)}</span>

                    <span
                      className="terminal-type-chip"
                      style={{ color: typeColor, borderColor: `${typeColor}44`, backgroundColor: `${typeColor}15` }}
                    >
                      {eventType}
                    </span>

                    <span className="terminal-agent">{agent}</span>

                    {ev.target && (
                      <span className="terminal-target">[{ev.target}]</span>
                    )}

                    <span className="terminal-payload">
                      {eventType === 'file_edit' && ev.payload?.bytes
                        ? `wrote ${ev.payload.bytes} bytes to ${ev.target}`
                        : eventType === 'task_claimed'
                        ? `claimed task '${ev.payload?.task_id || ''}'`
                        : eventType === 'task_done'
                        ? `completed task '${ev.payload?.task_id || ''}'`
                        : eventType === 'qa_audit' || eventType === 'test_run'
                        ? `score: ${ev.payload?.score ?? ev.payload?.composite_score ?? 'N/A'}/100 (passed: ${String(ev.payload?.passed ?? ev.payload?.converged)})`
                        : JSON.stringify(ev.payload || {})}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}
    </div>
  );
}

