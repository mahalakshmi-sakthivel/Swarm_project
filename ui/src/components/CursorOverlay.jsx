import React, { useState, useEffect } from 'react';

// Agent Role Color Palette matching Figma / Devin multiplayer aesthetics
const AGENT_ROLES = [
  { id: 'structure', name: 'Layout', color: '#3b82f6', textColor: '#ffffff', tag: '1140 x 180' },
  { id: 'style', name: 'Pixel', color: '#ec4899', textColor: '#ffffff', tag: 'Cards Grid' },
  { id: 'script', name: 'Motion', color: '#10b981', textColor: '#ffffff', tag: '622 x 18' },
  { id: 'qa', name: 'Critic', color: '#f59e0b', textColor: '#000000', tag: 'Lighthouse' },
  { id: 'integration', name: 'Index', color: '#8b5cf6', textColor: '#ffffff', tag: 'Synthesizer' },
];

export default function CursorOverlay({
  runId,
  activeEvents = [],
  tasks = [],
  hasIndexHtml = false,
  enabled = true,
}) {
  if (!enabled) return null;

  // Cursor Positions with smooth simulated animation between target sections
  const [positions, setPositions] = useState({
    structure: { x: 24, y: 18, active: true, box: { x: 12, y: 12, w: 76, h: 14 } },
    style: { x: 56, y: 46, active: true, box: { x: 28, y: 38, w: 64, h: 26 } },
    script: { x: 74, y: 72, active: true, box: { x: 42, y: 68, w: 48, h: 10 } },
    qa: { x: 82, y: 28, active: true, box: { x: 70, y: 22, w: 22, h: 16 } },
  });

  // Natural animated gliding effect
  useEffect(() => {
    const interval = setInterval(() => {
      setPositions((prev) => {
        const next = { ...prev };
        for (const role of Object.keys(next)) {
          // Slight lifelike wandering around their active workspace
          const dx = (Math.random() - 0.5) * 6;
          const dy = (Math.random() - 0.5) * 4;
          next[role] = {
            ...next[role],
            x: Math.max(8, Math.min(88, next[role].x + dx)),
            y: Math.max(8, Math.min(84, next[role].y + dy)),
          };
        }
        return next;
      });
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  // Update target when new events arrive
  useEffect(() => {
    if (activeEvents.length === 0) return;
    const latest = activeEvents[activeEvents.length - 1];
    const agent = latest.agent || latest.agent_id || '';
    const target = latest.target || '';

    let role = 'structure';
    if (agent.includes('style') || target.includes('css')) role = 'style';
    else if (agent.includes('script') || target.includes('js')) role = 'script';
    else if (agent.includes('qa')) role = 'qa';

    const targetCoords = {
      'index.html': { x: 26, y: 20, box: { x: 10, y: 14, w: 80, h: 18 } },
      'styles.css': { x: 58, y: 44, box: { x: 25, y: 35, w: 68, h: 30 } },
      'script.js': { x: 68, y: 76, box: { x: 38, y: 66, w: 54, h: 14 } },
      'vision': { x: 80, y: 30, box: { x: 65, y: 18, w: 28, h: 22 } },
    };

    const coord = targetCoords[target] || { x: 48, y: 48, box: { x: 20, y: 20, w: 60, h: 40 } };

    setPositions((prev) => ({
      ...prev,
      [role]: {
        ...prev[role],
        x: coord.x,
        y: coord.y,
        box: coord.box,
        active: true,
      },
    }));
  }, [activeEvents]);

  return (
    <div className="multiplayer-cursor-layer">
      {/* 1. Active Selection Bounding Boxes */}
      {Object.entries(positions).map(([roleKey, pos]) => {
        const roleDef = AGENT_ROLES.find((r) => r.id === roleKey) || AGENT_ROLES[0];
        if (!pos.box) return null;

        return (
          <div
            key={`box-${roleKey}`}
            className="agent-selection-box"
            style={{
              left: `${pos.box.x}%`,
              top: `${pos.box.y}%`,
              width: `${pos.box.w}%`,
              height: `${pos.box.h}%`,
              borderColor: `${roleDef.color}88`,
            }}
          >
            {/* Dimension / Component Tag Pill */}
            <div
              className="selection-dimension-pill"
              style={{
                backgroundColor: roleDef.color,
                color: roleDef.textColor,
              }}
            >
              {roleDef.tag}
            </div>
          </div>
        );
      })}

      {/* 2. Active Cursors with Solid Name Pills */}
      {Object.entries(positions).map(([roleKey, pos]) => {
        const roleDef = AGENT_ROLES.find((r) => r.id === roleKey) || AGENT_ROLES[0];

        return (
          <div
            key={`cursor-${roleKey}`}
            className="figma-cursor"
            style={{
              left: `${pos.x}%`,
              top: `${pos.y}%`,
              '--cursor-color': roleDef.color,
            }}
          >
            {/* Crisp 20px SVG Cursor Arrow with outline */}
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
              {roleDef.name}
            </div>
          </div>
        );
      })}
    </div>
  );
}
