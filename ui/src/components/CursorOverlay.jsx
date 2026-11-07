import React, { useState, useEffect } from 'react';

// Agent Role Color Palette
const AGENT_ROLES = [
  { id: 'structure', name: 'Layout (Structure)', color: '#3b82f6', textColor: '#ffffff' },
  { id: 'style', name: 'Style Specialist', color: '#ec4899', textColor: '#ffffff' },
  { id: 'script', name: 'Script Specialist', color: '#10b981', textColor: '#ffffff' },
  { id: 'qa', name: 'QA Auditor', color: '#f59e0b', textColor: '#000000' },
  { id: 'integration', name: 'Integration', color: '#8b5cf6', textColor: '#ffffff' },
];

export default function CursorOverlay({
  runId,
  activeEvents = [],
  tasks = [],
  hasIndexHtml = false,
  enabled = false,
  runStatus = 'idle',
}) {
  // Cursors ONLY show when a run is actively running and cursors are enabled.
  // Once the build is completed, converged, or failed, all cursors disappear immediately.
  if (!enabled || runStatus === 'completed' || runStatus === 'converged' || runStatus === 'failed') {
    return null;
  }

  // Active agents derived strictly from recent events (last 10 seconds)
  const [activeAgents, setActiveAgents] = useState({});

  useEffect(() => {
    if (!activeEvents || activeEvents.length === 0) {
      setActiveAgents({});
      return;
    }

    const recent = activeEvents.slice(-15);
    const agentsMap = {};

    for (const ev of recent) {
      const agentId = ev.agent || ev.agent_id || '';
      const target = ev.target || '';
      const eventType = ev.type || ev.event_type || '';

      if (!agentId) continue;

      let role = 'structure';
      if (agentId.includes('style') || target.includes('css')) role = 'style';
      else if (agentId.includes('script') || target.includes('js')) role = 'script';
      else if (agentId.includes('qa')) role = 'qa';
      else if (agentId.includes('integration')) role = 'integration';

      // Map targets to reasonable viewport regions
      let pos = { x: 25, y: 25 };
      if (role === 'structure') pos = { x: 30, y: 20 };
      if (role === 'style') pos = { x: 50, y: 45 };
      if (role === 'script') pos = { x: 65, y: 70 };
      if (role === 'qa') pos = { x: 75, y: 30 };
      if (role === 'integration') pos = { x: 45, y: 55 };

      agentsMap[role] = {
        role,
        agentId,
        target,
        eventType,
        ...pos,
      };
    }

    setActiveAgents(agentsMap);
  }, [activeEvents]);

  if (Object.keys(activeAgents).length === 0) return null;

  return (
    <div className="multiplayer-cursor-layer" style={{ pointerEvents: 'none' }}>
      {Object.values(activeAgents).map((agentInfo) => {
        const roleDef = AGENT_ROLES.find((r) => r.id === agentInfo.role) || AGENT_ROLES[0];

        return (
          <div
            key={`cursor-${agentInfo.role}`}
            className="figma-cursor"
            style={{
              left: `${agentInfo.x}%`,
              top: `${agentInfo.y}%`,
              '--cursor-color': roleDef.color,
            }}
          >
            {/* Crisp 20px SVG Cursor Arrow */}
            <svg
              className="figma-pointer-icon"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill={roleDef.color}
              stroke="#ffffff"
              strokeWidth="2"
              strokeLinejoin="round"
            >
              <path d="M3 3l7 18 3-7 7-3L3 3z" />
            </svg>

            {/* Solid Pill Name Badge */}
            <div
              className="figma-cursor-pill"
              style={{
                backgroundColor: roleDef.color,
                color: roleDef.textColor,
              }}
            >
              {roleDef.name} {agentInfo.target ? `[${agentInfo.target}]` : ''}
            </div>
          </div>
        );
      })}
    </div>
  );
}
