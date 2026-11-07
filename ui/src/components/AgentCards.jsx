import React from 'react';

const SWARM_ROLES = [
  {
    role: 'structure',
    title: 'Structure Specialist',
    color: 'var(--role-structure)',
    icon: '🏗️',
    description: 'HTML5 skeleton, semantic hierarchy, metadata, asset linking.',
  },
  {
    role: 'style',
    title: 'Style Specialist',
    color: 'var(--role-style)',
    icon: '🎨',
    description: 'Modern dark CSS design tokens, responsive layout, flex/grid.',
  },
  {
    role: 'script',
    title: 'Script Specialist',
    color: 'var(--role-script)',
    icon: '⚡',
    description: 'DOM interaction, smooth scrolling, event listeners, state.',
  },
  {
    role: 'qa',
    title: 'QA Specialist',
    color: 'var(--role-qa)',
    icon: '🔍',
    description: 'Deterministic HTML5 validation, CSS linting, syntax verification.',
  },
  {
    role: 'integration',
    title: 'Integration Specialist',
    color: 'var(--role-integration)',
    icon: '🧩',
    description: 'End-to-end alignment, cross-asset verification, final polish.',
  },
];

export default function AgentCards({ agents = {}, activeTasks = [] }) {
  return (
    <div className="agent-cards-container">
      <div className="section-title-row">
        <h3>🤖 Swarm Agents ({SWARM_ROLES.length})</h3>
        <span className="section-hint">Decentralized Autonomous Workers</span>
      </div>

      <div className="agent-cards-grid">
        {SWARM_ROLES.map((roleDef) => {
          const agentData = agents[roleDef.role] || {
            status: 'idle',
            target: '',
            current_task: null,
            last_activity: 'Waiting for tasks...',
            name: `agent-${roleDef.role}-01`,
          };

          // Find if an active task belongs to this role
          const claimedTask = activeTasks.find(
            (t) => t.role_hint === roleDef.role && (t.status === 'in_progress' || t.status === 'claimed')
          );

          const isWorking = agentData.status === 'working' || !!claimedTask;
          const displayStatus = isWorking ? 'working' : agentData.status || 'idle';

          return (
            <div
              key={roleDef.role}
              className={`agent-card agent-${roleDef.role} ${isWorking ? 'is-working' : ''}`}
              style={{ '--agent-color': roleDef.color }}
            >
              <div className="agent-card-header">
                <div className="agent-identity">
                  <span className="agent-icon">{roleDef.icon}</span>
                  <div>
                    <h4 className="agent-role-title">{roleDef.title}</h4>
                    <span className="agent-name">{agentData.name}</span>
                  </div>
                </div>
                <div className={`agent-status-badge status-${displayStatus}`}>
                  {isWorking && <span className="agent-pulse"></span>}
                  {displayStatus}
                </div>
              </div>

              <div className="agent-card-footer">
                <div className="agent-target-row">
                  <span className="agent-footer-label">Target:</span>
                  <span className="agent-target-code">
                    {claimedTask?.target || agentData.target || 'None'}
                  </span>
                </div>
                {claimedTask && (
                  <div className="agent-task-row">
                    <span className="agent-footer-label">Task:</span>
                    <span className="agent-task-title" title={claimedTask.title}>
                      {claimedTask.title}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

