# 🎬 ClipForge

**AI-powered short-form video generator.** Create viral YouTube Shorts & TikTok videos with AI-generated visuals, natural voices, and cinematic effects — all from a single command.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What it does

Give ClipForge a topic. It writes a script, generates cinematic AI visuals, narrates with a natural voice, adds word-by-word animated subtitles, and renders a ready-to-upload short — in under 2 minutes.

```bash
clipforge generate --topic "lightning" --style mind_blowing
```

**That's it.** You get a 1080x1920 vertical video ready for YouTube Shorts, TikTok, or Instagram Reels.

---

## Features

- 🤖 **AI Script Writing** — 11 content styles (mind_blowing, dark_fact, psychology, space...) with 25+ viral hook templates
- 🎨 **AI-Generated Visuals** — Contextual images via [FLUX Schnell](https://fal.ai/models/fal-ai/flux/schnell) (~$0.003/image), with cinematic Ken Burns camera effects
- 🗣️ **Natural TTS Voices** — 14+ voices via Edge TTS (100% free, no API key)
- 📝 **Word-by-Word Subtitles** — Animated ASS subtitles with yellow highlight (85% of viewers watch without sound)
- 🎵 **Background Music** — Optional music layer with auto-mixing
- 📐 **Perfect Format** — 1080×1920, H.264, 30fps, optimized for mobile
- 🔄 **Fallback System** — No AI image API? Falls back to gradient clips. No LLM key? Bring your own script.
- 💰 **Almost Free** — Edge TTS is free. Groq LLM is free. Only AI images cost money (~$0.01/video)

## How it works

```
Topic → LLM Script → Scene Extraction → AI Images → Ken Burns Clips
                   → Edge TTS Audio → Word Timestamps → ASS Subtitles
                                                      → FFmpeg Compose → 🎬 Video
```

---

## Quick Start

### Install

```bash
pip install clipforge
```

**System requirement:** [FFmpeg](https://ffmpeg.org/download.html) must be installed.

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### Generate your first video

```bash
# With a custom script (no LLM key needed)
clipforge generate \
  --script "Lightning doesn't come from the sky. It shoots up from the ground at 270,000 miles per hour." \
  --output my_first_short.mp4

# With AI script generation (needs a free Groq key)
export CLIPFORGE_LLM_KEY=gsk_your_groq_key
clipforge generate --topic "black holes" --style space
```

### As a Python library

```python
from clipforge import generate_short

# Full auto — topic to video
generate_short(
    topic="the deep ocean",
    style="ocean_deep",
    output="ocean_short.mp4"
)

# Custom script — you write, ClipForge produces
generate_short(
    script="Your custom narration text goes here...",
    output="custom_short.mp4",
    voice="en-GB-RyanNeural"
)
```

---

## Configuration

All settings via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLIPFORGE_LLM_PROVIDER` | `groq` | LLM provider: `groq` (free), `openai`, `anthropic` |
| `CLIPFORGE_LLM_KEY` | — | API key for script generation |
| `CLIPFORGE_LLM_MODEL` | auto | Model name (auto-selects best per provider) |
| `CLIPFORGE_FAL_KEY` | — | [fal.ai](https://fal.ai) key for AI images (optional) |
| `CLIPFORGE_VOICE` | `en-US-AndrewMultilingualNeural` | Default TTS voice |
| `CLIPFORGE_OUTPUT_DIR` | `./output` | Where to save videos |

### Get your free keys

1. **Groq** (free LLM): [console.groq.com](https://console.groq.com) → Create API Key
2. **fal.ai** (AI images, ~$0.003/image): [fal.ai/dashboard](https://fal.ai/dashboard) → Keys

---

## CLI Reference

```bash
# Generate a video from a topic
clipforge generate --topic "quantum physics" --style mind_blowing

# Generate from your own script
clipforge generate --script "Your text here..." --voice en-GB-RyanNeural

# Full options
clipforge generate \
  --topic "lightning" \
  --style dark_fact \
  --voice en-US-BrianMultilingualNeural \
  --num-clips 5 \
  --ai-ratio 0.6 \
  --output lightning.mp4

# List available voices
clipforge voices

# Show current config
clipforge config
```

### Content Styles

| Style | Vibe |
|-------|------|
| `mind_blowing` | 🤯 Jaw-dropping scientific facts |
| `dark_fact` | 🌑 Mysterious, little-known stories |
| `psychology` | 🧠 Fascinating human behavior |
| `space` | 🌌 Awe-inspiring cosmos |
| `nature` | 🌿 Incredible natural world |
| `history` | ⚔️ Forgotten historical stories |
| `ocean_deep` | 🌊 Deep sea mysteries |
| `future_tech` | 🚀 Mind-bending technology |
| `body_facts` | 🫀 Bizarre human body facts |
| `myth_busted` | 💥 Common misconceptions debunked |
| `food_origins` | 🍕 Surprising food history |

---

## Advanced Usage

### Custom pipeline (mix & match)

```python
from clipforge.story import generate_story
from clipforge.visuals import generate_clips
from clipforge.voice import synthesize_speech
from clipforge.subtitles import generate_subtitles
from clipforge.compose import compose_video

# 1. Write or generate a script
script = generate_story(style="dark_fact", topic="Bermuda Triangle")

# 2. Generate AI visuals
clips = generate_clips(script, output_dir="./clips", num_clips=5, ai_ratio=0.8)

# 3. Text-to-speech
audio, word_timestamps = synthesize_speech(script, output_path="./voice.mp3")

# 4. Animated subtitles
subs = generate_subtitles(word_timestamps, output_path="./subs.ass")

# 5. Compose final video
compose_video(
    clips=clips,
    audio=audio,
    subtitles=subs,
    output="bermuda.mp4",
    music="./my_music.mp3",  # optional
    voice_volume=0.85,
    music_volume=0.08,
)
```

### Batch generation

```python
from clipforge import generate_short

topics = [
    ("lightning", "mind_blowing"),
    ("deep ocean creatures", "ocean_deep"),
    ("ancient Rome secrets", "history"),
]

for topic, style in topics:
    generate_short(topic=topic, style=style)
    print(f"✓ {topic}")
```

---

## Output Specs

| Property | Value |
|----------|-------|
| Resolution | 1080×1920 (9:16 portrait) |
| Codec | H.264 (libx264) |
| Quality | CRF 23 |
| FPS | 30 |
| Audio | AAC 192kbps, 44.1kHz |
| Subtitles | Burned-in ASS (Montserrat Bold) |
| Duration | 55-65 seconds (optimized for Shorts) |

---

## Cost Breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| Script (Groq) | **Free** | Free tier: 30 req/min |
| Voice (Edge TTS) | **Free** | Microsoft Edge TTS, unlimited |
| AI Images (fal.ai) | ~$0.009/video | 3 images × $0.003 |
| FFmpeg | **Free** | Open source |
| **Total per video** | **~$0.01** | or $0 without AI images |

---

## How does it compare?

| Feature | ClipForge | ShortGPT | MoneyPrinter |
|---------|-----------|----------|--------------|
| AI-generated visuals | ✅ Contextual | ❌ Stock only | ❌ Stock only |
| Free TTS | ✅ Edge TTS | ❌ ElevenLabs ($) | ✅ Edge TTS |
| Word-by-word subs | ✅ Animated | ❌ Basic | ❌ Basic |
| Ken Burns effects | ✅ 4 variants | ❌ | ❌ |
| Cost per video | ~$0.01 | ~$0.10+ | ~$0.05+ |
| One-command generate | ✅ | ❌ | ❌ |
| No GPU needed | ✅ | ✅ | ✅ |

---

## Contributing

PRs welcome! Areas that need love:
- More content styles and hook templates
- Additional LLM providers
- Video transition effects between clips
- Multi-language support (FR, ES, PT voices exist in Edge TTS)
- Web UI

---

## License

MIT — do whatever you want with it.

---

Built by [@DarkPancakes](https://github.com/DarkPancakes) • If this saves you time, drop a ⭐
