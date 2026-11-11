/**
 * API and WebSocket client for Swarm Website Builder.
 * Communicates with FastAPI backend on port 8000 via Vite proxy or direct URL.
 */

const API_BASE = ''; // Uses Vite proxy in development

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function listRuns() {
  const res = await fetch(`${API_BASE}/runs`);
  if (!res.ok) throw new Error(`Failed to list runs: ${res.statusText}`);
  return res.json();
}

export async function getRunDetails(runId) {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch run details for ${runId}: ${res.statusText}`);
  return res.json();
}

export async function getRunEvents(runId, sinceId = 0) {
  const res = await fetch(`${API_BASE}/runs/${runId}/events?since_id=${sinceId}`);
  if (!res.ok) throw new Error(`Failed to fetch events: ${res.statusText}`);
  return res.json();
}

export async function createRun(prompt, model = 'qwen3.5:4b', referenceImage = null) {
  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      model,
      reference_image: referenceImage,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create run: ${res.statusText}`);
  }
  return res.json();
}

export function subscribeToRun(runId, onMessage, onError, onOpen, onClose) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // If Vite proxying ws, connects to window.location.host; fallback to 127.0.0.1:8000 if needed
  const wsUrl = `${protocol}//${window.location.host}/ws/runs/${runId}`;

  let ws = null;
  let isClosedManually = false;

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = (e) => {
      if (onOpen) onOpen(e);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);
      } catch (err) {
        console.error('Failed to parse WebSocket JSON payload:', err);
      }
    };

    ws.onerror = (err) => {
      if (onError) onError(err);
    };

    ws.onclose = (event) => {
      if (!isClosedManually && onClose) onClose(event);
    };
  } catch (err) {
    if (onError) onError(err);
  }

  return {
    close: () => {
      isClosedManually = true;
      if (ws) ws.close();
    },
  };
}

export async function getRunSpec(runId) {
  const res = await fetch(`${API_BASE}/runs/${runId}/spec`);
  if (!res.ok) throw new Error(`Failed to fetch spec: ${res.statusText}`);
  return res.json();
}

export async function updateRunSpec(runId, spec) {
  const res = await fetch(`${API_BASE}/runs/${runId}/spec`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ spec }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update spec: ${res.statusText}`);
  }
  return res.json();
}

export async function submitQuickEdit(runId, instruction, targetFile = 'styles.css') {
  const res = await fetch(`${API_BASE}/runs/${runId}/quick-edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ instruction, target_file: targetFile }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to submit quick edit: ${res.statusText}`);
  }
  return res.json();
}

export async function retryTask(runId, taskId) {
  const res = await fetch(`${API_BASE}/runs/${runId}/tasks/${taskId}/retry`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to retry task: ${res.statusText}`);
  return res.json();
}

export async function getRunVersions(runId) {
  const res = await fetch(`${API_BASE}/runs/${runId}/versions`);
  if (!res.ok) throw new Error(`Failed to fetch versions: ${res.statusText}`);
  return res.json();
}

export function getZipExportUrl(runId) {
  return `${API_BASE}/runs/${runId}/export/zip`;
}

