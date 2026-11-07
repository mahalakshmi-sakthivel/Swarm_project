# Swarm Website Builder: UX/UI Specification

Version 1.0 | November 2026 | Status: Draft for mentor review
Derived from: Project Overview, sections 7 (users and use cases) and 12 (swarm cursor visualization)
Companion document: Data Model and API Specification (event types, endpoints and field names used here are defined there)

---

## 1. Purpose and scope

This document specifies the user experience and interface of the Swarm Website Builder: screens, layout, components, interaction rules, visual design tokens, states, accessibility and acceptance criteria.

**In scope:** the React interface (prompt and screenshot input, live preview with swarm cursors, task board, agent list, log stream, progress, replay mode, evaluation dashboard).

**Out of scope:** the generated websites' own design (that is the agents' output), user accounts, and mobile-first design of the builder itself (see section 13 for the supported viewports).

---

## 2. Users and goals

| User | Goal | Main screens | Use cases |
| --- | --- | --- | --- |
| Student or researcher studying multi-agent systems | See how agents coordinate, inspect individual agents, run failure experiments | Build view, Replay, Experiments | UC1, UC3, UC6 |
| Developer wanting a fast website draft | Enter a prompt or screenshot, get a working site, adjust it | Start, Build view | UC1, UC2, UC4 |
| Evaluator or mentor | Verify that the swarm works, compare it with baselines | Build view, Replay, Experiments | UC1, UC3, UC5 |
| Researcher running benchmarks | Configure experiments, read results, export data | Experiments | UC5, UC6 |

---

## 3. Design principles

1. **Real events only.** A cursor moves only when its agent does something real. The interface replays the event log and never invents motion. Decorative animation is not allowed.
2. **Show the swarm, not a controller.** No element may imply a boss agent. Agents are shown as equals with different role colors.
3. **Cause and effect are visible.** Every visual change in the preview can be traced to an event in the log with one click.
4. **Calm by default.** Many agents act at once. Motion is short, small and stackable. The user can slow, filter or pause at any time.
5. **Fast to start.** A new user starts a build in under a minute (non-functional requirement). The Start screen has one required field.
6. **Honest states.** Failures, stalls and recoveries are shown plainly, because resilience is a research result and not something to hide.

---

## 4. Information architecture

```
App
├── Start                      /                         (new build: prompt or screenshot)
├── Builds                     /builds                   (history list)
├── Build view                 /builds/:id               (live and finished builds)
│    └── Replay mode           /builds/:id?replay=1
├── Experiments                /experiments              (list and create)
│    └── Experiment detail     /experiments/:id          (live runs, summary, export)
└── Settings                   /settings                 (models, defaults, theme)
```

Primary navigation: a left rail with Start, Builds, Experiments, Settings. The Build view hides the rail by default to give the preview more space (toggle with the menu button).

---

## 5. User flows

### 5.1 UC1: Prompt to website

1. User opens **Start**, types a prompt, optionally adjusts options, presses **Build**.
2. App creates the build and navigates to the **Build view**.
3. Seeding phase: a banner reads "Seeding tasks". Task board fills with cards. Agent cursors appear one by one (`agent_spawned`).
4. Agents claim tasks (`task_claimed`), cursors move to targets, edits appear in the preview.
5. Testing agent runs tests. Failed sections flash red, fixes flash green.
6. Build completes: progress reaches 100%, a completion banner shows scores and a **Download project** button.

### 5.2 UC2: Screenshot to website

1. User switches the Start screen to **Screenshot** mode and uploads or drops an image.
2. Image preview and similarity threshold slider appear. User presses **Build**.
3. In the Build view the preview area is a **split view**: reference on the left, generated site on the right. A similarity gauge shows the latest score and iteration count.
4. Each vision iteration updates the gauge and per-section similarity chips. The build ends when the threshold or iteration limit is reached.

### 5.3 UC3: Inspect an agent

