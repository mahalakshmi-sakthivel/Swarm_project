"""
Vision Feedback Loop & Image-to-Code Package (Stage 5).
Provides headless screenshot capture, visual similarity scoring (SSIM & Perceptual Hash),
difference detection, and automated iterative refinement loops.
"""

from runtime.vision.capture import ScreenshotCapture
from runtime.vision.similarity import VisualSimilarityScorer, VisualDiffResult
from runtime.vision.feedback import VisionFeedbackLoop

__all__ = [
    "ScreenshotCapture",
    "VisualSimilarityScorer",
    "VisualDiffResult",
    "VisionFeedbackLoop",
]

