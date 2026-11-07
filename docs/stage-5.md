# Stage 5: Vision Feedback Loop & Image-to-Code

## 1. Overview
Stage 5 introduces the automated visual critique and repair engine, closing the loop between reference design mockups and sandboxed code execution. By taking headless browser screenshots of the live preview, computing Structural Similarity (SSIM) and Perceptual Hashing (pHash), and localizing visual defects, the swarm autonomously refines HTML layouts, dark theme CSS styling, and spacing until visual convergence is achieved.

### Key Architecture Components:
1. **Headless Browser Screenshot Engine ([`runtime/vision/capture.py`](file:///D:/swarm%20technology/runtime/vision/capture.py))**:
   - Class: `ScreenshotCapture`.
   - Automatically detects system Chromium installations on Windows (`C:\Program Files\Google\Chrome\Application\chrome.exe`, `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`, or PATH).
   - Executes headless rendering with isolated temporary profile: `--headless=new --disable-gpu --no-sandbox --hide-scrollbars --user-data-dir={tmp} --screenshot={output_path} --window-size=1280,800`.
   - Includes a deterministic PIL synthetic fallback engine for headless-restricted environments or continuous integration (CI) runners without a physical display server.

2. **Multi-Metric Similarity Scorer & Difference Detection ([`runtime/vision/similarity.py`](file:///D:/swarm%20technology/runtime/vision/similarity.py))**:
   - Class: `VisualSimilarityScorer`.
   - **Structural Similarity (SSIM)**: Implements Wang et al. (2004) luminance, contrast, and structure pooling across resized $1280 \times 800$ image blocks ($[0.0, 1.0]$).
   - **Perceptual Hash (pHash)**: 64-bit DCT perceptual hash comparing Hamming distance ($1.0 - (\text{dist} / 64.0)$).
   - **Composite Metric**:
     $$\text{Composite Score} = 0.60 \times \text{SSIM} + 0.40 \times \text{pHash}$$
   - **Visual Diff Heatmap**: Computes pixel-level difference masks ($|A - B| > 32$), overlays glowing magenta discrepancy markers, and groups defects into 4 vertical layout quadrants (`header_navigation`, `hero_section`, `body_content`, `footer_contact`).
   - Generates side-by-side composite comparison artifacts: `[REFERENCE MOCKUP | GENERATED PREVIEW | VISUAL DIFFERENCE HEATMAP]`.
   - Produces structured recommendations for Style and Structure agents.

3. **Vision Feedback Loop Orchestrator ([`runtime/vision/feedback.py`](file:///D:/swarm%20technology/runtime/vision/feedback.py))**:
   - Class: `VisionFeedbackLoop`.
   - Manages iteration cycles ($1 \dots \text{max\_iterations}$, default 5).
   - Emits `test_run` audit events to the append-only event log with composite scores, SSIM, pHash, and defect lists.
   - When $\text{score} < \text{threshold}$ (default $0.85$):
     - Emits `visual_mismatch` signal on `styles.css`.
     - Automatically synthesizes targeted repair tasks on the blackboard (e.g. `task-vision-style-iter-N` with priority 10, and `task-vision-structure-iter-N` with priority 9).
   - When $\text{score} \ge \text{threshold}$:
     - Emits `visual_alignment_passed` signal and marks visual convergence.

4. **Swarm Convergence Integration ([`runtime/swarm.py`](file:///D:/swarm%20technology/runtime/swarm.py))**:
   - When `reference_image` is provided in the goal, the swarm convergence gate validates both code QA tests and visual similarity before declaring convergence.

5. **API & Static Preview Routes ([`api/server.py`](file:///D:/swarm%20technology/api/server.py))**:
   - `GET /runs/{run_id}/vision/{filename}`: Serves iteration screenshots and diff heatmaps directly.
   - `GET /runs/{run_id}`: Reports list of generated vision assets alongside blackboard tasks and QA scores.

---

## 2. Test Verification

### Test Suite Execution
- `tests/test_vision_capture.py`:
  - `test_screenshot_capture_initialization`: PASSED
  - `test_capture_html_file`: PASSED
  - `test_capture_nonexistent_file_raises_error`: PASSED
- `tests/test_vision_similarity.py`:
  - `test_identical_images_similarity`: PASSED (SSIM > 0.99, pHash = 1.0, composite > 0.99)
  - `test_minor_variation_similarity`: PASSED (0.80 <= composite < 1.0)
  - `test_divergent_images_similarity`: PASSED (composite < 0.60, diff map generated)
  - `test_missing_image_file_handling`: PASSED
- `tests/test_vision_feedback_loop.py`:
  - `test_vision_loop_mismatch_creates_repair_tasks`: PASSED (emits `visual_mismatch`, spawns `task-vision-style-iter-1` with priority 10)
  - `test_vision_loop_convergence_on_matching_reference`: PASSED (emits `visual_alignment_passed`, score >= 0.85)

**Total Test Suite Status: 43/43 tests passing** across entire project repository.