1. User clicks a cursor (or an agent in the agent list).
2. The **Agent drawer** opens on the right: role, model, status, current task, recent actions (from events), the latest "thought", and statistics.
3. The cursor stays highlighted with a ring while the drawer is open. Clicking a recent action jumps the log and preview to that event.

### 5.4 UC4: Rebuild with a modified prompt

1. In the Build view, user presses **Rebuild**.
2. A dialog shows the original prompt as editable text and a checkbox "Reuse current files as the starting point".
3. User confirms. A new build starts and the app navigates to it. The old build stays in history with a "Rebuilt as ..." link.

### 5.5 UC5: Run a benchmark

1. In **Experiments**, user presses **New experiment** and picks a preset (E1 to E4) or a custom setup.
2. User selects systems (B1, B2, B3, S), test prompts or screenshots, repetitions (minimum 3), and optional failure injection.
3. User starts the run. The detail page shows a live runs table and charts that fill as runs finish.
4. When complete, the user opens the summary and exports CSV or JSON.

### 5.6 UC6: Inject a failure

1. In the Build view, the user selects an agent (cursor or list) and opens the **Inject failure** menu in the Agent drawer: Kill, Pause or Stall.
2. A confirmation dialog explains the effect. The user confirms.
3. The cursor changes state (fades for Kill, dims for Pause). The task card shows a lease countdown. After lease expiry the card returns to Open and a replacement cursor appears.
4. A **Recovery timer** chip shows the time from failure to replacement and to task completion.

---

## 6. Screens

### 6.1 Start screen

```
┌──────────────────────────────────────────────────────────────┐
│  Swarm Website Builder                                       │
│                                                              │
│  [ Prompt ] [ Screenshot ]                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Describe the website you want...                       │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│  Examples: Portfolio · Blog · Landing page · Dashboard       │
│                                                              │
│  ▸ Options   Roles: [UI/UX][Frontend][Backend][Testing]      │
│              Model size: ( Small )( Balanced )( Large )      │
│              Max iterations: [5]   Seed: [auto]              │
│                                                              │
│                                          [  Build  ]         │
│  Recent builds:  card  card  card                            │
└──────────────────────────────────────────────────────────────┘
```

| Element | Behavior |
| --- | --- |
| Mode tabs | Prompt (default) and Screenshot. Switching keeps entered text |
| Prompt field | Multi-line, up to 2,000 characters, character counter after 1,500. Enter inserts a newline, Ctrl or Cmd + Enter submits |
| Example chips | Fill the prompt field with a sample prompt. Chips are text only |
| Screenshot drop zone | Drag and drop or click. PNG, JPEG or WebP, up to 10 MB. Shows thumbnail, dimensions and a Remove button |
| Similarity threshold | Slider 0.5 to 0.99, default 0.85. Shown only in Screenshot mode |
| Options (collapsed) | Role checkboxes (minimum: Frontend and Testing), model size preset, max iterations (1 to 10), seed |
| Build button | Disabled until the prompt has at least 10 characters (Prompt mode) or an image is attached (Screenshot mode). Shows a spinner after press |
| Recent builds | Up to 6 cards with thumbnail, prompt preview, status and time |

Validation messages appear inline under the field, in plain language (for example, "Please add a bit more detail, at least 10 characters.").

