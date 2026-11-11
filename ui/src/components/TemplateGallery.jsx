import React from 'react';

const TEMPLATES = [
  {
    type: 'restaurant',
    title: 'Culinary Bistro & Lounge',
    icon: '🍽️',
    description: 'Artisan farm-to-table dining with seasonal menu highlights, chef story, and reservation form.',
    prompt: 'Build a high-end French bistro website with warm rustic colors, a seasonal menu page, chef story section, and an interactive reservation form.',
    pages: ['index.html', 'menu.html', 'about.html'],
  },
  {
    type: 'saas',
    title: 'AI Platform & Cloud Dev',
    icon: '🚀',
    description: 'High-conversion developer platform landing page with live statistics, tiered pricing, and terminal preview.',
    prompt: 'Build a modern SaaS landing page for an AI agent platform with dark theme, live metric counters, 3-tier pricing table, and newsletter waitlist form.',
    pages: ['index.html'],
  },
  {
    type: 'portfolio',
    title: 'Creative Engineering Studio',
    icon: '💼',
    description: 'Minimalist designer and full-stack engineer showcase with interactive case studies and contact form.',
    prompt: 'Build a clean software architect portfolio with a selected projects grid, skills badge matrix, case study cards, and an inquiry contact form.',
    pages: ['index.html', 'work.html'],
  },
  {
    type: 'store',
    title: 'Lifestyle Apparel & Goods',
    icon: '🛍️',
    description: 'Sleek e-commerce storefront with product grid, price tags, category filters, and sustainable trust badges.',
    prompt: 'Build an elegant boutique store for sustainable apparel with curated collection grid, product cards with price badges, and customer review testimonials.',
    pages: ['index.html'],
  },
  {
    type: 'blog',
    title: 'Tech & Architecture Journal',
    icon: '✍️',
    description: 'Clean editorial publication with featured essays, 3-column articles grid, reading times, and author bios.',
    prompt: 'Build a thoughtful technology and design publication with featured article hero, 3-column article cards with reading times, and newsletter subscription form.',
    pages: ['index.html'],
  },
];

export default function TemplateGallery({ onSelectTemplate, onCustomizeTemplate }) {
  return (
    <div className="template-gallery-container">
      <div className="gallery-header">
        <h3>🎨 Starter Template Gallery</h3>
        <p>Select a hand-crafted architecture template to generate immediately or customize the prompt first.</p>
      </div>

      <div className="templates-cards-grid">
        {TEMPLATES.map((tmpl) => (
          <div key={tmpl.type} className="template-card">
            <div className="card-top-row">
              <span className="template-icon">{tmpl.icon}</span>
              <span className="template-type-badge">{tmpl.type}</span>
            </div>
            <h4>{tmpl.title}</h4>
            <p className="template-desc">{tmpl.description}</p>
            <div className="template-pages">
              {tmpl.pages.map((p) => (
                <span key={p} className="page-tag">{p}</span>
              ))}
            </div>
            <div className="template-actions-row">
              <button
                className="btn-use-template"
                onClick={() => onSelectTemplate(tmpl.prompt)}
                title="Immediately build this template"
              >
                ⚡ Generate
              </button>
              {onCustomizeTemplate && (
                <button
                  type="button"
                  className="btn-customize-template"
                  onClick={() => onCustomizeTemplate(tmpl.prompt)}
                  title="Load prompt into editor to tweak"
                >
                  ✏️ Edit Prompt
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

