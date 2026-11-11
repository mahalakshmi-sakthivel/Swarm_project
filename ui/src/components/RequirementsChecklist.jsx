import React from 'react';

export default function RequirementsChecklist({ requirements = [], qaReport = null }) {
  if (!requirements || requirements.length === 0) {
    return (
      <div className="requirements-panel empty">
        <h4>📋 Requirements Checklist</h4>
        <p className="empty-hint">Requirements will be extracted from your goal prompt after task-00-plan.</p>
      </div>
    );
  }

  // Derive pass/fail status per requirement ID from QA defects
  const failingReqIds = new Set();
  if (qaReport?.defects) {
    for (const defect of qaReport.defects) {
      if (defect.req_id) {
        failingReqIds.add(defect.req_id);
      }
    }
  }

  const satisfiedCount = requirements.filter((r) => !failingReqIds.has(r.id)).length;
  const totalCount = requirements.length;
  const coveragePercent = totalCount > 0 ? Math.round((satisfiedCount / totalCount) * 100) : 100;

  return (
    <div className="requirements-panel">
      <div className="panel-header">
        <div className="panel-title-row">
          <h4>📋 Requirements Checklist</h4>
          <span className={`coverage-badge ${coveragePercent === 100 ? 'full' : 'partial'}`}>
            {coveragePercent}% Verified ({satisfiedCount}/{totalCount})
          </span>
        </div>
        <p className="panel-subtitle">Live validation against deterministic QA audit rules</p>
      </div>

      <div className="requirements-list">
        {requirements.map((req) => {
          const isFailing = failingReqIds.has(req.id);
          const isSatisfied = !isFailing;
          return (
            <div key={req.id} className={`requirement-card ${isSatisfied ? 'pass' : 'fail'}`}>
              <div className="req-status-icon">
                {isSatisfied ? '✅' : '❌'}
              </div>
              <div className="req-details">
                <div className="req-id-badge">{req.id}</div>
                <p className="req-description">{req.description}</p>
              </div>
              <span className={`status-pill ${isSatisfied ? 'satisfied' : 'pending'}`}>
                {isSatisfied ? 'Pass' : 'Defect Found'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