### 6.2 Build view (main screen)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ☰  "Photographer portfolio"   ● Running  58%  ████████░░░░  02:14        │
│                          [Pause view] [Rebuild] [Replay] [Download] [⋯]  │
├──────────────────────────────────────┬───────────────────────────────────┤
│                                      │ Agents (4)                        │
│        LIVE PREVIEW                  │  ● UI/UX-1    working   hero      │
│   (generated site in iframe with     │  ● Frontend-1 working   gallery   │
│    cursor overlay)                   │  ● Backend-1  idle                │
│                                      │  ● Testing-1  working   tests     │
│        ➤ Frontend-1                  ├───────────────────────────────────┤
│        ➤ UI/UX-1                     │ Task board                        │
│                                      │ Open | Claimed | In prog | Review │
│  [Desktop][Tablet][Mobile]  [Cursors]│ | Done                            │
├──────────────────────────────────────┴───────────────────────────────────┤
│ Log   [filters: role ▾ type ▾ search]                   [Auto-scroll ✓]  │
│ 14:21:09  Frontend-1  claimed "Build hero section"                       │
│ 14:21:14  Frontend-1  edited src/pages/index.html (+42 −0)               │
└──────────────────────────────────────────────────────────────────────────┘
```

**Regions**

| Region | Content | Notes |
| --- | --- | --- |
| Top bar | Build title, status chip, progress bar, elapsed time, actions | Sticky. Status chip colors in section 10.3 |
| Preview | Sandboxed iframe of the generated site plus cursor overlay | Takes about 60% of width on desktop |
| Right column | Agent list (top), Task board (bottom) | Resizable divider |
| Bottom panel | Log stream | Collapsible, default height about 25% |
| Agent drawer | Opens over the right column on cursor or agent click | Closes with Esc |

**Top bar actions**

| Action | Behavior |
| --- | --- |
| Pause view | Freezes the **display** only (cursors and log stop updating, events keep buffering). Label changes to "Resume view" and a badge shows buffered event count. The build itself is not paused |
| Rebuild | Opens the rebuild dialog (flow 5.4) |
| Replay | Switches to Replay mode (section 6.3) |
| Download | Available when status is Completed. Downloads the project ZIP |
| Overflow menu | Cancel build, copy build link, export event log (NDJSON), view configuration |

### 6.3 Replay mode

A finished build can be replayed from its event log. The layout is identical to the Build view, with a **timeline bar** replacing the log's auto-scroll toggle.

```
┌────────────────────────────────────────────────────────────────────┐
│  ◀◀   ▶/❚❚   ▶▶     0.5× 1× 2× 4×     ●━━━━━━━━○━━━━━━━━  02:14    │
│  markers:  ▲ agent_failed   ◆ test_failed   ✔ score   ● task_done  │
└────────────────────────────────────────────────────────────────────┘
```

| Control | Behavior |
| --- | --- |
| Play / pause | Space bar toggles |
| Speed | 0.5×, 1×, 2×, 4× (sent to the server as `speed`) |
| Scrub | Drag the handle or click the bar. The interface requests the state at that `seq` and re-renders cursors and preview |
| Step | Left and right arrow keys step one event |
| Markers | Failures, failed tests, scores and completed tasks, clickable |
| Exit | "Back to live" button, or Esc |

The preview in Replay mode shows the project state **at the replayed time** (rebuilt from artifact versions up to that `seq`). If a historic state cannot be rendered, the preview shows a placeholder with the last successful screenshot.

### 6.4 Builds (history)

A table with: thumbnail, title (prompt preview), mode icon (text or image), status, system (S or baseline), duration, final scores, created date. Row actions: Open, Replay, Rebuild, Download, Delete. Filters: status, mode, date. Search by prompt text.

### 6.5 Experiments

**List:** table with code (E1 to E4), name, research question, status, runs completed, created date.

**Create dialog (stepper):**

1. **Preset or custom:** E1 (compare B1, B2, B3, S), E2 (swarm of small vs one larger model), E3 (failure injection), E4 (with and without vision loop).
2. **Systems and models:** checkboxes for B1, B2, B3, S, with model selection per system.
3. **Test set:** multi-select of prompts (10 to 20) and screenshots (5 to 10).
4. **Repetitions and options:** repetitions (minimum 3, default 3), failure injection (mode, count, at what progress), vision loop on or off.
5. **Review and start:** summary with estimated number of runs and a rough time estimate.

**Detail page tabs**

| Tab | Content |
| --- | --- |
| Overview | Status, progress (runs done of total), configuration |
| Runs | Table of runs: system, test case, repetition, status, key metrics, link to the build (opens Build view or Replay) |
| Results | Charts (section 8) and the summary table with mean and standard deviation per system |
| Export | Buttons for CSV and JSON, and "Copy summary as Markdown table" |

### 6.6 Settings

| Section | Controls |
| --- | --- |
| Models | List from the model server (name, size, loaded), default model per role group (simple, main, hard), optional hosted model toggle |
| Defaults | Default roles, lease length, max iterations, similarity threshold |
| Interface | Theme (Light, Dark, System), reduced motion (System, On, Off), cursor labels (Always, On hover), log density |
| Connection | API base URL, server health status |

---

## 7. Swarm cursor visualization (detailed specification)

### 7.1 Principles

- The **event log is the single source of truth**. The cursor layer consumes `event` messages from the WebSocket stream (or replayed events) and applies the behaviors below.
- One cursor per live agent. Positions are computed from the event `target`.
- Cursors are an overlay above the preview iframe and never intercept clicks on the generated site, except on the cursor itself.

### 7.2 Cursor anatomy

| Part | Description |
| --- | --- |
| Pointer | 20 px arrow in the role color with a 1.5 px white outline |
| Label | Rounded pill beside the pointer: agent display name (for example "Frontend-1") and a one-word activity ("editing", "testing", "idle") |
| Trail | Soft line following the pointer for 400 ms after a move |
| State ring | Thin ring around the pointer: selected (white), failed (red dashed), paused (gray) |

Labels are always shown by default. If more than six cursors are active, labels switch to initials and show the full label on hover.

### 7.3 Event to cursor mapping

This table extends the overview (section 12). Timings are defaults and scale with the replay speed.

| Event | Cursor and preview behavior | Duration |
| --- | --- | --- |
| `agent_spawned` | Cursor fades and scales in at the top-left of the preview. Agent list row appears | 300 ms |
| `task_claimed` | Cursor glides to the center of the target section (found by `target`). Task card moves to Claimed | 500 ms, ease-out |
| `task_started` | Label changes to "working". Task card moves to In progress | Instant |
| `file_edit` | Typing indicator on the pointer. The target section gets a soft outline in the role color. Preview reloads (debounced) | Outline holds 1.2 s |
| `signal_emitted` | Pulse (expanding ring) at the target, color by signal type (section 10.3). Signal chip appears in the target's badge area | 800 ms |
| `signal_reinforced` | Pulse repeats with larger radius. Chip shows a small count | 800 ms |
| `test_run` | Cursor glides to the preview toolbar or Tests tab. Label shows "testing" and a small spinner | While suite runs |
| `test_failed` | Target section flashes red, failure badge stays until fixed. Log row gets a red marker | Flash 1 s |
| `fix_applied` | Target section flashes green and the failure badge clears | Flash 1 s |
| `conflict_detected` | Section outlined in orange with a "conflict" chip until resolved | Until resolved |
| `lease_expired` | Task card shows a warning icon and returns to Open | Instant |
| `agent_failed` | Cursor desaturates and fades out over 600 ms, leaving a small ✕ marker at its last position for 5 s. Agent list row turns red | 600 ms |
| `agent_recovered` | Replacement cursor appears at the failed cursor's last position with a brief highlight and then moves to the task target. A dotted line links the old marker to the new cursor | 700 ms |
| `agent_paused` / `agent_resumed` | Cursor dims to 40% / restores | 200 ms |
| `task_done` | Section receives a brief check badge, section marked complete in the page outline, progress bar updates | 600 ms |
| `build_completed` | All cursors gather at the bottom of the preview and fade out. Completion banner appears | 1 s |

### 7.4 Target resolution

1. `section:<name>`: the generated page marks sections with `data-swarm-section="<name>"`. The overlay locates that element's bounding box in the iframe and anchors the cursor to its center.
2. `file:<path>`: the cursor goes to the section most associated with the file (from the last known mapping). If none is known, it goes to the **Files** tab in the right column.
3. `panel:<name>`: the cursor moves to the named interface panel (`tests`, `preview`, `log`).
4. If a target cannot be found (the section does not exist yet), the cursor goes to a **staging area** at the bottom of the preview, with the label "preparing <name>".

The UI/UX and Frontend agents are instructed (in their system prompts) to add `data-swarm-section` attributes. The Testing agent checks that every section has one.

### 7.5 Many agents, one screen

| Situation | Rule |
| --- | --- |
| Two cursors on the same section | Offset by 24 px horizontally so labels do not overlap |
| More than 8 cursors | Show the 8 most recently active. Others collapse into a "+N" chip that opens the agent list |
| Event bursts (more than 20 events per second) | Coalesce `file_edit` events per agent into one outline. Log keeps every row |
| Display paused or tab hidden | Events buffer. On resume, the layer fast-forwards to the final positions and plays only the last 2 seconds of effects |
| Reduced motion enabled | No gliding or pulses. Cursors jump to targets and show a static highlight for 1 s |

### 7.6 Interaction

- **Click a cursor:** selects it and opens the Agent drawer (flow 5.3).
- **Hover a cursor:** shows a tooltip with the current task title and lease time remaining.
- **Click a section badge:** opens a popover listing signals and tasks tied to that section.
- **Cursor toggle button** (bottom left of the preview): shows or hides the cursor layer. The preview itself is always usable.

---

## 8. Evaluation dashboard

Shown in Experiment detail (Results tab) and as a compact **Scores** panel in the Build view's right column.

### 8.1 Build scores panel

Cards for: build success, test pass rate, Lighthouse (performance, accessibility, best practices), visual similarity (screenshot mode only), model calls and tokens, bugs found and fixed. Each card shows the latest value and a small sparkline by iteration.

### 8.2 Experiment charts

| Chart | Type | Data | Research question |
| --- | --- | --- | --- |
| Quality by system | Grouped bar with error bars | Test pass rate and Lighthouse by B1, B2, B3, S | RQ1 |
| Cost by system | Bar | Model calls, tokens, total time | RQ2 |
| Small swarm vs large model | Paired bar | E2 comparison of quality and cost | RQ2 |
| Recovery | Box plot or dot plot | Recovery time and success rate after failure injection | RQ3 |
| Vision loop | Line chart | Visual similarity by iteration, with and without the loop | RQ4 |
| Per-test-case table | Heat map table | Test case by system, colored by test pass rate | RQ1 |

All charts show averages with variation (standard deviation) over repetitions, include axis labels with units, have a data table alternative, and offer **Download PNG** and **Download CSV**.

Charts must not hide unfavorable results. If the swarm does not beat a baseline, the chart shows that plainly (the overview lists this as an accepted outcome).

---

## 9. Components

| Component | Description | States |
| --- | --- | --- |
| `PromptForm` | Mode tabs, prompt field, drop zone, options, submit | empty, valid, submitting, error |
| `BuildHeader` | Title, status chip, progress bar, timer, actions | running, paused view, completed, failed, cancelled |
| `PreviewPane` | Sandboxed iframe, viewport switcher, cursor toggle | loading, ready, stale (build changed), error |
| `CursorLayer` | Overlay that renders cursors from events | live, replay, paused, reduced motion |
| `Cursor` | Pointer, label, trail, state ring | idle, working, testing, failed, paused, recovered |
| `SplitCompare` | Reference vs generated view with similarity gauge and slider overlay | loading, ready |
| `AgentList` | Rows with color dot, name, status, current target | working, idle, failed, paused |
| `AgentDrawer` | Detail panel (flow 5.3) with Inject failure menu | open, closed |
| `TaskBoard` | Five columns, cards sorted by priority | empty, populated |
| `TaskCard` | Title, role chip, target, priority, owner avatar, lease countdown | per task status |
| `LogStream` | Virtualized list of event rows with filters | live, paused, filtered, empty |
| `SignalChip` | Colored chip with type and strength | strong, fading, resolved |
| `ScoreCard` | Value, sparkline, trend | normal, no data |
| `ReplayBar` | Transport controls, timeline, markers | playing, paused, scrubbing |
| `RunsTable` | Experiment runs with status and metrics | running, done, failed |
| `ChartCard` | Chart, legend, data table toggle, export buttons | loading, ready, no data |
| `Toast` | Short non-blocking message | info, success, warning, error |
| `ConfirmDialog` | For Kill, Cancel build, Delete | default |

**Task card details:** the lease countdown appears for Claimed and In progress cards and turns amber under 20 seconds and red at expiry. Dragging cards is **not** allowed, because agents choose tasks and the user must not act as a controller. Cards are read-only and open a detail popover on click.

---

## 10. Visual design

### 10.1 Typography

| Use | Font | Size and weight |
| --- | --- | --- |
| UI text | System UI stack (Inter if loaded) | 14 px regular |
| Headings | Same family | 20 / 16 px semibold |
| Log and code | Monospace stack (JetBrains Mono if loaded) | 12.5 px regular |
| Agent label | UI font | 12 px medium |

### 10.2 Layout and spacing

- 4 px base grid. Spacing scale: 4, 8, 12, 16, 24, 32.
- Corner radius 8 px for cards, 999 px for chips and cursor labels.
- Minimum desktop width 1280 px for the full Build view layout (see section 13).

### 10.3 Color tokens

Theme tokens are CSS variables. Values below are defaults and must meet contrast requirements (section 12).

**Role colors**

| Role | Light theme | Dark theme |
| --- | --- | --- |
| UI/UX | `#C026D3` | `#E879F9` |
| Frontend | `#2563EB` | `#60A5FA` |
| Backend | `#16A34A` | `#4ADE80` |
| Database | `#CA8A04` | `#FACC15` |
| Testing | `#EA580C` | `#FB923C` |
| Integration | `#0891B2` | `#22D3EE` |
| Reviewer | `#7C3AED` | `#A78BFA` |

