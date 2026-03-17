"""
AI visual generation for clipforge.

Generates contextual images via fal.ai Flux Schnell and converts them
to Ken Burns effect video clips. Falls back to gradient color clips
when no FAL_KEY is configured.
"""

import json
import logging
import os
import random
import subprocess
import uuid
from pathlib import Path
from typing import Optional

import requests

from .config import Config, get_config
from .story import _call_llm

log = logging.getLogger("clipforge.visuals")

# ── Cinematic prompt suffixes ────────────────────────────────────────────────

CINEMATIC_SUFFIXES: list[str] = [
    "cinematic lighting, dramatic atmosphere, 4K, photorealistic, film grain",
    "cinematic, moody lighting, ultra detailed, photorealistic, shallow depth of field",
    "dramatic lighting, volumetric fog, photorealistic, cinematic composition, 4K",
    "epic cinematic shot, hyper-realistic, dramatic shadows, professional photography",
    "cinematic wide shot, dramatic golden hour lighting, photorealistic, ultra sharp",
    "dark cinematic tone, high contrast, photorealistic, dramatic chiaroscuro",
    "neon-lit cinematic, cyberpunk atmosphere, ultra detailed, photorealistic",
    "atmospheric fog, cinematic color grading, photorealistic, wide angle lens",
]

# ── Gradient color palettes for fallback clips ───────────────────────────────

GRADIENT_PALETTES: list[tuple[str, str]] = [
    ("0x0b0b2e", "0x1a0a3a"),  # deep indigo
    ("0x1a0000", "0x0a0a2e"),  # dark red to navy
    ("0x001a1a", "0x0a0a2e"),  # teal to navy
    ("0x1a1a00", "0x0a002e"),  # olive to purple
    ("0x0d1117", "0x161b22"),  # github dark
    ("0x0f0c29", "0x302b63"),  # midnight purple
    ("0x000428", "0x004e92"),  # deep ocean
    ("0x1f1c2c", "0x928dab"),  # dusty lavender
]


def _enhance_prompt(scene: str) -> str:
    """Turn a scene description into a cinematic AI image prompt."""
    suffix = random.choice(CINEMATIC_SUFFIXES)
    return (
        f"{scene}, {suffix}. "
        f"No text, no words, no letters, no watermark, no UI elements. "
        f"Portrait orientation 9:16, vertical composition."
    )


# ── Scene prompt extraction ──────────────────────────────────────────────────


def extract_scene_prompts(
    story: str,
    num_scenes: int = 5,
    config: Optional[Config] = None,
) -> list[str]:
    """Use LLM to extract visual scene descriptions from a story.

    Args:
        story: The narrated story text.
        num_scenes: Number of visual scenes to extract.
        config: Configuration instance.

    Returns:
        List of image generation prompt strings.
    """
    config = config or get_config()

    prompt = f"""Extract exactly {num_scenes} visual scenes from this story for AI image generation.

Story:
\"\"\"{story}\"\"\"

Rules:
- Each scene should be a vivid, specific visual description (15-30 words)
- Describe what we SEE, not what we hear or feel
- Include setting, lighting, mood, and key visual elements
- Scenes should flow chronologically through the story
- Make scenes cinematic and dramatic
- NO text, NO people's faces in close-up (avoid uncanny valley)
- Focus on environments, objects, phenomena, wide shots
- If the story mentions a specific place/object, describe it visually

Return ONLY a JSON array of strings, nothing else:
["scene 1 description", "scene 2 description", ...]"""

    try:
        text = _call_llm(prompt, config, max_tokens=1024, temperature=0.6)

        # Handle possible markdown wrapping
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        scenes = json.loads(text)
        if isinstance(scenes, list) and len(scenes) > 0:
            log.info("Extracted %d scene prompts from story", len(scenes))
            return scenes[:num_scenes]
    except (json.JSONDecodeError, IndexError, RuntimeError) as exc:
        log.warning("Scene extraction failed: %s", exc)

    # Fallback: split story into chunks
    words = story.split()
    chunk_size = max(1, len(words) // num_scenes)
    scenes = []
    for i in range(num_scenes):
        chunk = " ".join(words[i * chunk_size : (i + 1) * chunk_size])
        scenes.append(f"cinematic scene depicting: {chunk[:80]}")
    return scenes


# ── AI image generation ──────────────────────────────────────────────────────


def generate_image(
    prompt: str,
    output_path: Path,
    config: Optional[Config] = None,
) -> Path:
    """Generate a portrait image via fal.ai Flux Schnell.

    Args:
        prompt: Image generation prompt.
        output_path: Where to save the PNG image.
        config: Configuration instance.

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If FAL_KEY is not set or generation fails.
    """
    import fal_client

    config = config or get_config()

    if not config.has_fal:
        raise RuntimeError("CLIPFORGE_FAL_KEY not set — cannot generate AI images")

    os.environ["FAL_KEY"] = config.fal_key
    enhanced = _enhance_prompt(prompt)
    log.info("Generating image: %s...", prompt[:60])

    result = fal_client.subscribe(
        "fal-ai/flux/schnell",
        arguments={
            "prompt": enhanced,
            "image_size": {"width": 1080, "height": 1920},
            "num_images": 1,
            "num_inference_steps": 4,
            "enable_safety_checker": False,
        },
    )

    if not result or not result.get("images"):
        raise RuntimeError("fal.ai returned no images")

    image_url = result["images"][0]["url"]
    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)

    size_kb = output_path.stat().st_size // 1024
    log.info("Saved image: %s (%d KB)", output_path.name, size_kb)
    return output_path


