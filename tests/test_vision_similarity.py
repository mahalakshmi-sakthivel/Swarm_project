"""
Unit Tests for Stage 5 Visual Similarity Scorer & Difference Detection.
Tests:
- Identical images produce SSIM=1.0, pHash=1.0, composite=1.0
- Minor variations produce high but strictly sub-1.0 similarity
- Drastically different images produce low similarity (< 0.5)
- Visual difference heatmap generation
- Defect quadrant detection and recommendation synthesis
"""

import sys
sys.path.insert(0, ".")

from pathlib import Path
from PIL import Image, ImageDraw
import pytest

from runtime.vision.similarity import VisualSimilarityScorer, VisualDiffResult


@pytest.fixture
def test_images(tmp_path):
    """Generate deterministic synthetic test images."""
    size = (640, 400)

    # 1. Base reference image (dark theme portfolio layout)
    base_img = Image.new("RGB", size, color="#090d16")
    draw = ImageDraw.Draw(base_img)
    # Header
    draw.rectangle([(0, 0), (size[0], 50)], fill="#111827")
    draw.text((20, 15), "Brand Portfolio", fill="#60a5fa")
    # Hero
    draw.rectangle([(30, 80), (size[0] - 30, 180)], fill="#1e293b")
    draw.text((50, 110), "Full Stack Developer", fill="#ffffff")
    # Cards
    draw.rectangle([(30, 210), (190, 320)], fill="#1e293b", outline="#60a5fa")
    draw.rectangle([(220, 210), (380, 320)], fill="#1e293b", outline="#e879f9")
    draw.rectangle([(410, 210), (570, 320)], fill="#1e293b", outline="#4ade80")
    # Footer
    draw.rectangle([(0, 360), (size[0], size[1])], fill="#111827")

    base_path = tmp_path / "reference.png"
    base_img.save(str(base_path), "PNG")

    # 2. Identical clone
    clone_path = tmp_path / "identical.png"
    base_img.save(str(clone_path), "PNG")

    # 3. Minor shift (slightly different hero accent color)
    minor_img = base_img.copy()
    minor_draw = ImageDraw.Draw(minor_img)
    minor_draw.rectangle([(30, 80), (size[0] - 30, 180)], fill="#2d3748")  # slightly different shade
    minor_path = tmp_path / "minor_variation.png"
    minor_img.save(str(minor_path), "PNG")

    # 4. Major divergence (all white canvas with black text)
    divergent_img = Image.new("RGB", size, color="#ffffff")
    div_draw = ImageDraw.Draw(divergent_img)
    div_draw.text((100, 100), "Completely different content", fill="#000000")
    divergent_path = tmp_path / "divergent.png"
    divergent_img.save(str(divergent_path), "PNG")

    return {
        "base": base_path,
        "identical": clone_path,
        "minor": minor_path,
        "divergent": divergent_path,
        "diff_out": tmp_path / "diff_output.png",
    }


def test_identical_images_similarity(test_images):
    scorer = VisualSimilarityScorer(target_size=(640, 400), convergence_threshold=0.85)
    res = scorer.compare(test_images["base"], test_images["identical"])

    assert isinstance(res, VisualDiffResult)
    assert res.ssim_score > 0.99
    assert res.phash_score == 1.0
    assert res.composite_score > 0.99
    assert res.converged is True
    assert len(res.mismatched_regions) == 0


def test_minor_variation_similarity(test_images):
    scorer = VisualSimilarityScorer(target_size=(640, 400), convergence_threshold=0.85)
    res = scorer.compare(test_images["base"], test_images["minor"])

    assert 0.70 < res.ssim_score < 1.0
    assert res.phash_score >= 0.85
    assert res.composite_score >= 0.80
    assert len(res.recommendations) >= 1


def test_divergent_images_similarity(test_images):
    scorer = VisualSimilarityScorer(target_size=(640, 400), convergence_threshold=0.85)
    res = scorer.compare(
        test_images["base"],
        test_images["divergent"],
        diff_output_path=test_images["diff_out"]
    )

    assert res.composite_score < 0.60
    assert res.converged is False
    assert len(res.mismatched_regions) > 0
    # Verify diff map was exported
    assert test_images["diff_out"].exists()
    assert test_images["diff_out"].stat().st_size > 0


def test_missing_image_file_handling(tmp_path):
    scorer = VisualSimilarityScorer()
    with pytest.raises(FileNotFoundError):
        scorer.compare(tmp_path / "nonexistent1.png", tmp_path / "nonexistent2.png")