When several agents share a role, they share the color and differ by number in the label and by a small shape marker on the pointer (circle, square, triangle, diamond), so color is not the only identifier.

**Status colors**

| Meaning | Token | Light | Dark |
| --- | --- | --- | --- |
| Success, fix applied | `--ok` | `#15803D` | `#4ADE80` |
| Failure, test failed | `--bad` | `#B91C1C` | `#F87171` |
| Warning, lease low, conflict | `--warn` | `#B45309` | `#FBBF24` |
| Info, running | `--info` | `#1D4ED8` | `#60A5FA` |
| Neutral, idle | `--muted` | `#6B7280` | `#9CA3AF` |

**Signal type colors** (used for pulses and chips): `bug_found` bad, `need_styling` UI/UX color, `needs_review` Reviewer color, `blocked` warn, `conflict` warn, `ready_for_test` Testing color, `visual_mismatch` bad, `help_requested` info.

Surfaces, borders and text colors follow a standard neutral scale per theme. Dark theme is a first-class theme, not an afterthought.

### 10.4 Iconography and imagery

Line icons at 16 and 20 px with a 1.5 px stroke. Each event type in the log has an icon (for example pencil for `file_edit`, flask for `test_run`, warning triangle for `agent_failed`).

### 10.5 Motion

- Durations 150 to 600 ms, ease-out for entrances, ease-in for exits.
- Motion tied to events (section 7.3) is the only motion that conveys swarm activity.
- UI transitions (drawers, dialogs) use 200 ms slide or fade.
- Reduced motion mode removes all non-essential motion (see 7.5 and section 12).