# ── Ken Burns effect ─────────────────────────────────────────────────────────


def image_to_clip(
    image_path: Path,
    output_path: Path,
    duration: float = 5.0,
) -> Path:
    """Convert a static image to a video clip with Ken Burns zoom/pan effect.

    Args:
        image_path: Path to the source image.
        output_path: Where to save the MP4 clip.
        duration: Clip duration in seconds.

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If ffmpeg fails.
    """
    fps = 30
    total_frames = int(duration * fps)

    effect = random.choice(["zoom_in", "zoom_out", "pan_right", "pan_left"])

    # Work at 2x resolution internally for smooth sub-pixel movement,
    # then downscale to 1080x1920 at the end.
    canvas_w, canvas_h = 2160, 3840

    # Slow, smooth movements — smaller increments prevent jitter
    zoom_step = 0.0005  # very gradual zoom
    pan_step = 1        # 1px at 2x res = 0.5px at output

    zoompan_filters = {
        "zoom_in": (
            f"zoompan=z='min(zoom+{zoom_step},1.12)'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={canvas_w}x{canvas_h}:fps={fps}"
        ),
        "zoom_out": (
            f"zoompan=z='if(eq(on,1),1.12,max(zoom-{zoom_step},1.0))'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={canvas_w}x{canvas_h}:fps={fps}"
        ),
        "pan_right": (
            f"zoompan=z='1.08'"
            f":x='if(eq(on,1),0,min(x+{pan_step},iw-iw/zoom))'"
            f":y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={canvas_w}x{canvas_h}:fps={fps}"
        ),
        "pan_left": (
            f"zoompan=z='1.08'"
            f":x='if(eq(on,1),iw-iw/zoom,max(x-{pan_step},0))'"
            f":y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s={canvas_w}x{canvas_h}:fps={fps}"
        ),
    }

    zoompan = zoompan_filters[effect]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Upscale image first for clean zoompan, then downscale to 1080x1920
    vf = f"scale=2160:3840:flags=lanczos,{zoompan},scale=1080:1920:flags=lanczos"

    cmd = [
        "nice", "-n", "15", "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "20",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg zoompan failed: {result.stderr[-500:]}")

    log.info("Ken Burns clip: %s (%.1fs, %s)", output_path.name, duration, effect)
    return output_path


# ── Fallback gradient clip ───────────────────────────────────────────────────


def _generate_gradient_clip(output_path: Path, duration: float = 5.0) -> Path:
    """Generate a solid gradient color clip as fallback when no FAL_KEY."""
    c0, c1 = random.choice(GRADIENT_PALETTES)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c={c0}:s=1080x1920:d={duration}:r=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "23",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg gradient clip failed: {result.stderr[-500:]}")

    log.info("Gradient clip: %s (%.1fs)", output_path.name, duration)
    return output_path


# ── Main orchestrator ────────────────────────────────────────────────────────


def generate_clips(
    story: str,
    output_dir: Path,
    num_clips: int = 5,
    ai_ratio: float = 1.0,
    config: Optional[Config] = None,
) -> list[Path]:
    """Generate video clips for a story.

    Uses AI-generated images (via fal.ai) when available, falling back
    to solid gradient clips otherwise.

    Args:
        story: The narrated story text.
        output_dir: Directory to save generated clips.
        num_clips: Total number of clips to generate.
        ai_ratio: Fraction of clips to generate as AI (0.0-1.0).
        config: Configuration instance.

    Returns:
        Ordered list of clip paths (MP4).
    """
    config = config or get_config()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    use_ai = config.has_fal and ai_ratio > 0
    n_ai = max(1, int(num_clips * ai_ratio)) if use_ai else 0

    # Extract scene prompts if using AI
    scene_prompts: list[str] = []
    if use_ai:
        try:
            scene_prompts = extract_scene_prompts(story, num_scenes=n_ai, config=config)
        except Exception as exc:
            log.warning("Scene extraction failed: %s", exc)

    ai_slots = set(random.sample(range(num_clips), min(n_ai, num_clips)))
    clips: list[Path] = []
    ai_idx = 0

    for i in range(num_clips):
        duration = random.uniform(3.5, 6.0)
        uid = uuid.uuid4().hex[:6]

        if i in ai_slots and ai_idx < len(scene_prompts):
            # Try AI generation
            try:
                prompt = scene_prompts[ai_idx]
                img_path = output_dir / f"ai_img_{i:02d}_{uid}.png"
                clip_path = output_dir / f"ai_clip_{i:02d}_{uid}.mp4"

                generate_image(prompt, img_path, config=config)
                image_to_clip(img_path, clip_path, duration=duration)

                # Clean up raw image
                img_path.unlink(missing_ok=True)
                clips.append(clip_path)
                ai_idx += 1
                log.info("Clip %d/%d: AI generated", i + 1, num_clips)
                continue
            except Exception as exc:
                log.warning("AI clip %d failed: %s — using fallback", i + 1, exc)

        # Fallback: gradient clip
        clip_path = output_dir / f"gradient_clip_{i:02d}_{uid}.mp4"
        _generate_gradient_clip(clip_path, duration=duration)
        clips.append(clip_path)
        log.info("Clip %d/%d: gradient fallback", i + 1, num_clips)

    ai_count = sum(1 for c in clips if "ai_clip" in c.name)
    log.info("Generated %d AI + %d fallback clips", ai_count, len(clips) - ai_count)
    return clips
