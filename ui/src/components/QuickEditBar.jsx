import React, { useState } from 'react';
import { submitQuickEdit } from '../services/api';

export default function QuickEditBar({ runId, onEditSubmitted }) {
  const [instruction, setInstruction] = useState('');
  const [targetFile, setTargetFile] = useState('styles.css');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!instruction.trim() || !runId) return;

    setIsSubmitting(true);
    setFeedback(null);
    try {
      const res = await submitQuickEdit(runId, instruction, targetFile);
      setInstruction('');
      setFeedback(`Targeted edit queued for @${res.role} on ${res.target}`);
      if (onEditSubmitted) onEditSubmitted(res);
      setTimeout(() => setFeedback(null), 4000);
    } catch (err) {
      alert(`Error submitting quick edit: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="quick-edit-bar">
      <form onSubmit={handleSubmit} className="quick-edit-form">
        <div className="quick-edit-label">
          <span>⚡ Quick Edit:</span>
        </div>
        <input
          type="text"
          className="quick-edit-input"
          placeholder="e.g. 'Make the hero background darker' or 'Increase card border radius to 16px'..."
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          disabled={isSubmitting || !runId}
        />
        <select
          className="quick-edit-select"
          value={targetFile}
          onChange={(e) => setTargetFile(e.target.value)}
          disabled={isSubmitting || !runId}
        >
          <option value="styles.css">styles.css (Styling)</option>
          <option value="index.html">index.html (Structure)</option>
          <option value="script.js">script.js (Interactivity)</option>
        </select>
        <button
          type="submit"
          className="btn-quick-submit"
          disabled={isSubmitting || !instruction.trim() || !runId}
        >
          {isSubmitting ? 'Routing...' : 'Apply Edit'}
        </button>
      </form>
      {feedback && <div className="quick-edit-feedback">{feedback}</div>}
    </div>
  );
}
