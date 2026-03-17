"""
CLI entry point for clipforge.

Provides ``clipforge generate``, ``clipforge voices``, and
``clipforge config`` commands via Click.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .config import VOICES, get_config
from .story import STYLES


def _setup_logging(verbose: bool) -> None:
    """Configure logging for CLI output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.version_option(__version__, prog_name="clipforge")
def cli() -> None:
    """clipforge — AI-powered short-form video generator.

    Create viral YouTube Shorts & TikTok videos with AI-generated
    visuals, natural voices, and cinematic effects.
    """


@cli.command()
@click.option("--topic", "-t", type=str, default=None, help="Topic for AI story generation.")
@click.option(
    "--style", "-s",
    type=click.Choice(sorted(STYLES.keys()), case_sensitive=False),
    default="mind_blowing",
    help="Story style/genre.",
)
@click.option("--script", type=str, default=None, help="Custom script text (skips AI generation).")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output video path.")
@click.option("--voice", "-v", type=str, default=None, help="TTS voice name or shorthand.")
@click.option("--num-clips", type=int, default=5, help="Number of visual clips to generate.")
@click.option("--music", type=click.Path(exists=True), default=None, help="Background music file.")
@click.option("--verbose", is_flag=True, help="Enable debug logging.")
def generate(
    topic: Optional[str],
    style: str,
    script: Optional[str],
    output: Optional[str],
    voice: Optional[str],
    num_clips: int,
    music: Optional[str],
    verbose: bool,
) -> None:
    """Generate a short-form video.

    Either provide --topic for AI story generation, or --script with
    your own text. The pipeline generates TTS narration, visual clips,
    word-level subtitles, and composes the final video.

    Examples:

      clipforge generate --topic "lightning" --style mind_blowing

      clipforge generate --script "Your custom script..." --output video.mp4
    """
    _setup_logging(verbose)
    log = logging.getLogger("clipforge.cli")

    config = get_config()

    # Resolve output path
    if output:
        output_path = Path(output)
    else:
        config.ensure_output_dir()
        output_path = config.output_dir / "short.mp4"

    # Step 1: Get the story/script
    if script:
        story = script
        log.info("Using custom script (%d words)", len(story.split()))
    elif topic or config.has_llm:
        if not config.has_llm:
            click.echo("Error: No LLM API key set. Set CLIPFORGE_LLM_KEY or use --script.", err=True)
            sys.exit(1)
        from .story import generate_story
        click.echo(f"Generating {style} story (topic: {topic or 'random'})...")
        story = generate_story(style=style, topic=topic, config=config)
        click.echo(f"Story ({len(story.split())} words):\n{story}\n")
    else:
        click.echo("Error: Provide --topic, --script, or set CLIPFORGE_LLM_KEY.", err=True)
        sys.exit(1)

    # Step 2: Generate TTS
    from .voice import generate_speech
    tmp_dir = output_path.parent / ".clipforge_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    audio_path = tmp_dir / "voice.mp3"

    click.echo("Generating TTS narration...")
    word_data = generate_speech(
        story, audio_path, voice=voice, config=config,
    )
    click.echo(f"Audio: {audio_path} ({audio_path.stat().st_size // 1024} KB)")

    # Step 3: Generate subtitles
    from .subtitles import generate_subtitles
    subs_path = tmp_dir / "subs.ass"

    click.echo("Generating subtitles...")
    generate_subtitles(word_data, subs_path)

    # Step 4: Generate visual clips
    from .visuals import generate_clips
    clips_dir = tmp_dir / "clips"

    click.echo(f"Generating {num_clips} visual clips...")
    clips = generate_clips(story, clips_dir, num_clips=num_clips, config=config)
    click.echo(f"Generated {len(clips)} clips")

    # Step 5: Compose final video
    from .compose import compose_video

    click.echo("Composing final video...")
    music_path = Path(music) if music else None
    compose_video(
        clips=clips,
        audio=audio_path,
        subs=subs_path,
        output=output_path,
        music=music_path,
    )

    size_mb = output_path.stat().st_size / 1024 / 1024
    click.echo(f"\nDone! Video saved to: {output_path} ({size_mb:.1f} MB)")

    # Cleanup temp files
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)


@cli.command()
def voices() -> None:
    """List available TTS voices."""
    click.echo("Available TTS voices:\n")
    click.echo(f"  {'Shorthand':<12} {'Full Voice Name'}")
    click.echo(f"  {'─' * 12} {'─' * 40}")
    for short, full in sorted(VOICES.items()):
        click.echo(f"  {short:<12} {full}")
    click.echo(f"\nSet default: export CLIPFORGE_VOICE=en-US-AndrewMultilingualNeural")


@cli.command("config")
def show_config() -> None:
    """Show current configuration."""
    config = get_config()
    summary = config.summary()

    click.echo("clipforge configuration:\n")
    for key, value in summary.items():
        click.echo(f"  {key:<15} {value}")
    click.echo(f"\nSet via environment variables (CLIPFORGE_*).")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