---

## 11. States and error handling

| Situation | UI response |
| --- | --- |
| Model server unreachable (`MODEL_UNAVAILABLE`) | Start screen shows a banner: "The model server is not running. Start Ollama or llama.cpp and try again." with a **Retry** button and a link to Settings > Connection |
| Image invalid (`INVALID_IMAGE`) | Inline message under the drop zone: "That file can't be used. Please upload a PNG, JPEG or WebP image under 10 MB." |
| WebSocket disconnect | Small banner "Reconnecting..." in the top bar. The client reconnects with the last `seq`. After 30 s without success, banner changes to "Connection lost" with **Retry** |
| Build failed | Status chip turns red. Banner shows `failure_reason` in plain language and offers **Rebuild** and **View log** |
| Build timeout | Banner: "The build ran out of time. Partial results are available." with Download and Rebuild |
| Agent failure (real or injected) | Cursor failure animation (7.3), task card warning, toast "Frontend-1 stopped. The task returned to the pool." |
| Preview cannot render | Placeholder with the last successful screenshot and the message "The site doesn't build yet." |
| Empty states | Task board: "No tasks yet. Seeding starts after you press Build." Log: "Events will appear here." Experiments: "No experiments yet. Create one to compare systems." |
| Destructive actions | Kill agent, Cancel build and Delete require a confirmation dialog stating the effect |
| Long operations | Skeleton loaders for lists, determinate progress where possible, otherwise a spinner with text |

