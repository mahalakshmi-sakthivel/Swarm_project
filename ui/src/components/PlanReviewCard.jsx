import React, { useState, useEffect } from 'react';
import { getRunSpec, updateRunSpec } from '../services/api';

export default function PlanReviewCard({ runId, onApproved, onPlanUpdated }) {
  const [spec, setSpec] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!runId) return;
    let isMounted = true;
    setLoading(true);
    setError(null);

    getRunSpec(runId)
      .then((data) => {
        if (isMounted) {
          setSpec(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [runId]);

  if (loading) {
    return (
      <div className="plan-review-card loading">
        <div className="spinner"></div>
        <p>Loading synthesized SiteSpec contract...</p>
      </div>
    );
  }

  if (error || !spec) {
    return null; // Don't show if spec not yet ready or failed
  }

  const handleColorChange = async (colorKey, newColor) => {
    const updatedSpec = {
      ...spec,
      theme: {
        ...spec.theme,
        [colorKey]: newColor,
      },
    };
    setSpec(updatedSpec);

    // Instant live regeneration of base.css without LLM call
    try {
      await updateRunSpec(runId, updatedSpec);
      if (onPlanUpdated) onPlanUpdated();
    } catch (err) {
      console.error('Failed to update live theme:', err);
    }
  };

  const handleFontChange = async (fontKey, newFont) => {
    const updatedSpec = {
      ...spec,
      theme: {
        ...spec.theme,
        [fontKey]: newFont,
      },
    };
    setSpec(updatedSpec);
    try {
      await updateRunSpec(runId, updatedSpec);
      if (onPlanUpdated) onPlanUpdated();
    } catch (err) {
      console.error('Failed to update live font:', err);
    }
  };

  const handleApprove = () => {
    if (onApproved) onApproved();
  };

  return (
    <div className="plan-review-card">
      <div className="plan-review-header">
        <div className="plan-title-group">
          <span className="badge badge-accent">Phase 1 Contract</span>
          <h3>📋 Site Plan & Theme Review: {spec.brand_name}</h3>
          <p className="plan-tagline">{spec.tagline || 'Autonomous website architecture plan'}</p>
        </div>
        <button className="btn-approve" onClick={handleApprove}>
          ✓ Approve & Build
        </button>
      </div>

      <div className="plan-grid">
        {/* Pages Hierarchy & Nav */}
        <div className="plan-section">
          <h4>Pages & Navigation Hierarchy</h4>
          <div className="pages-list">
            {spec.pages?.map((p, idx) => (
              <div key={p.id || idx} className="page-item-badge">
                <span className="page-order">{idx + 1}</span>
                <span className="page-title">{p.title}</span>
                <span className="page-file">({p.file})</span>
                <span className="section-count">{p.sections?.length || 0} sections</span>
              </div>
            ))}
          </div>
        </div>

        {/* Live Theme Color Tokens */}
        <div className="plan-section">
          <h4>Theme Color Tokens (Instant :root Edit)</h4>
          <div className="color-swatches-grid">
            {['primary', 'secondary', 'accent', 'bg', 'text'].map((cKey) => (
              <div key={cKey} className="color-swatch-control">
                <label>{cKey}</label>
                <div className="swatch-wrapper">
                  <input
                    type="color"
                    value={spec.theme?.[cKey] || '#2563eb'}
                    onChange={(e) => handleColorChange(cKey, e.target.value)}
                  />
                  <span className="color-hex">{spec.theme?.[cKey]}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Typography */}
        <div className="plan-section">
          <h4>Typography</h4>
          <div className="fonts-control-row">
            <div className="font-item">
              <label>Heading Font</label>
              <select
                value={spec.theme?.font_heading || 'Inter'}
                onChange={(e) => handleFontChange('font_heading', e.target.value)}
              >
                <option value="Inter">Inter</option>
                <option value="Poppins">Poppins</option>
                <option value="Playfair Display">Playfair Display</option>
                <option value="Space Grotesk">Space Grotesk</option>
                <option value="Cinzel">Cinzel</option>
                <option value="Outfit">Outfit</option>
              </select>
            </div>
            <div className="font-item">
              <label>Body Font</label>
              <select
                value={spec.theme?.font_body || 'Inter'}
                onChange={(e) => handleFontChange('font_body', e.target.value)}
              >
                <option value="Inter">Inter</option>
                <option value="Roboto">Roboto</option>
                <option value="Open Sans">Open Sans</option>
                <option value="Lato">Lato</option>
                <option value="Plus Jakarta Sans">Plus Jakarta Sans</option>
              </select>
            </div>
          </div>
        </div>

        {/* Features & Requirements */}
        <div className="plan-section">
          <h4>Features & Requirements ({spec.requirements?.length || 0})</h4>
          <div className="requirements-preview-pills">
            {spec.requirements?.map((req) => (
              <span key={req.id} className="req-pill" title={req.description}>
                <strong>{req.id}:</strong> {req.description}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
