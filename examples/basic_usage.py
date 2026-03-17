#!/usr/bin/env python3
"""
Basic clipforge usage example.

Generates a short-form video from a topic or custom script.

Prerequisites:
  - pip install clipforge
  - ffmpeg installed on system
  - Set CLIPFORGE_LLM_KEY for AI story generation (optional)
  - Set CLIPFORGE_FAL_KEY for AI image generation (optional)
"""

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

# ── Option 1: Full AI pipeline (requires LLM key) ───────────────────────────

# from clipforge import generate_short
# video = generate_short(
#     topic="lightning",
#     style="mind_blowing",
#     output="output/lightning.mp4",
# )
# print(f"Video saved: {video}")


# ── Option 2: Custom script (no LLM key needed) ─────────────────────────────

from clipforge import generate_short

script = """
Right now, as you listen to this, there are over 8 million lightning strikes
hitting Earth every single day. But here is what nobody tells you. Lightning
does not actually come from the sky. It shoots up from the ground. That bolt
you see is the return stroke, racing upward at 270,000 miles per hour. The
temperature inside a lightning bolt is five times hotter than the surface of
the sun. For a split second, a channel thinner than your thumb becomes the
hottest point on the entire planet. Scientists have discovered that lightning
creates antimatter, the same stuff that powers theoretical starships. Every
thunderstorm above your head is producing particles that should not exist
outside of a particle accelerator. The scariest part? We still do not fully
understand why it happens.
""".strip()

video = generate_short(
    script=script,
    output="output/lightning_custom.mp4",
    voice="andrew",
    num_clips=4,
)
print(f"Video saved: {video}")


# ── Option 3: Use individual components ──────────────────────────────────────

# from clipforge.voice import generate_speech, list_voices
# from clipforge.subtitles import generate_subtitles
#
# # Just generate TTS + subtitles
# word_data = generate_speech(script, "output/voice.mp3", voice="ryan")
# generate_subtitles(word_data, "output/subs.ass")
# print("TTS and subtitles generated!")
#
# # List all voices
# for short, full in list_voices().items():
#     print(f"  {short}: {full}")
