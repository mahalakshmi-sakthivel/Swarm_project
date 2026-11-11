import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import PromptBar from './components/PromptBar';
import AgentCards from './components/AgentCards';
import TaskBoard from './components/TaskBoard';
import PreviewPane from './components/PreviewPane';
import EventFeed from './components/EventFeed';
import PlanReviewCard from './components/PlanReviewCard';
import RequirementsChecklist from './components/RequirementsChecklist';
import AgentTimeline from './components/AgentTimeline';
import QAScorecard from './components/QAScorecard';
import QuickEditBar from './components/QuickEditBar';
import TemplateGallery from './components/TemplateGallery';
import VersionHistoryModal from './components/VersionHistoryModal';
import {
  listRuns,
  getRunDetails,
  getRunEvents,
  createRun,
  subscribeToRun,
} from './services/api';
import './App.css';

export default function App() {
  const [runs, setRuns] = useState([]);
  const [currentRunId, setCurrentRunId] = useState(null);
  const [runDetails, setRunDetails] = useState(null);
  const [events, setEvents] = useState([]);
  const [agents, setAgents] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [showVersionModal, setShowVersionModal] = useState(false);
  const [reloadTrigger, setReloadTrigger] = useState(0);
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [activeTab, setActiveTab] = useState('preview'); // preview | plan | qa | requirements | timeline | templates
  const [customPrompt, setCustomPrompt] = useState('');
  const [isPromptExpanded, setIsPromptExpanded] = useState(true);

  const wsSubRef = useRef(null);

  // 1. Initial Load: Fetch runs list
  const refreshRunsList = useCallback(async (selectNewest = false) => {
    try {
      const data = await listRuns();
      const runList = data.runs || [];
      setRuns(runList);

      if (runList.length > 0) {
        if (selectNewest || !currentRunId) {
          setCurrentRunId(runList[0].run_id);
        }
      }
    } catch (err) {
      console.error('Error fetching runs list:', err);
    }
  }, [currentRunId]);

  useEffect(() => {
    refreshRunsList(true);
  }, [refreshRunsList]);

  // 2. Fetch Run Details
  const fetchDetails = useCallback(async (runId) => {
    if (!runId) return;
    try {
      const details = await getRunDetails(runId);
      setRunDetails(details);

      // Load initial events
      const evData = await getRunEvents(runId, 0);
      setEvents(evData.events || []);

      // Derive active agent status from tasks & events
      if (details.tasks) {
        const newAgents = {};
        for (const t of details.tasks) {
          if (t.role_hint) {
            newAgents[t.role_hint] = {
              name: t.owner || `agent-${t.role_hint}-01`,
              role: t.role_hint,
              status: t.status === 'in_progress' ? 'working' : t.status === 'done' ? 'done' : 'idle',
              target: t.target || '',
              last_activity: `${t.status}: ${t.title}`,
            };
          }
        }
        setAgents((prev) => ({ ...prev, ...newAgents }));
      }
    } catch (err) {
      console.error(`Failed to load details for ${runId}:`, err);
    }
  }, []);

  // 3. Periodic Polling Fallback (only while run is actively building)
  useEffect(() => {
    if (!currentRunId) return;
    if (runDetails?.status === 'converged' || runDetails?.status === 'completed' || runDetails?.status === 'failed') {
      return;
    }
    const interval = setInterval(() => {
      fetchDetails(currentRunId);
    }, 3000);
    return () => clearInterval(interval);
  }, [currentRunId, fetchDetails, runDetails?.status]);

  // 4. Connect WebSocket for Real-time Streaming
  useEffect(() => {
    if (!currentRunId) return;

    fetchDetails(currentRunId);

    if (wsSubRef.current) {
      wsSubRef.current.close();
      wsSubRef.current = null;
    }

    const sub = subscribeToRun(
      currentRunId,
      (data) => {
        if (data.type === 'history_event' && data.data) {
          const ev = data.data;
          setEvents((prev) => {
            if (prev.some((e) => e.id === ev.id)) return prev;
            return [...prev, ev];
          });

          const agent = ev.agent || ev.agent_id;
          const eventType = ev.type || ev.event_type;
          if (agent) {
            const roleMatch = agent.match(/agent-([a-z]+)-/);
            const role = roleMatch ? roleMatch[1] : 'general';
            setAgents((prev) => ({
              ...prev,
              [role]: {
                name: agent,
                role,
                status: eventType === 'task_done' ? 'done' : 'working',
                target: ev.target || prev[role]?.target || '',
                last_activity: `${eventType} on ${ev.target || 'sandbox'}`,
              },
            }));
          }
        } else if (data.type === 'event' && data.data) {
          const ev = data.data;
          setEvents((prev) => {
            if (prev.some((e) => e.id === ev.id)) return prev;
            return [...prev, ev];
          });

          const agent = ev.agent || ev.agent_id;
          const eventType = ev.type || ev.event_type;

          if (agent) {
            const roleMatch = agent.match(/agent-([a-z]+)-/);
            const role = roleMatch ? roleMatch[1] : 'general';

            setAgents((prev) => ({
              ...prev,
              [role]: {
                name: agent,
                role,
                status: eventType === 'task_done' ? 'done' : 'working',
                target: ev.target || prev[role]?.target || '',
                last_activity: `${eventType} on ${ev.target || 'sandbox'}`,
              },
            }));
          }

          if (eventType === 'file_edit' && runDetails?.status !== 'converged') {
            if (window._reloadTimer) clearTimeout(window._reloadTimer);
            window._reloadTimer = setTimeout(() => {
              setReloadTrigger((v) => v + 1);
              fetchDetails(currentRunId);
            }, 300);
          }
        } else if (data.type === 'state_snapshot' && data.data) {
          setRunDetails((prev) => ({
            ...prev,
            ...data.data,
            files: (data.data.files && data.data.files.length > 0) ? data.data.files : (prev?.files || []),
            qa: data.data.qa || prev?.qa || null,
          }));
        }
      },
      (err) => {
        console.warn('WebSocket stream notice:', err);
        setIsConnected(false);
      },
      () => {
        setIsConnected(true);
      },
      () => {
        setIsConnected(false);
      }
    );

    wsSubRef.current = sub;

    return () => {
      if (wsSubRef.current) {
        wsSubRef.current.close();
        wsSubRef.current = null;
      }
    };
  }, [currentRunId, fetchDetails]);

  // Launch New Run Handler
  const handleLaunchRun = async (prompt, model) => {
    setIsLaunching(true);
    try {
      const newRun = await createRun(prompt, model);
      setShowPromptModal(false);
      await refreshRunsList(false);
      setCurrentRunId(newRun.run_id);
      setActiveTab('preview');
    } catch (err) {
      alert(`Error launching swarm run: ${err.message}`);
    } finally {
      setIsLaunching(false);
    }
  };

  const handleRefreshPreview = () => {
    setReloadTrigger((v) => v + 1);
    if (currentRunId) {
      fetchDetails(currentRunId);
    }
  };

  const qaData = runDetails?.qa;
  const qaScore = qaData ? qaData.score : null;
  const qaPassed = qaData ? qaData.passed : false;
  const files = runDetails?.files || [];
  const tasks = runDetails?.tasks || [];
  const spec = runDetails?.spec || null;
  const requirements = spec?.requirements || [];

  // Calculate Build Progress & Stage Status
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((t) => t.status === 'done' || t.status === 'completed').length;
  const inProgressTask = tasks.find((t) => t.status === 'in_progress' || t.status === 'claimed');
  const isFinished = runDetails?.status === 'converged' || runDetails?.status === 'completed';
  const progressPercent = isFinished
    ? 100
    : totalTasks > 0
    ? Math.min(95, Math.round((completedTasks / totalTasks) * 100))
    : runDetails?.status === 'running'
    ? 15
    : 0;

  return (
    <div className="swarm-app">
      {/* Top Header */}
      <Header
        runs={runs}
        currentRunId={currentRunId}
        onSelectRun={(id) => setCurrentRunId(id)}
        onNewRunClick={() => {
          setIsPromptExpanded(true);
          setTimeout(() => {
            const el = document.getElementById('goal-prompt');
            if (el) {
              el.focus();
              el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
              setShowPromptModal(true);
            }
          }, 80);
        }}
        runStatus={runDetails?.status}
        qaScore={qaScore}
        qaPassed={qaPassed}
        isConnected={isConnected}
        onRefreshPreview={handleRefreshPreview}
      />

      {/* Main App Workspace */}
      <main className="swarm-workspace">
        {/* Always-Accessible Custom Prompt Builder Bar */}
        <section className="top-prompt-creator-section">
          {isPromptExpanded ? (
            <div className="prompt-wrapper">
              <div className="prompt-toggle-bar">
                <span className="prompt-section-label">✨ Create New Website</span>
                {currentRunId && (
                  <button
                    type="button"
                    className="btn-toggle-prompt"
                    onClick={() => setIsPromptExpanded(false)}
                    title="Minimize prompt box to view preview"
                  >
                    ▲ Collapse
                  </button>
                )}
              </div>
              <PromptBar
                onLaunchRun={handleLaunchRun}
                isLaunching={isLaunching}
                initialPrompt={customPrompt}
                isModal={false}
              />
            </div>
          ) : (
            <div className="prompt-collapsed-bar" onClick={() => setIsPromptExpanded(true)}>
              <span className="collapsed-text">🚀 <strong>Start New Website Build:</strong> Type a prompt to generate a new website...</span>
              <button type="button" className="btn-expand-prompt">
                ▼ Open Prompt Box
              </button>
            </div>
          )}
        </section>

        {/* Real-Time Build Progress & Completion Status */}
        {currentRunId && (
          <div className="build-progress-bar-container">
            <div className="progress-meta">
              <div className="progress-phase-info">
                {isFinished ? (
                  <span className="phase-text success">
                    ✅ <strong>Build Complete:</strong> All tasks passed QA verification (100%)
                  </span>
                ) : runDetails?.status === 'running' ? (
                  <span className="phase-text running">
                    <span className="pulse-dot"></span> <strong>Building:</strong>{' '}
                    {inProgressTask
                      ? `${inProgressTask.title} (${inProgressTask.target || inProgressTask.role_hint})`
                      : 'Swarm agents coordinating next file...'}
                  </span>
                ) : (
                  <span className="phase-text idle">
                    ⏸️ Status: {runDetails?.status || 'Idle'}
                  </span>
                )}
              </div>
              <div className="progress-timing-info">
                <span className="task-count">
                  Tasks: {completedTasks} of {Math.max(totalTasks, 4)} completed ({progressPercent}%)
                </span>
                {runDetails?.status === 'running' && (
                  <span className="timing-estimate">
                    ⏱️ Est. build time: 1.5 - 2.5 min (~30s / task)
                  </span>
                )}
                <button
                  className="btn-version-history"
                  onClick={() => setShowVersionModal(true)}
                >
                  📜 Versions
                </button>
              </div>
            </div>
            <div className="progress-track">
              <div
                className={`progress-fill ${isFinished ? 'complete' : ''}`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}

        {/* Phase 7 Dashboard Workspace Tabs */}
        {currentRunId && (
          <nav className="dashboard-tab-bar" aria-label="Dashboard views">
            <button
              className={`dashboard-tab ${activeTab === 'preview' ? 'active' : ''}`}
              onClick={() => setActiveTab('preview')}
            >
              🌐 Live Preview
            </button>
            <button
              className={`dashboard-tab ${activeTab === 'plan' ? 'active' : ''}`}
              onClick={() => setActiveTab('plan')}
            >
              📋 Plan Review & Theme
            </button>
            <button
              className={`dashboard-tab ${activeTab === 'qa' ? 'active' : ''}`}
              onClick={() => setActiveTab('qa')}
            >
              🛡️ QA Scorecard {qaScore !== null ? `(${qaScore.toFixed(0)}/100)` : ''}
            </button>
            <button
              className={`dashboard-tab ${activeTab === 'requirements' ? 'active' : ''}`}
              onClick={() => setActiveTab('requirements')}
            >
              ✅ Requirements ({requirements.length})
            </button>
            <button
              className={`dashboard-tab ${activeTab === 'timeline' ? 'active' : ''}`}
              onClick={() => setActiveTab('timeline')}
            >
              ⏱️ Agent Timeline ({tasks.length})
            </button>
            <button
              className={`dashboard-tab ${activeTab === 'templates' ? 'active' : ''}`}
              onClick={() => setActiveTab('templates')}
            >
              🎨 Template Gallery
            </button>
          </nav>
        )}

        {/* Tab 1: Live Preview & Quick Edit */}
        {activeTab === 'preview' && currentRunId && (
          <div className={`workspace-grid ${isFocusMode ? 'focus-mode-grid' : ''}`}>
            {/* Left Column: Live Preview & Quick Edit */}
            <section className="preview-section">
              <div className="section-title-bar">
                <h3>🌐 Live Sandbox Preview</h3>
                <span className="section-badge">Hot-Reload Active</span>
              </div>
              <PreviewPane
                runId={currentRunId}
                files={files}
                tasks={tasks}
                activeEvents={events}
                reloadTrigger={reloadTrigger}
                runStatus={runDetails?.status}
                isFocusMode={isFocusMode}
                onToggleFocusMode={setIsFocusMode}
              />
              {/* Quick Edit Bar */}
              <QuickEditBar
                runId={currentRunId}
                onEditSubmitted={() => {
                  fetchDetails(currentRunId);
                  setReloadTrigger((v) => v + 1);
                }}
              />
            </section>

            {/* Right Column: Agents & Blackboard Tasks (Hidden in Focus Mode) */}
            {!isFocusMode && (
              <section className="sidebar-section">
                <AgentCards agents={agents} activeTasks={tasks} />
                <TaskBoard tasks={tasks} />
              </section>
            )}
          </div>
        )}

        {/* Tab 2: Plan Review Card */}
        {activeTab === 'plan' && currentRunId && (
          <section className="tab-content-section">
            <PlanReviewCard
              runId={currentRunId}
              onApproved={() => {
                setActiveTab('preview');
                handleRefreshPreview();
              }}
              onPlanUpdated={() => {
                setReloadTrigger((v) => v + 1);
                fetchDetails(currentRunId);
              }}
            />
          </section>
        )}

        {/* Tab 3: QA Scorecard */}
        {activeTab === 'qa' && currentRunId && (
          <section className="tab-content-section">
            <QAScorecard qaData={qaData} runStatus={runDetails?.status} />
          </section>
        )}

        {/* Tab 4: Requirements Checklist */}
        {activeTab === 'requirements' && currentRunId && (
          <section className="tab-content-section">
            <RequirementsChecklist
              requirements={requirements}
              qaReport={qaData}
            />
          </section>
        )}

        {/* Tab 5: Agent Timeline */}
        {activeTab === 'timeline' && currentRunId && (
          <section className="tab-content-section">
            <AgentTimeline
              runId={currentRunId}
              tasks={tasks}
              onTaskRetried={() => {
                fetchDetails(currentRunId);
              }}
            />
          </section>
        )}

        {/* Tab 6: Template Gallery */}
        {activeTab === 'templates' && (
          <section className="tab-content-section">
            <TemplateGallery
              onSelectTemplate={(prompt) => handleLaunchRun(prompt, 'qwen3.5:4b')}
              onCustomizeTemplate={(prompt) => {
                setCustomPrompt(prompt);
                setIsPromptExpanded(true);
                window.scrollTo({ top: 0, behavior: 'smooth' });
                setTimeout(() => {
                  const el = document.getElementById('goal-prompt');
                  if (el) el.focus();
                }, 100);
              }}
            />
          </section>
        )}

        {/* Bottom Full-Width Log Stream */}
        <section className="log-section">
          <EventFeed events={events} />
        </section>
      </main>

      {/* New Run Modal Dialog */}
      {showPromptModal && (
        <div className="modal-overlay" onClick={() => setShowPromptModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <PromptBar
              onLaunchRun={handleLaunchRun}
              isLaunching={isLaunching}
              onClose={() => setShowPromptModal(false)}
              isModal={true}
              initialPrompt={customPrompt}
            />
            <div className="modal-gallery-row">
              <TemplateGallery
                onSelectTemplate={(prompt) => handleLaunchRun(prompt, 'qwen3.5:4b')}
                onCustomizeTemplate={(prompt) => {
                  setCustomPrompt(prompt);
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {showVersionModal && currentRunId && (
        <VersionHistoryModal
          runId={currentRunId}
          onClose={() => setShowVersionModal(false)}
        />
      )}
    </div>
  );
}
