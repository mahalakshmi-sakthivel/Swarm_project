import React from 'react';

const ROLE_COLORS = {
  structure: '#60a5fa',
  style: '#e879f9',
  script: '#4ade80',
  qa: '#fb923c',
  integration: '#22d3ee',
};

// Target file to approximate viewport coordinates
const FILE_COORDINATES = {
  'index.html': { x: 28, y: 22 },
  'styles.css': { x: 62, y: 38 },
  'script.js': { x: 45, y: 65 },
  'sandbox': { x: 50, y: 50 },
};

export default function CursorOverlay({ activeEvents = [], enabled = true }) {
  if (!enabled) return null;

  // Extract recent active agent actions
  const recentAgents = {};
  for (let i = activeEvents.length - 1; i >= 0; i--) {
    const ev = activeEvents[i];
    const agent = ev.agent;
    if (agent && !recentAgents[agent]) {
      // Determine role from agent name (e.g., agent-structure-01 -> structure)
      const roleMatch = agent.match(/agent-([a-z]+)-/);
      const role = roleMatch ? roleMatch[1] : 'general';
      const target = ev.target || 'sandbox';

      // Default or target-based coordinate
      const baseCoord = FILE_COORDINATES[target] || { x: 50, y: 50 };
      // Small deterministic jitter based on agent name
      const charCode = agent.charCodeAt(agent.length - 1) || 0;
      const jitterX = (charCode % 11) - 5;
      const jitterY = ((charCode * 3) % 11) - 5;

      recentAgents[agent] = {
        agent,
        role,
        color: ROLE_COLORS[role] || '#60a5fa',
        type: ev.type,
        target,
        x: Math.max(10, Math.min(90, baseCoord.x + jitterX)),
        y: Math.max(10, Math.min(90, baseCoord.y + jitterY)),
      };
    }
    if (Object.keys(recentAgents).length >= 5) break;
  }

  const cursors = Object.values(recentAgents);

  return (
    <div className="cursor-overlay-layer">
      {cursors.map((c) => (
        <div
          key={c.agent}
          className="swarm-cursor"
          style={{
            left: `${c.x}%`,
            top: `${c.y}%`,
            '--cursor-color': c.color,
          }}
        >
          {/* SVG Arrow Pointer */}
          <svg
            className="cursor-pointer"
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill={c.color}
            stroke="#ffffff"
            strokeWidth="1.5"
            strokeLinejoin="round"
          >
            <path d="M3 3l7 18 3-7 7-3L3 3z" />
          </svg>

          {/* Cursor Label Pill */}
          <div className="cursor-label">
            <span className="cursor-agent-name">{c.agent}</span>
            <span className="cursor-activity">
              {c.type === 'file_edit'
                ? `editing ${c.target}`
                : c.type === 'task_claimed'
                ? `working on ${c.target}`
                : c.type === 'qa_audit'
                ? 'auditing quality'
                : c.type}
            </span>
          </div>

          <div className="cursor-pulse"></div>
        </div>
      ))}
    </div>
  );
}
