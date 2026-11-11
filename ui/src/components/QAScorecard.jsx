import React from 'react';

export default function QAScorecard({ qaData, runStatus }) {
  if (!qaData) {
    return (
      <div className="qa-scorecard empty">
        <h4>🛡️ Deterministic QA Scorecard</h4>
        <p className="empty-hint">QA validation runs automatically once structure, style, and script tasks complete.</p>
      </div>
    );
  }

  const { score = 0, passed = false, defects = [], checks_passed = [] } = qaData;

  const checks = [
    {
      id: 'link-check',
      label: 'Links Integrity',
      desc: 'All relative and anchor links resolve correctly (no dead links or "#" stubs)',
      passed: !defects.some((d) => d.rule === 'link-check'),
    },
    {
      id: 'theme-check',
      label: 'Theme & CSS Variables',
      desc: 'No hardcoded hex colors or fonts outside generated :root tokens',
      passed: !defects.some((d) => d.rule === 'theme-check'),
    },
    {
      id: 'requirements-check',
      label: 'Requirements Coverage',
      desc: 'Every section and feature from spec.json is present in HTML/JS',
      passed: !defects.some((d) => d.rule === 'requirements-check'),
    },
    {
      id: 'responsive-check',
      label: 'Responsive Design',
      desc: 'Fluid layouts, meta viewport tags, and 390px/1280px breakpoints',
      passed: !defects.some((d) => d.rule === 'responsive-check'),
    },
    {
      id: 'accessibility-check',
      label: 'Accessibility (a11y)',
      desc: 'Single <h1> per page, non-empty image alt text, and form labels',
      passed: !defects.some((d) => d.rule === 'accessibility-check'),
    },
    {
      id: 'js-check',
      label: 'JavaScript Integrity',
      desc: 'Brace balance, null checks on DOM queries, zero console errors',
      passed: !defects.some((d) => d.rule === 'js-check'),
    },
  ];

  return (
    <div className="qa-scorecard">
      <div className="scorecard-header">
        <div className="score-summary">
          <div className={`score-circle ${passed ? 'passed' : 'failing'}`}>
            <span className="score-number">{score}</span>
            <span className="score-max">/100</span>
          </div>
          <div className="score-text">
            <h4>🛡️ Deterministic QA Audit</h4>
            <p className="score-status">
              {passed ? (
                <span className="status-badge passed">✅ Converged & Verified (100% Pass)</span>
              ) : runStatus === 'running' ? (
                <span className="status-badge running">⏳ Audit in Progress...</span>
              ) : (
                <span className="status-badge partial">⚠️ {defects.length} Defect(s) Identified</span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* 6 Core Check Cards Grid */}
      <div className="qa-checks-grid">
        {checks.map((chk) => (
          <div key={chk.id} className={`qa-check-card ${chk.passed ? 'pass' : 'fail'}`}>
            <div className="check-icon">{chk.passed ? '✓' : '✕'}</div>
            <div className="check-info">
              <h5>{chk.label}</h5>
              <p>{chk.desc}</p>
            </div>
            <span className={`check-badge ${chk.passed ? 'pass' : 'fail'}`}>
              {chk.passed ? 'Pass' : 'Defect'}
            </span>
          </div>
        ))}
      </div>

      {/* Actionable Defects Table */}
      {defects.length > 0 && (
        <div className="defects-section">
          <h5>Actionable Defects ({defects.length})</h5>
          <div className="defects-table-wrapper">
            <table className="defects-table">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Line</th>
                  <th>Rule</th>
                  <th>Summary</th>
                  <th>Fix Hint</th>
                </tr>
              </thead>
              <tbody>
                {defects.map((d, i) => (
                  <tr key={i} className={`defect-row severity-${d.severity || 'high'}`}>
                    <td className="defect-file">{d.target}</td>
                    <td className="defect-line">{d.line || '-'}</td>
                    <td className="defect-rule"><code>{d.rule}</code></td>
                    <td className="defect-summary">{d.summary}</td>
                    <td className="defect-hint">{d.remediation || 'Repair required'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

