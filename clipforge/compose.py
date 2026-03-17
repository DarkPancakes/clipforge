"""
FFmpeg video composition for clipforge.

Concatenates video clips, mixes voice + optional background music,
burns in ASS subtitles, and outputs a 1080x1920 H.264 MP4 ready
for YouTube Shorts / TikTok.
"""

import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Optional

log = logging.getLogger("clipforge.compose")


def _get_duration(media_path: Path) -> float:
    """Probe a media file and return its duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(media_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {media_path}: {result.stderr[-300:]}")
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def compose_video(
    clips: list[Path],
    audio: Path,
    subs: Path,
    output: Path,
    music: Optional[Path] = None,
    voice_vol: float = 0.85,
    music_vol: float = 0.08,
) -> Path:
    """Compose the final short-form video.

    Concatenates clips (looping to fill audio duration), scales to
    1080x1920 with crop (no black bars), mixes voice audio with
    optional background music, and burns in ASS subtitles.

    Args:
        clips: Ordered list of video clip paths.
        audio: Path to the voice narration audio file.
        subs: Path to the ASS subtitle file.
        output: Where to save the final MP4.
        music: Optional background music file (will be looped and mixed).
        voice_vol: Voice volume multiplier (default 0.85).
        music_vol: Music volume multiplier (default 0.08).

    Returns:
        The output path on success.

    Raises:
        RuntimeError: If ffmpeg fails or no clips are provided.
    """
    if not clips:
        raise RuntimeError("No video clips provided for composition")

    clips = [Path(c) for c in clips]
    audio = Path(audio)
    subs = Path(subs)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Get audio duration
    audio_dur = _get_duration(audio)
    duration = audio_dur + 1.0  # 1s padding

    log.info(
        "Composing video: %d clips, %.1fs audio, output=%s",
        len(clips), audio_dur, output.name,
    )

    # Build concat file (loop clips to fill duration)
    total_vid = 0.0
    for clip in clips:
        total_vid += _get_duration(clip)

    loops_needed = int(duration / total_vid) + 2 if total_vid > 0 else 1

    concat_file = Path(f"/tmp/clipforge_concat_{uuid.uuid4().hex[:8]}.txt")
    with open(concat_file, "w") as f:
        for _ in range(loops_needed):
            for clip in clips:
                f.write(f"file '{clip.resolve()}'\n")

    try:
        # Build ffmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-i", str(audio),
        ]

        if music:
            cmd += ["-stream_loop", "-1", "-i", str(music)]

        cmd += ["-t", str(duration)]

        # Escape subtitle path for ffmpeg filter
        subs_escaped = (
            str(subs.resolve())
            .replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
        )

        vf = (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"ass={subs_escaped}"
        )

        if music:
            cmd += [
                "-filter_complex",
                (
                    f"[0:v]{vf}[vout];"
                    f"[1:a]volume={voice_vol}[voice];"
                    f"[2:a]volume={music_vol}[music];"
                    f"[voice][music]amix=inputs=2:duration=first[aout]"
                ),
                "-map", "[vout]",
                "-map", "[aout]",
            ]
        else:
            cmd += [
                "-vf", vf,
                "-af", f"volume={voice_vol}",
                "-map", "0:v",
                "-map", "1:a",
            ]

        cmd += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-movflags", "+faststart",
            "-r", "30",
            "-pix_fmt", "yuv420p",
            str(output),
        ]

        log.debug("FFmpeg command: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {proc.stderr[-500:]}")

        size_mb = output.stat().st_size / 1024 / 1024
        log.info("Video composed: %s (%.1f MB, %.1fs)", output.name, size_mb, duration)
        return output

    finally:
        concat_file.unlink(missing_ok=True)
