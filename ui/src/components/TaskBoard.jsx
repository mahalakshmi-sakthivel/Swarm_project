import React from 'react';

const ROLE_COLORS = {
  structure: 'var(--role-structure)',
  style: 'var(--role-style)',
  script: 'var(--role-script)',
  qa: 'var(--role-qa)',
  integration: 'var(--role-integration)',
};

export default function TaskBoard({ tasks = [] }) {
  const openTasks = tasks.filter((t) => t.status === 'open');
  const inProgressTasks = tasks.filter((t) => t.status === 'in_progress' || t.status === 'claimed');
  const doneTasks = tasks.filter((t) => t.status === 'done');

  const renderCard = (task) => {
    const roleColor = ROLE_COLORS[task.role_hint] || 'var(--accent-primary)';

    return (
      <div key={task.id} className="task-card">
        <div className="task-card-header">
          <span
            className="task-role-badge"
            style={{ backgroundColor: `${roleColor}22`, color: roleColor, borderColor: `${roleColor}55` }}
          >
            {task.role_hint || 'general'}
          </span>
          {task.priority && (
            <span className="task-priority">P{task.priority}</span>
          )}
        </div>

        <h5 className="task-title">{task.title}</h5>
        {task.description && (
          <p className="task-desc">{task.description}</p>
        )}

        <div className="task-card-footer">
          <span className="task-target">
            📄 {task.target || 'sandbox'}
          </span>
          {task.owner && (
            <span className="task-owner" title={`Owner: ${task.owner}`}>
              👤 {task.owner}
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="task-board-container">
      <div className="section-title-row">
        <h3>📋 Blackboard Tasks ({tasks.length})</h3>
        <span className="section-hint">Shared SQLite Memory State</span>
      </div>

      <div className="task-columns-grid">
        {/* Open Column */}
        <div className="task-column">
          <div className="column-header">
            <span className="column-dot open-dot"></span>
            <span className="column-title">Open</span>
            <span className="column-count">{openTasks.length}</span>
          </div>
          <div className="column-cards-list">
            {openTasks.length === 0 ? (
              <div className="empty-column-hint">No open tasks</div>
            ) : (
              openTasks.map(renderCard)
            )}
          </div>
        </div>

        {/* In Progress Column */}
        <div className="task-column">
          <div className="column-header">
            <span className="column-dot progress-dot"></span>
            <span className="column-title">In Progress</span>
            <span className="column-count">{inProgressTasks.length}</span>
          </div>
          <div className="column-cards-list">
            {inProgressTasks.length === 0 ? (
              <div className="empty-column-hint">No tasks in progress</div>
            ) : (
              inProgressTasks.map(renderCard)
            )}
          </div>
        </div>

        {/* Done Column */}
        <div className="task-column">
          <div className="column-header">
            <span className="column-dot done-dot"></span>
            <span className="column-title">Completed</span>
            <span className="column-count">{doneTasks.length}</span>
          </div>
          <div className="column-cards-list">
            {doneTasks.length === 0 ? (
              <div className="empty-column-hint">No completed tasks</div>
            ) : (
              doneTasks.map(renderCard)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
