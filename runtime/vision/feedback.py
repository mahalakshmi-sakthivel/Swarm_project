"""
Vision Feedback Loop Orchestrator (Stage 5).
Automates the visual inspection loop:
Render Sandbox -> Capture Viewport -> Compute SSIM & Perceptual Difference
-> Emit Visual Signals -> Synthesize Targeted Style/Structure Repair Tasks.
"""

import logging
from pathlib import Path
from typing import Optional

from runtime.blackboard import Blackboard, Task
from runtime.events import EventLog
from runtime.sandbox import Sandbox
from runtime.vision.capture import ScreenshotCapture
from runtime.vision.similarity import VisualDiffResult, VisualSimilarityScorer

logger = logging.getLogger("runtime.vision.feedback")


class VisionFeedbackLoop:
    """Automated vision evaluation and iterative repair loop."""

    def __init__(
        self,
        runs_dir: str | Path,
        convergence_threshold: float = 0.85,
        max_iterations: int = 5,
        browser_path: Optional[str] = None,
    ):
        self.runs_dir = Path(runs_dir)
        self.convergence_threshold = convergence_threshold
        self.max_iterations = max_iterations
        self.capturer = ScreenshotCapture(browser_path=browser_path)
        self.scorer = VisualSimilarityScorer(convergence_threshold=convergence_threshold)

    def run_iteration(
        self,
        run_id: str,
        blackboard: Blackboard,
        event_log: EventLog,
        sandbox: Sandbox,
        reference_image_path: str | Path,
        iteration: int = 1,
    ) -> VisualDiffResult:
        """
        Execute one complete vision feedback cycle for an active swarm run.
        """
        ref_path = Path(reference_image_path)
        if not ref_path.exists():
            raise FileNotFoundError(f"Reference image path does not exist: {ref_path}")

        run_vision_dir = self.runs_dir / run_id / "vision"
        run_vision_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = run_vision_dir / f"screenshot_iter_{iteration}.png"
        diff_path = run_vision_dir / f"diff_iter_{iteration}.png"

        # 1. Verify that HTML exists in sandbox
        if not sandbox.file_exists("index.html"):
            logger.warning(f"Run '{run_id}' has no index.html yet; skipping vision capture.")
            return VisualDiffResult(
                ssim_score=0.0,
                phash_score=0.0,
                composite_score=0.0,
                converged=False,
                threshold=self.convergence_threshold,
                recommendations=["index.html not generated yet"],
            )

        # 2. Capture Headless Screenshot of Sandbox
        html_abs_path = sandbox.sandbox_dir / "index.html"
        self.capturer.capture(
            target=html_abs_path,
            output_path=screenshot_path,
            width=1280,
            height=800,
        )

        # 3. Compute Visual Similarity & Difference Heatmap
        diff_result = self.scorer.compare(
            reference_image_path=ref_path,
            candidate_image_path=screenshot_path,
            diff_output_path=diff_path,
        )

        logger.info(
            f"Vision Iteration {iteration} for '{run_id}': Composite Score = "
            f"{diff_result.composite_score:.3f} (SSIM: {diff_result.ssim_score:.3f}, "
            f"pHash: {diff_result.phash_score:.3f}, Converged: {diff_result.converged})"
        )

        # 4. Record Vision Audit Event
        event_log.append(
            run_id=run_id,
            agent_id="agent-qa-01",
            event_type="test_run",
            target="vision",
            payload={
                "iteration": iteration,
                "metric": "visual_similarity",
                "composite_score": round(diff_result.composite_score, 4),
                "ssim": round(diff_result.ssim_score, 4),
                "phash": round(diff_result.phash_score, 4),
                "converged": diff_result.converged,
                "screenshot": str(screenshot_path.name),
                "diff_map": str(diff_path.name),
                "mismatches": diff_result.mismatched_regions,
            },
        )

        # 5. Check Convergence Criteria
        if diff_result.converged:
            logger.info(f"Swarm reached visual convergence on iteration {iteration}!")
            blackboard.emit_signal(
                run_id=run_id,
                sig_type="visual_alignment_passed",
                target="sandbox",
                emitter="agent-qa-01",
                initial_strength=1.0,
            )
            return diff_result

        # 6. If Not Converged, Emit Defect Signals and Targeted Repair Tasks
        logger.info(f"Visual mismatch detected; emitting signals and generating repair tasks...")
        blackboard.emit_signal(
            run_id=run_id,
            sig_type="visual_mismatch",
            target="styles.css",
            emitter="agent-qa-01",
            initial_strength=0.9,
        )

        recs_summary = " | ".join(diff_result.recommendations[:3])

        # Style repair task
        style_task_id = f"task-vision-style-iter-{iteration}"
        blackboard.add_task(
            Task(
                id=style_task_id,
                run_id=run_id,
                title=f"Visual Alignment: CSS Theme & Layout Refinement (Iter {iteration})",
                description=(
                    f"Visual similarity ({diff_result.composite_score:.2f}) is below target "
                    f"({self.convergence_threshold:.2f}). Required fixes: {recs_summary}"
                ),
                role_hint="style",
                status="open",
                priority=10,  # Highest priority to fix immediately
                target="styles.css",
            )
        )

        # If navigation or structure is misaligned, also spawn structure repair task
        if any(r.get("section") == "header_navigation" for r in diff_result.mismatched_regions):
            struct_task_id = f"task-vision-structure-iter-{iteration}"
            blackboard.add_task(
                Task(
                    id=struct_task_id,
                    run_id=run_id,
                    title=f"Visual Alignment: HTML Structure & Navigation (Iter {iteration})",
                    description=(
                        "Header and navigation elements differ from reference mockup. "
                        "Reorganize header containers and semantic link tags."
                    ),
                    role_hint="structure",
                    status="open",
                    priority=9,
                    target="index.html",
                )
            )

        return diff_result
