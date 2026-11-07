import React, { useState } from 'react';

const PRESET_EXAMPLES = [
  {
    title: 'Developer Portfolio',
    prompt: 'A modern dark-themed portfolio for a creative web developer featuring a sleek hero section, interactive skills grid, project showcase cards, and a contact form with social links.',
  },
  {
    title: 'SaaS Landing Page',
    prompt: 'A high-converting SaaS landing page for an AI productivity app with clean typography, key value propositions, an interactive 3-tier pricing table, customer testimonials, and a responsive footer.',
  },
  {
    title: 'Cyberpunk Game Showcase',
    prompt: 'A futuristic cyberpunk video game showcase website with neon violet glow effects, interactive character cards, game feature highlights, system requirements matrix, and newsletter signup.',
  },
  {
    title: 'Creative Design Agency',
    prompt: 'A minimal modern design agency website featuring bold typography, grid-based case studies with tag filters, about us leadership gallery, and interactive service booking inquiries.',
  },
];

export default function PromptBar({ onLaunchRun, isLaunching, onClose, isModal = false }) {
  const [prompt, setPrompt] = useState(
    'A modern dark-themed portfolio for a creative web developer featuring a sleek hero section, interactive skills grid, project showcase cards, and a contact form with social links.'
  );
  const [model, setModel] = useState('qwen3.5:4b');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim() || isLaunching) return;
    onLaunchRun(prompt.trim(), model);
  };

  return (
    <div className={`prompt-card ${isModal ? 'prompt-card-modal' : ''}`}>
      <div className="prompt-header">
        <div className="prompt-title-group">
          <h3>🚀 Start New Autonomous Swarm Build</h3>
          <p>The decentralized swarm of specialized agents will self-organize, write code, audit quality, and converge.</p>
        </div>
        {isModal && (
          <button className="btn-close" onClick={onClose}>
            ✕
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="prompt-form">
        <div className="prompt-field-group">
          <label htmlFor="goal-prompt">Goal Prompt:</label>
          <textarea
            id="goal-prompt"
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the website you want the swarm to build..."
            required
          />
        </div>

        <div className="presets-row">
          <span className="presets-label">Examples:</span>
          {PRESET_EXAMPLES.map((ex, idx) => (
            <button
              key={idx}
              type="button"
              className="chip-preset"
              onClick={() => setPrompt(ex.prompt)}
            >
              {ex.title}
            </button>
          ))}
        </div>

        <div className="prompt-controls-row">
          <div className="model-select-group">
            <label htmlFor="model-select">Ollama Model:</label>
            <select
              id="model-select"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              <option value="qwen3.5:4b">qwen3.5:4b (Fast Local)</option>
              <option value="qwen2.5-coder:7b">qwen2.5-coder:7b</option>
              <option value="qwen2.5-coder:1.5b">qwen2.5-coder:1.5b (Ultra Light)</option>
              <option value="deepseek-r1:1.5b">deepseek-r1:1.5b</option>
            </select>
          </div>

          <div className="submit-group">
            {isModal && (
              <button type="button" className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
            )}
            <button
              type="submit"
              className="btn-primary"
              disabled={isLaunching || !prompt.trim()}
            >
              {isLaunching ? (
                <>
                  <span className="spinner"></span> Spawning Swarm...
                </>
              ) : (
                'Launch Swarm Agents'
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
