"""
Text-to-speech integration for clipforge.

Uses Microsoft Edge TTS (free, no API key required) with 16+ natural
voices and word-level timestamp extraction for subtitle sync.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import edge_tts

from .config import VOICES, Config, get_config

log = logging.getLogger("clipforge.voice")

# ── Word timestamp data type ─────────────────────────────────────────────────

WordTiming = dict  # {"text": str, "start": float, "duration": float}


# ── Core TTS generation ─────────────────────────────────────────────────────


async def _generate_tts(
    text: str,
    output_path: Path,
    voice: str = "en-US-AndrewMultilingualNeural",
    rate: str = "-8%",
    pitch: str = "-3Hz",
) -> list[WordTiming]:
    """Generate TTS audio with word-level timestamps via Edge TTS.

    Args:
        text: The text to synthesize.
        output_path: Where to save the MP3 audio file.
        voice: Edge TTS voice identifier.
        rate: Speech rate adjustment (e.g., "-8%", "+10%").
        pitch: Pitch adjustment (e.g., "-3Hz", "+5Hz").

    Returns:
        List of word timing dicts with text, start (seconds), duration (seconds).
    """
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    word_timings: list[WordTiming] = []

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(str(output_path), "wb") as audio_file:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,  # ticks → seconds
                    "duration": chunk["duration"] / 10_000_000,
                })

    size_kb = output_path.stat().st_size // 1024
    log.info(
        "TTS generated: %s (%d KB, %d words, voice=%s)",
        output_path.name, size_kb, len(word_timings), voice,
    )
    return word_timings


def generate_speech(
    text: str,
    output_path: Path,
    voice: Optional[str] = None,
    rate: str = "-8%",
    pitch: str = "-3Hz",
    config: Optional[Config] = None,
) -> list[WordTiming]:
    """Generate TTS audio with word-level timestamps (sync wrapper).

    Args:
        text: The text to synthesize.
        output_path: Where to save the MP3 audio file.
        voice: Edge TTS voice name or shorthand from VOICES dict.
        rate: Speech rate adjustment.
        pitch: Pitch adjustment.
        config: Configuration instance.

    Returns:
        List of word timing dicts for subtitle generation.
    """
    config = config or get_config()
    voice = voice or config.voice

    # Resolve shorthand voice names
    if voice.lower() in VOICES:
        voice = VOICES[voice.lower()]

    log.info("Generating TTS for %d chars with voice %s...", len(text), voice)
    return asyncio.run(
        _generate_tts(text, Path(output_path), voice=voice, rate=rate, pitch=pitch)
    )


def list_voices() -> dict[str, str]:
    """Return all available voice shortcuts and their full identifiers."""
    return dict(VOICES)
