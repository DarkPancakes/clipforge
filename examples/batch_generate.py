#!/usr/bin/env python3
"""
Batch video generation example for clipforge.

Generates multiple short-form videos across different styles and topics.

Prerequisites:
  - pip install clipforge
  - ffmpeg installed
  - CLIPFORGE_LLM_KEY set (for story generation)
  - CLIPFORGE_FAL_KEY set (optional, for AI visuals)
"""

import logging
import time
from pathlib import Path

from clipforge import generate_short
from clipforge.config import Config
from clipforge.story import list_styles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("batch")

# ── Configuration ────────────────────────────────────────────────────────────

OUTPUT_DIR = Path("output/batch")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define batch jobs: (topic, style, voice)
JOBS = [
    ("lightning", "mind_blowing", "andrew"),
    ("black holes", "space", "ryan"),
    ("sleep paralysis", "psychology", "sonia"),
    ("deep sea anglerfish", "ocean_deep", "brian"),
    ("the placebo effect", "body_facts", "emma"),
    ("chocolate origins", "food_origins", "jenny"),
    ("flat earth", "myth_busted", "davis"),
    ("quantum computing", "future_tech", "guy"),
]


def main() -> None:
    """Run batch generation."""
    log.info("Starting batch generation: %d videos", len(JOBS))
    log.info("Available styles: %s", ", ".join(sorted(list_styles().keys())))

    results = []
    for i, (topic, style, voice) in enumerate(JOBS, 1):
        output_path = OUTPUT_DIR / f"{style}_{topic.replace(' ', '_')}.mp4"
        log.info("─" * 60)
        log.info("[%d/%d] Generating: %s (%s)", i, len(JOBS), topic, style)

        start = time.time()
        try:
            video = generate_short(
                topic=topic,
                style=style,
                voice=voice,
                output=str(output_path),
                num_clips=4,
            )
            elapsed = time.time() - start
            size_mb = video.stat().st_size / 1024 / 1024
            results.append((topic, style, True, elapsed, size_mb))
            log.info("Done: %s (%.1fs, %.1f MB)", video.name, elapsed, size_mb)
        except Exception as exc:
            elapsed = time.time() - start
            results.append((topic, style, False, elapsed, 0))
            log.error("Failed: %s — %s (%.1fs)", topic, exc, elapsed)

    # Summary
    log.info("=" * 60)
    log.info("BATCH COMPLETE")
    log.info("=" * 60)
    success = sum(1 for r in results if r[2])
    log.info("Success: %d/%d", success, len(results))
    for topic, style, ok, elapsed, size in results:
        status = "OK" if ok else "FAIL"
        log.info("  [%s] %s (%s) — %.1fs, %.1f MB", status, topic, style, elapsed, size)


if __name__ == "__main__":
    main()
