"""
ASS subtitle generation for clipforge.

Creates word-by-word highlighted subtitles in ASS format with
Montserrat Bold 58px, white text with yellow highlight on the
current word. Positioned center-bottom for vertical (9:16) video.
"""

import logging
from pathlib import Path

log = logging.getLogger("clipforge.subtitles")

# ── ASS header template ──────────────────────────────────────────────────────

ASS_HEADER = """\
[Script Info]
Title: clipforge
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Montserrat Bold,58,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,3,2,2,40,40,120,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""


def _format_timestamp(seconds: float) -> str:
    """Format seconds as ASS timestamp ``H:MM:SS.cc``."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


# ── Public API ───────────────────────────────────────────────────────────────


def generate_subtitles(
    word_data: list[dict],
    output_path: Path,
    words_per_group: int = 3,
) -> Path:
    """Generate an ASS subtitle file with word-by-word yellow highlighting.

    Each group of ``words_per_group`` words is displayed together. Within
    each group, the current word is highlighted in yellow while the rest
    remain white, creating a karaoke-style reading effect.

    Args:
        word_data: List of dicts from ``voice.generate_speech``, each with
            ``text`` (str), ``start`` (float seconds), ``duration`` (float).
        output_path: Where to write the ``.ass`` file.
        words_per_group: How many words to show at once (default 3).

    Returns:
        The output_path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Group words into display chunks
    groups: list[dict] = []
    for i in range(0, len(word_data), words_per_group):
        chunk = word_data[i : i + words_per_group]
        text = " ".join(w["text"] for w in chunk).upper()
        start = chunk[0]["start"]
        end = chunk[-1]["start"] + chunk[-1]["duration"]
        groups.append({"text": text, "start": start, "end": end, "words": chunk})

    # Build ASS dialogue lines
    lines: list[str] = []

    for g_idx, group in enumerate(groups):
        chunk = group["words"]
        words_upper = [w["text"].upper() for w in chunk]

        for w_idx, word in enumerate(chunk):
            w_start = word["start"]
            w_end = word["start"] + word["duration"]

            # Extend timing for seamless display
            if w_idx < len(chunk) - 1:
                w_end = chunk[w_idx + 1]["start"]
            elif g_idx < len(groups) - 1:
                w_end = group["end"]

            # Build text with current word highlighted yellow
            parts: list[str] = []
            for j, word_text in enumerate(words_upper):
                if j == w_idx:
                    # Yellow highlight: &H0000FFFF = AABBGGRR = yellow
                    parts.append(
                        r"{\c&H0000FFFF&}" + word_text + r"{\c&H00FFFFFF&}"
                    )
                else:
                    parts.append(word_text)

            line_text = r"{\an2}" + " ".join(parts)
            ts_start = _format_timestamp(w_start)
            ts_end = _format_timestamp(w_end)

            lines.append(
                f"Dialogue: 0,{ts_start},{ts_end},Default,,0,0,0,,{line_text}"
            )

    # Write ASS file
    ass_content = ASS_HEADER + "\n".join(lines) + "\n"
    output_path.write_text(ass_content, encoding="utf-8")

    log.info(
        "Subtitles generated: %s (%d groups, %d events)",
        output_path.name, len(groups), len(lines),
    )
    return output_path
