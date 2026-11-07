# Stage 4: Real-Time Swarm Dashboard (Frontend UI)

## 1. Overview
Stage 4 delivers a real-time reactive dashboard for visualizing, inspecting, and launching autonomous multi-agent swarms. Built with React 19, Vite, JavaScript, and modern CSS tokens following the UX/UI Specification (`docs/ux_ui_spec.md`), the dashboard communicates seamlessly with the Stage 3 FastAPI backend via REST and Starlette WebSocket streaming.

### Key Components Built:
1. **Header & Run Switcher ([`ui/src/components/Header.jsx`](file:///D:/swarm%20technology/ui/src/components/Header.jsx))**:
   - Swarm Website Builder branding with pulse indicators.
   - Run dropdown switcher enabling instant browsing across historical and active runs.
   - Status chips (`Running`, `Converged`, `Failed`), QA audit score pill, and WebSocket connection indicator (`Live WS` / `Polling`).
   - Quick "New Build" launcher and manual preview refresh button.

2. **Goal Prompt Input & Presets ([`ui/src/components/PromptBar.jsx`](file:///D:/swarm%20technology/ui/src/components/PromptBar.jsx))**:
   - Multi-line textarea for goal prompts with character counter support.
   - 4 quick preset examples (Developer Portfolio, SaaS Landing Page, Cyberpunk Game Showcase, Creative Design Agency).
   - Model selection dropdown (`qwen3.5:4b`, `qwen2.5-coder:7b`, etc.).
   - Launch button with spinner states that triggers `POST /runs`.

3. **Swarm Agent Cards ([`ui/src/components/AgentCards.jsx`](file:///D:/swarm%20technology/ui/src/components/AgentCards.jsx))**:
   - Visual cards for the 5 specialized swarm roles:
     - `structure` (`#60a5fa` - Blue)
     - `style` (`#e879f9` - Magenta)
     - `script` (`#4ade80` - Green)
     - `qa` (`#fb923c` - Amber)
     - `integration` (`#22d3ee` - Cyan)
   - Real-time status badges (`idle`, `working`, `done`, `failed`).
   - Displays claimed task title, target filename, and active pulse animations.

4. **Blackboard Kanban Task Board ([`ui/src/components/TaskBoard.jsx`](file:///D:/swarm%20technology/ui/src/components/TaskBoard.jsx))**:
   - 3-column Kanban board (`Open`, `In Progress`, `Completed`) reflecting the shared SQLite memory state.
   - Task cards showing priority tags (e.g. `P1`, `P5`), role badges, target file links, owner agent badges, and task descriptions.

5. **Sandbox Live Preview Pane ([`ui/src/components/PreviewPane.jsx`](file:///D:/swarm%20technology/ui/src/components/PreviewPane.jsx))**:
   - Sandboxed `<iframe>` rendering `/runs/{run_id}/preview/index.html`.
   - Automatic hot-reload triggered when `file_edit`, `task_done`, or `qa_audit` events are pushed over WebSocket.
   - Viewport switcher: Desktop (100%), Tablet (768px), Mobile (375px).
   - "Open Tab" shortcut to open the generated site in a separate browser window.

6. **Interactive Swarm Cursor Overlay ([`ui/src/components/CursorOverlay.jsx`](file:///D:/swarm%20technology/ui/src/components/CursorOverlay.jsx))**:
   - Visual overlay projecting agent pointers and activity pills directly above the preview sandbox.
   - Smooth movement and pulsing rings indicating which agent is actively editing or auditing code.
   - Toggle button to enable/disable cursors at any time.

7. **Live Event Terminal Log ([`ui/src/components/EventFeed.jsx`](file:///D:/swarm%20technology/ui/src/components/EventFeed.jsx))**:
   - High-contrast monospace terminal consuming WebSocket events (`/ws/runs/{run_id}`).
   - Multi-criteria filtering: by agent role, by event type (`file_edit`, `task_claimed`, `task_done`, `qa_audit`, etc.), and free-text search query.
   - Auto-scroll lock toggle with timestamps and color-coded event chips.

8. **API & WebSocket Client Service ([`ui/src/services/api.js`](file:///D:/swarm%20technology/ui/src/services/api.js))**:
   - Handles REST calls (`/runs`, `/runs/{id}`, `/health`) and WebSocket lifecycle management (`onopen`, `onmessage`, `onerror`, `onclose`).

9. **FastAPI Static Mount ([`api/server.py`](file:///D:/swarm%20technology/api/server.py))**:
   - Compiled React bundle (`ui/dist`) is directly served from the root route `/` of the FastAPI backend (`http://127.0.0.1:8000/`).

---

## 2. Verification & Testing

### Test Suite Execution
- All 11 API and WebSocket tests passed:
  - `test_health_endpoint`: PASSED
  - `test_favicon_endpoint`: PASSED (204 No Content)
  - `test_dashboard_root_serving`: PASSED (Serves compiled React HTML at `/`)
  - `test_list_runs`: PASSED
  - `test_get_run_details`: PASSED
  - `test_get_run_events_polling`: PASSED
  - `test_preview_html_asset`: PASSED
  - `test_preview_css_asset`: PASSED
  - `test_preview_js_asset`: PASSED
  - `test_preview_traversal_security_rejection`: PASSED
  - `test_websocket_event_streaming`: PASSED
- Total test suite status: **33/33 tests passing** across entire project repository.

### Production Build Verification
- Built cleanly with Vite:
  - `dist/index.html` (0.45 kB)
  - `dist/assets/index-*.css` (17.10 kB)
  - `dist/assets/index-*.js` (242.40 kB)
  - Build time: 225ms.
