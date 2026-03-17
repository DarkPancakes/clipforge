"""
clipforge — AI-powered short-form video generator.

Create viral YouTube Shorts & TikTok videos with AI-generated visuals,
natural voices, and cinematic effects.

Quick start::

    from clipforge import generate_short
    generate_short(topic="lightning", style="mind_blowing", output="video.mp4")

Or use individual components::

    from clipforge.story import generate_story
    from clipforge.voice import generate_speech
    from clipforge.subtitles import generate_subtitles
    from clipforge.visuals import generate_clips
    from clipforge.compose import compose_video
"""

__version__ = "0.1.0"
__author__ = "DarkPancakes"

import logging
import shutil
from pathlib import Path
from typing import Optional

from .config import Config, get_config

log = logging.getLogger("clipforge")


def generate_short(
    topic: Optional[str] = None,
    style: str = "mind_blowing",
    script: Optional[str] = None,
    output: str = "output/short.mp4",
    voice: Optional[str] = None,
    num_clips: int = 5,
    music: Optional[str] = None,
    config: Optional[Config] = None,
) -> Path:
    """Generate a complete short-form video end-to-end.

    This is the high-level convenience function that runs the full
    pipeline: story generation → TTS → subtitles → visuals → composition.

    Args:
        topic: Topic for AI story generation (requires LLM key).
        style: Content style (see ``clipforge.story.STYLES``).
        script: Custom script text — skips AI story generation.
        output: Output video file path.
        voice: TTS voice name or shorthand.
        num_clips: Number of visual clips to generate.
        music: Optional background music file path.
        config: Configuration override.

    Returns:
        Path to the generated video file.

    Raises:
        RuntimeError: If critical steps fail.
        ValueError: If neither topic/script is provided and no LLM key is set.
    """
    from .compose import compose_video
    from .story import generate_story
    from .subtitles import generate_subtitles
    from .visuals import generate_clips
    from .voice import generate_speech

    config = config or get_config()
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_dir = output_path.parent / f".clipforge_tmp_{id(config)}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Story
        if script:
            story = script
        elif topic or config.has_llm:
            story = generate_story(style=style, topic=topic, config=config)
        else:
            raise ValueError(
                "Provide 'topic' (with CLIPFORGE_LLM_KEY set) or 'script' text."
            )

        log.info("Story: %d words", len(story.split()))

        # 2. TTS
        audio_path = tmp_dir / "voice.mp3"
        word_data = generate_speech(
            story, audio_path, voice=voice, config=config,
        )

        # 3. Subtitles
        subs_path = tmp_dir / "subs.ass"
        generate_subtitles(word_data, subs_path)

        # 4. Visuals
        clips_dir = tmp_dir / "clips"
        clips = generate_clips(
            story, clips_dir, num_clips=num_clips, config=config,
        )

        # 5. Compose
        music_path = Path(music) if music else None
        compose_video(
            clips=clips,
            audio=audio_path,
            subs=subs_path,
            output=output_path,
            music=music_path,
        )

        log.info("Video generated: %s", output_path)
        return output_path

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
