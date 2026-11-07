"""
Visual Similarity Scorer and Difference Detection (Stage 5).
Computes Structural Similarity Index (SSIM), Perceptual Hash (pHash),
and generates visual difference heatmaps with section defect localization.
"""

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import imagehash
import numpy as np
from PIL import Image, ImageChops, ImageDraw

logger = logging.getLogger("runtime.vision.similarity")


@dataclass
class VisualDiffResult:
    """Detailed visual comparison metrics and defect localization."""
    ssim_score: float
    phash_score: float
    composite_score: float
    converged: bool
    threshold: float
    mismatched_regions: List[Dict[str, Any]] = field(default_factory=list)
    diff_image_path: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ssim_score": round(self.ssim_score, 4),
            "phash_score": round(self.phash_score, 4),
            "composite_score": round(self.composite_score, 4),
            "converged": self.converged,
            "threshold": self.threshold,
            "mismatched_regions_count": len(self.mismatched_regions),
            "diff_image_path": self.diff_image_path,
            "recommendations": self.recommendations,
        }


class VisualSimilarityScorer:
    """Multi-metric image similarity and visual defect detection engine."""

    def __init__(
        self,
        target_size: Tuple[int, int] = (1280, 800),
        convergence_threshold: float = 0.85,
        ssim_weight: float = 0.60,
        phash_weight: float = 0.40,
    ):
        self.target_size = target_size
        self.convergence_threshold = convergence_threshold
        self.ssim_weight = ssim_weight
        self.phash_weight = phash_weight

    def compare(
        self,
        reference_image_path: str | Path,
        candidate_image_path: str | Path,
        diff_output_path: Optional[str | Path] = None,
    ) -> VisualDiffResult:
        """
        Compare a reference mockup image against a generated screenshot.
        Computes SSIM, perceptual hash, detects mismatched regions,
        and optionally exports a visual difference comparison image.
        """
        ref_path = Path(reference_image_path)
        cand_path = Path(candidate_image_path)

        if not ref_path.exists():
            raise FileNotFoundError(f"Reference image not found: {ref_path}")
        if not cand_path.exists():
            raise FileNotFoundError(f"Candidate image not found: {cand_path}")

        # 1. Open and resize images to standard target viewport
        with Image.open(ref_path) as ref_raw, Image.open(cand_path) as cand_raw:
            ref_rgb = ref_raw.convert("RGB").resize(self.target_size, Image.Resampling.BILINEAR)
            cand_rgb = cand_raw.convert("RGB").resize(self.target_size, Image.Resampling.BILINEAR)

        # 2. Compute Structural Similarity Index (SSIM)
        ssim = self._compute_ssim(ref_rgb, cand_rgb)

        # 3. Compute Perceptual Hash (pHash)
        phash = self._compute_phash_similarity(ref_rgb, cand_rgb)

        # 4. Compute Weighted Composite Score
        composite = (self.ssim_weight * ssim) + (self.phash_weight * phash)
        composite = max(0.0, min(1.0, composite))
        converged = composite >= self.convergence_threshold

        # 5. Detect Mismatched Regions and Generate Diff Heatmap
        regions, diff_saved_path = self._generate_diff_and_regions(
            ref_rgb, cand_rgb, diff_output_path
        )

        # 6. Generate Actionable Feedback Recommendations
        recommendations = self._generate_recommendations(ssim, phash, regions)

        return VisualDiffResult(
            ssim_score=ssim,
            phash_score=phash,
            composite_score=composite,
            converged=converged,
            threshold=self.convergence_threshold,
            mismatched_regions=regions,
            diff_image_path=str(diff_saved_path) if diff_saved_path else None,
            recommendations=recommendations,
        )

    @staticmethod
    def _compute_ssim(img1: Image.Image, img2: Image.Image) -> float:
        """
        Calculate Mean Structural Similarity Index (SSIM) on luminance channel.
        Wang et al. (2004) formulation with 8x8 block pooling.
        """
        gray1 = np.array(img1.convert("L"), dtype=np.float64)
        gray2 = np.array(img2.convert("L"), dtype=np.float64)

        k1 = 0.01
        k2 = 0.03
        l = 255.0
        c1 = (k1 * l) ** 2
        c2 = (k2 * l) ** 2

        # Block-based mean and variance estimation
        block_size = 16
        h, w = gray1.shape
        num_h = h // block_size
        num_w = w // block_size

        if num_h == 0 or num_w == 0:
            # Fallback for small images
            mu1 = np.mean(gray1)
            mu2 = np.mean(gray2)
            sigma1_sq = np.var(gray1)
            sigma2_sq = np.var(gray2)
            sigma12 = np.cov(gray1.flatten(), gray2.flatten())[0, 1]
            return float(((2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)) / ((mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2)))

        ssim_blocks = []
        for i in range(num_h):
            for j in range(num_w):
                b1 = gray1[i * block_size : (i + 1) * block_size, j * block_size : (j + 1) * block_size]
                b2 = gray2[i * block_size : (i + 1) * block_size, j * block_size : (j + 1) * block_size]

                mu1 = np.mean(b1)
                mu2 = np.mean(b2)
                sigma1_sq = np.var(b1)
                sigma2_sq = np.var(b2)
                sigma12 = np.mean((b1 - mu1) * (b2 - mu2))

                numerator = (2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)
                denominator = (mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2)
                ssim_blocks.append(numerator / denominator)

        mean_ssim = float(np.mean(ssim_blocks))
        return max(0.0, min(1.0, mean_ssim))

    @staticmethod
    def _compute_phash_similarity(img1: Image.Image, img2: Image.Image) -> float:
        """
        Compute normalized perceptual hash similarity using 64-bit DCT pHash.
        Returns value in range [0.0, 1.0].
        """
        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)
        hamming_dist = hash1 - hash2
        # Max distance for 64-bit hash is 64
        similarity = 1.0 - (hamming_dist / 64.0)
        return max(0.0, min(1.0, float(similarity)))

    def _generate_diff_and_regions(
        self,
        ref_img: Image.Image,
        cand_img: Image.Image,
        diff_output_path: Optional[str | Path],
    ) -> Tuple[List[Dict[str, Any]], Optional[Path]]:
        """
        Compute pixel difference mask, group into bounding box defect clusters,
        and optionally composite a 3-column [Reference | Generated | Diff Heatmap] canvas.
        """
        diff = ImageChops.difference(ref_img, cand_img)
        diff_gray = diff.convert("L")
        diff_np = np.array(diff_gray)

        # Threshold difference: pixels differing by > 32 in intensity
        threshold = 32
        mask = diff_np > threshold

        # Group difference into 4 vertical zones (Header, Hero, Body, Footer)
        h, w = mask.shape
        zone_h = h // 4
        zone_names = ["header_navigation", "hero_section", "body_content", "footer_contact"]
        regions = []

        for z_idx, name in enumerate(zone_names):
            zone_slice = mask[z_idx * zone_h : (z_idx + 1) * zone_h, :]
            diff_ratio = float(np.mean(zone_slice))
            if diff_ratio > 0.08:  # More than 8% mismatched pixels in this quadrant
                regions.append({
                    "section": name,
                    "zone_y_range": [z_idx * zone_h, (z_idx + 1) * zone_h],
                    "mismatch_ratio": round(diff_ratio, 3),
                    "severity": "high" if diff_ratio > 0.25 else "medium",
                })

        diff_path = None
        if diff_output_path:
            diff_path = Path(diff_output_path)
            diff_path.parent.mkdir(parents=True, exist_ok=True)

            # Create side-by-side composite: [Reference | Generated | Diff Map]
            target_w, target_h = self.target_size
            composite_w = target_w * 3
            composite_h = target_h + 40

            canvas = Image.new("RGB", (composite_w, composite_h), color="#090d16")
            canvas.paste(ref_img, (0, 40))
            canvas.paste(cand_img, (target_w, 40))

            # Colorize diff heatmap in high-contrast red/magenta
            heatmap_np = np.zeros((target_h, target_w, 3), dtype=np.uint8)
            heatmap_np[mask] = [232, 121, 249]  # Bright magenta difference pixels
            heatmap_img = Image.fromarray(heatmap_np)
            diff_blended = Image.blend(cand_img, heatmap_img, alpha=0.6)
            canvas.paste(diff_blended, (target_w * 2, 40))

            # Add header labels
            draw = ImageDraw.Draw(canvas)
            draw.text((20, 12), "REFERENCE MOCKUP", fill="#60a5fa")
            draw.text((target_w + 20, 12), "GENERATED PREVIEW", fill="#4ade80")
            draw.text((target_w * 2 + 20, 12), "VISUAL DIFFERENCE HEATMAP", fill="#e879f9")

            canvas.save(str(diff_path), "PNG")

        return regions, diff_path

    @staticmethod
    def _generate_recommendations(
        ssim: float, phash: float, regions: List[Dict[str, Any]]
    ) -> List[str]:
        """Produce concrete repair directives for Style and Structure agents."""
        recs = []
        if ssim < 0.70:
            recs.append("Structural layout mismatch: Check container flex/grid alignment, margin gutters, and semantic hierarchy.")
        if phash < 0.75:
            recs.append("Color palette and visual tone mismatch: Adjust dark theme background tokens, card borders, and accent contrast.")

        for r in regions:
            sec = r["section"]
            ratio_pct = int(r["mismatch_ratio"] * 100)
            if sec == "header_navigation":
                recs.append(f"Header: {ratio_pct}% visual divergence. Verify logo placement, navbar link spacing, and header height.")
            elif sec == "hero_section":
                recs.append(f"Hero section: {ratio_pct}% visual divergence. Adjust headline font-size, subtitle padding, and call-to-action button styling.")
            elif sec == "body_content":
                recs.append(f"Body content: {ratio_pct}% visual divergence. Realign cards grid, skills badges, and project showcase layout.")
            elif sec == "footer_contact":
                recs.append(f"Footer section: {ratio_pct}% visual divergence. Align footer columns, social link badges, and bottom padding.")

        if not recs:
            recs.append("Visual appearance aligns closely with the reference design.")
        return recs