Error messages use plain language, state what happened and what the user can do, and never show raw stack traces. A "Details" link reveals the technical error code (for example `TASK_ALREADY_CLAIMED`).

---

## 12. Accessibility

Target: WCAG 2.2 level AA.

| Area | Requirement |
| --- | --- |
| Contrast | Text 4.5:1, large text and UI components 3:1, in both themes |
| Color independence | Roles also have a name and shape marker. Test results show icons and text, not color only. Charts use patterns or direct labels in addition to color |
| Keyboard | All controls reachable by Tab. Visible focus ring (2 px). Shortcuts: Space (replay play/pause), arrow keys (step), `C` (toggle cursors), `L` (focus log), Esc (close drawer or dialog) |
| Cursors | Cursors are a visual layer. The same information is available as text in the Agent list and Log, which are ordinary focusable elements |
| Screen readers | Log is an `aria-live="polite"` region with rate limiting (batched announcements every 3 seconds). Status changes ("Build completed", "Frontend-1 stopped") use `role="status"`. Charts have text summaries and a data table view |
| Motion | Respect `prefers-reduced-motion`. A manual override is in Settings. No flashing above 3 flashes per second (red and green flashes are single, 1 s pulses) |
| Targets | Minimum 24 × 24 px interactive targets (cursor click target enlarged to 32 × 32 px) |
| Text scaling | Layout works at 200% zoom with panels stacking (see section 13) |

