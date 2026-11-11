import React, { useState, useEffect } from 'react';

const PRESET_EXAMPLES = [
  {
    title: 'French Bistro',
    prompt: 'Build a high-end French bistro website with warm rustic colors, a seasonal menu page, chef story section, and an interactive reservation form.',
  },
  {
    title: 'Developer Portfolio',
    prompt: 'A modern dark-themed portfolio for a creative web developer featuring a sleek hero section, interactive skills grid, project showcase cards, and a contact form with social links.',
  },
  {
    title: 'SaaS Platform',
    prompt: 'A high-converting SaaS landing page for an AI productivity app with clean typography, key value propositions, an interactive 3-tier pricing table, customer testimonials, and a responsive footer.',
  },
  {
    title: 'Artisan Bakery',
    prompt: 'Build an artisan organic bakery website with warm pastels, daily pastry specials grid, baker story section, and catering order inquiry form.',
  },
  {
    title: 'Boutique Store',
    prompt: 'Build an elegant boutique store for sustainable apparel with curated collection grid, product cards with price badges, and customer review testimonials.',
  },
  {
    title: 'Tech Publication',
    prompt: 'Build a thoughtful technology and design publication with featured article hero, 3-column article cards with reading times, and newsletter subscription form.',
  },
];

export default function PromptBar({
  onLaunchRun,
  isLaunching,
  onClose,
  isModal = false,
  initialPrompt = '',
}) {
  const [prompt, setPrompt] = useState(
    initialPrompt ||
    'Build a high-end French bistro website with warm rustic colors, a seasonal menu page, chef story section, and an interactive reservation form.'
  );
  const [model, setModel] = useState('qwen3.5:4b');

  useEffect(() => {
    if (initialPrompt) {
      setPrompt(initialPrompt);
    }
  }, [initialPrompt]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim() || isLaunching) return;
    onLaunchRun(prompt.trim(), model);
  };

  return (
    <div className={`prompt-card ${isModal ? 'prompt-card-modal' : ''}`}>
      <div className="prompt-header">
        <div className="prompt-title-group">
          <h3>⚡ Build Any Website with Autonomous Swarm</h3>
          <p>Type your custom prompt below or choose an example. The multi-agent swarm will plan, code, style, and verify your website.</p>
        </div>
        {isModal && (
          <button className="btn-close" onClick={onClose} aria-label="Close dialog">
            ✕
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="prompt-form">
        <div className="prompt-field-group">
          <label htmlFor="goal-prompt">
            <strong>Website Prompt:</strong>
            <span className="field-hint"> (Describe your business, theme, pages, sections, or specific features)</span>
          </label>
          <textarea
            id="goal-prompt"
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Build an organic Italian restaurant website with menu cards, chef profile, dark burgundy theme, and a table booking form..."
            required
            autoFocus={isModal}
          />
        </div>

        <div className="presets-row">
          <span className="presets-label">Quick Ideas:</span>
          {PRESET_EXAMPLES.map((ex, idx) => (
            <button
              key={idx}
              type="button"
              className="chip-preset"
              onClick={() => setPrompt(ex.prompt)}
              title="Click to insert this prompt"
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
              <option value="qwen3.5:4b">qwen3.5:4b (Fast Local - Default)</option>
              <option value="qwen2.5-coder:7b">qwen2.5-coder:7b (High Accuracy)</option>
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
              className="btn-primary btn-generate"
              disabled={isLaunching || !prompt.trim()}
            >
              {isLaunching ? (
                <>
                  <span className="spinner"></span> Spawning Swarm...
                </>
              ) : (
                '🚀 Generate Website'
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

