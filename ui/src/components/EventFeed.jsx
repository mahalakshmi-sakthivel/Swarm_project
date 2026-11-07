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
  const feedEndRef = useRef(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (autoScroll && feedEndRef.current) {
      feedEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, autoScroll]);

  // Filter events
  const filteredEvents = events.filter((ev) => {
    // Role filter
    if (roleFilter !== 'all') {
      const agentRole = ev.agent || '';
      if (!agentRole.includes(roleFilter)) return false;
    }

    // Type filter
    if (typeFilter !== 'all' && ev.type !== typeFilter) {
      return false;
    }

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchAgent = ev.agent?.toLowerCase().includes(q);
      const matchType = ev.type?.toLowerCase().includes(q);
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
    <div className="event-feed-container">
      {/* Header and Controls */}
      <div className="feed-header">
        <div className="feed-title-group">
          <h3>⚡ Live Swarm Event Log ({filteredEvents.length})</h3>
          <span className="feed-subtitle">Real-time Starlette WebSocket Stream</span>
        </div>

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
      </div>

      {/* Terminal Rows */}
      <div className="feed-terminal">
        {filteredEvents.length === 0 ? (
          <div className="empty-terminal-hint">
            Waiting for swarm events to stream over WebSocket...
          </div>
        ) : (
          filteredEvents.map((ev, idx) => {
            const typeColor = EVENT_TYPE_COLORS[ev.type] || '#94a3b8';
            return (
              <div key={ev.id || idx} className="terminal-row">
                <span className="terminal-time">{formatTime(ev.timestamp)}</span>

                <span
                  className="terminal-type-chip"
                  style={{ color: typeColor, borderColor: `${typeColor}44`, backgroundColor: `${typeColor}15` }}
                >
                  {ev.type}
                </span>

                <span className="terminal-agent">{ev.agent || 'system'}</span>

                {ev.target && (
                  <span className="terminal-target">[{ev.target}]</span>
                )}

                <span className="terminal-payload">
                  {ev.type === 'file_edit' && ev.payload?.bytes
                    ? `wrote ${ev.payload.bytes} bytes to ${ev.target}`
                    : ev.type === 'task_claimed'
                    ? `claimed task '${ev.payload?.task_id || ''}'`
                    : ev.type === 'task_done'
                    ? `completed task '${ev.payload?.task_id || ''}'`
                    : ev.type === 'qa_audit'
                    ? `score: ${ev.payload?.score ?? 'N/A'}/100 (passed: ${String(ev.payload?.passed)})`
                    : JSON.stringify(ev.payload || {})}
                </span>
              </div>
            );
          })
        )}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}