---

## 13. Responsive behavior and supported viewports

The builder is designed for desktop and laptop screens (the swarm view needs space).

| Viewport width | Layout |
| --- | --- |
| 1280 px and above | Full Build view as in section 6.2 |
| 1024 to 1279 px | Right column narrows. Log panel collapsed by default. Left rail hidden |
| 768 to 1023 px | Panels become tabs: Preview, Agents, Tasks, Log. Cursors stay on the Preview tab. Agent drawer becomes a bottom sheet |
| Below 768 px | Read-only monitoring: progress, status, agent list, log, scores. Preview is available full screen. Starting experiments is not supported (shows a message to use a larger screen) |

The generated site's own responsiveness is previewed with the viewport switcher (Desktop 1280, Tablet 768, Mobile 375) in the Preview pane.

---

## 14. Content and copy guidelines

- Plain, short, active voice ("Frontend-1 claimed Build hero section").
- Log rows are written from the event: `<time> <agent> <verb> <object>`. Verb mapping: `task_claimed` claimed, `file_edit` edited, `signal_emitted` signaled, `test_run` ran tests, `test_failed` found a failure in, `fix_applied` fixed, `agent_failed` stopped, `agent_recovered` took over from.
- Numbers use consistent units: seconds with one decimal under a minute, `mm:ss` above. Scores 0 to 1 shown to two decimals, Lighthouse 0 to 100 as integers.
- Terminology is consistent: **agent**, **task**, **signal**, **artifact**, **lease**, **build**. Tooltips explain "signal" and "lease" on first use, linking to the glossary.

---

## 15. Performance targets for the interface

| Metric | Target |
| --- | --- |
| Time from pressing Build to first task cards | Under 5 seconds on the target laptop (after the model is loaded) |
| Event to visual latency | Under 300 ms from WebSocket message to cursor update |
| Frame rate with 8 cursors and bursts | 60 fps typical, never below 30 fps |
| Log rendering | Virtualized. Smooth with 10,000 rows |
| Preview reload | Debounced to at most once per second per build |
| Initial load | Under 3 seconds on localhost |

