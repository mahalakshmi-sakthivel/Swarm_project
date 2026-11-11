import React, { useState } from 'react';
import { retryTask } from '../services/api';

const STATUS_ICONS = {
  open: '⏳',
  in_progress: '⚡',
  done: '✅',
  completed: '✅',
  failed: '❌',
};

const STATUS_LABELS = {
  open: 'Queued',
  in_progress: 'Running',
  done: 'Done',
  completed: 'Done',
  failed: 'Failed',
};

export default function AgentTimeline({ runId, tasks = [], onTaskRetried }) {
  const [selectedTask, setSelectedTask] = useState(null);
  const [retryingId, setRetryingId] = useState(null);

  const handleRetry = async (taskId, e) => {
    if (e) e.stopPropagation();
    setRetryingId(taskId);
    try {
      await retryTask(runId, taskId);
      if (onTaskRetried) onTaskRetried(taskId);
    } catch (err) {
      alert(`Failed to retry task: ${err.message}`);
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <div className="agent-timeline-container">
      <div className="timeline-header">
        <h4>⏱️ Agent Execution Timeline</h4>
        <span className="task-summary-badge">
          {tasks.filter((t) => t.status === 'done' || t.status === 'completed').length} / {tasks.length} Completed
        </span>
      </div>

      <div className="timeline-items">
        {tasks.map((t, idx) => {
          const statusKey = t.status || 'open';
          const icon = STATUS_ICONS[statusKey] || '⏳';
          const label = STATUS_LABELS[statusKey] || statusKey;
          const isSelected = selectedTask?.id === t.id;

          return (
            <div
              key={t.id}
              className={`timeline-card status-${statusKey} ${isSelected ? 'selected' : ''}`}
              onClick={() => setSelectedTask(t)}
            >
              <div className="timeline-marker">
                <span className="marker-icon">{icon}</span>
                {idx < tasks.length - 1 && <div className="timeline-connector" />}
              </div>

              <div className="timeline-content">
                <div className="task-header-row">
                  <span className="task-title">{t.title}</span>
                  <span className={`task-status-pill ${statusKey}`}>{label}</span>
                </div>

                <div className="task-meta-row">
                  <span className="task-role">@{t.role_hint || 'general'}</span>
                  {t.target && <span className="task-target">🎯 {t.target}</span>}
                  <span className="task-priority">P{t.priority}</span>
                </div>

                {t.status === 'failed' && (
                  <button
                    className="btn-retry-task"
                    disabled={retryingId === t.id}
                    onClick={(e) => handleRetry(t.id, e)}
                  >
                    {retryingId === t.id ? 'Retrying...' : '🔄 Retry this task'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Task Details Modal */}
      {selectedTask && (
        <div className="task-detail-overlay" onClick={() => setSelectedTask(null)}>
          <div className="task-detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h4>Task Details: {selectedTask.title}</h4>
              <button className="close-btn" onClick={() => setSelectedTask(null)}>✕</button>
            </div>
            <div className="modal-body">
              <p><strong>ID:</strong> {selectedTask.id}</p>
              <p><strong>Role:</strong> @{selectedTask.role_hint}</p>
              <p><strong>Status:</strong> {selectedTask.status}</p>
              <p><strong>Target File:</strong> {selectedTask.target || 'N/A'}</p>
              <div className="task-desc-box">
                <strong>Description:</strong>
                <pre>{selectedTask.description}</pre>
              </div>
              {selectedTask.depends_on && selectedTask.depends_on.length > 0 && (
                <p><strong>Depends On:</strong> {selectedTask.depends_on.join(', ')}</p>
              )}
            </div>
            <div className="modal-footer">
              <button
                className="btn-retry-task"
                disabled={retryingId === selectedTask.id}
                onClick={() => handleRetry(selectedTask.id)}
              >
                {retryingId === selectedTask.id ? 'Retrying...' : '🔄 Retry Task'}
              </button>
              <button className="btn-close" onClick={() => setSelectedTask(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