The interface must remain responsive while agents run (non-functional requirement). Heavy work (screenshots, scoring) happens on the server.

---

## 16. Technical notes for implementation

- Stack: React with JavaScript, CSS, SVG for cursors and trails, WebSocket for events (per the technology stack).
- State: one event store keyed by `build_id` holds ordered events by `seq`. Views are derived from that store (agents, tasks, signals, progress). This guarantees that live view and replay behave identically.
- The cursor layer is a pure function of (event store, current time). In replay it uses the replay clock.
- The preview iframe uses `sandbox="allow-scripts"` and a separate origin or path, with no access to the interface's cookies or storage.
- Section lookup uses `postMessage` between the preview and the overlay: a small injected helper reports bounding boxes for `data-swarm-section` elements on load and on resize.

---

## 17. Acceptance criteria

| ID | Criterion | Verifies |
| --- | --- | --- |
| UX1 | A new user enters a prompt and starts a build in under 60 seconds without help | Usability, UC1 |
| UX2 | Every cursor movement in the live view corresponds to an event in the log (checked by replaying the log and comparing cursor paths) | Principle 1, FR9 |
| UX3 | Live view and replay of the same build produce the same cursor positions and section states at the same `seq` | Replay |
| UX4 | Clicking a cursor opens the Agent drawer with current task and the five most recent actions | UC3 |
| UX5 | Screenshot mode shows reference and generated site side by side with a similarity score updating each iteration | UC2, RQ4 |
| UX6 | Killing an agent shows the failure animation, the task returns to Open, a replacement cursor appears, and recovery time is displayed | UC6, RQ3 |
| UX7 | Rebuild creates a new build linked to the original, with the prompt editable | UC4 |
| UX8 | An experiment can be created, run, and exported as CSV and JSON | UC5, FR12 |
| UX9 | All features usable by keyboard only. Automated checks (axe or similar) report no critical issues | Accessibility |
| UX10 | With reduced motion on, no gliding or pulse animations play | Accessibility |
| UX11 | Disconnecting the network for 10 seconds causes a reconnect banner, and the view catches up without duplicated or missing events | Reliability |
| UX12 | The UI remains usable (interactions under 100 ms) while 4 agents are active | Performance |

---

## 18. Traceability

| Use case or requirement | Screen or component | API used |
| --- | --- | --- |
| UC1, FR1 | Start, Build view | `POST /builds`, event WebSocket |
| UC2, FR6 | Start (Screenshot mode), SplitCompare, Scores panel | `POST /builds` (multipart), `GET /scores/visual-history` |
| UC3 | CursorLayer, AgentDrawer | `GET /agents/{id}` |
| UC4, FR10 | Rebuild dialog | `POST /builds/{id}/rebuild` |
| UC5, FR12 | Experiments screens, ChartCard | `/experiments/*` |
| UC6, FR11 | Agent drawer, Inject failure menu | `POST .../inject-failure` |
| FR8, FR9 | LogStream, CursorLayer, ReplayBar | `GET /events`, WebSocket stream |
| FR7 | TaskBoard, SignalChip | `GET /tasks`, `GET /signals` |
| O5 | CursorLayer (section 7) | WebSocket stream |
| O6 | Evaluation dashboard (section 8) | `GET /experiments/{id}/summary` |
| O7 | Recovery timer, failure animations | Events `agent_failed`, `lease_expired`, `agent_recovered` |

---

## 19. Open items for mentor review

1. Confirm whether the Replay preview should rebuild historic project state, or use stored screenshots per iteration (cheaper, less exact).
2. Decide the maximum number of simultaneous cursors displayed (default 8) after testing with real runs.
3. Confirm the page-section convention (`data-swarm-section`) with the agent prompts, since cursor accuracy depends on it.
4. Decide whether to include a Files tab with a code viewer in version 1.0 or leave it for later.
5. Run a quick usability check with 3 to 5 users against UX1 before the final demo.
