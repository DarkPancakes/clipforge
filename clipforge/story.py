"""
Story generation for clipforge.

Generates engaging 140-165 word short-form video scripts via any
OpenAI-compatible LLM (Groq free tier, OpenAI, Anthropic).
Supports 11 content styles and 25+ hook templates.
"""

import json
import logging
import random
import re
import time
import requests as _requests
from typing import Optional

from .config import Config, get_config

log = logging.getLogger("clipforge.story")

# ── Content styles ───────────────────────────────────────────────────────────

STYLES: dict[str, str] = {
    "mind_blowing": (
        "Tell a mind-blowing scientific or historical fact that most people "
        "don't know. Tone: amazed, wonder."
    ),
    "dark_fact": (
        "Tell a dark, mysterious, little-known fact. The tone should be calm, "
        "mysterious, almost whispered."
    ),
    "psychology": (
        "Tell a disturbing or fascinating psychology fact about human behavior. "
        "Tone: intimate, thought-provoking."
    ),
    "space": (
        "Tell an awe-inspiring fact about space or the universe. "
        "Tone: grand, contemplative."
    ),
    "nature": (
        "Tell an incredible fact about nature or animals. "
        "Tone: warm, contemplative, awe-inspiring."
    ),
    "history": (
        "Tell a forgotten or bizarre historical story. "
        "Tone: storytelling, dramatic."
    ),
    "ocean_deep": (
        "Tell an incredible fact about the deep ocean or sea creatures. "
        "Tone: mysterious, awe-inspiring, slightly terrifying."
    ),
    "future_tech": (
        "Tell a mind-bending fact about emerging technology or what science "
        "says the future holds. Tone: excited, visionary."
    ),
    "body_facts": (
        "Tell a bizarre fact about the human body that makes people go wow. "
        "Tone: intimate, slightly gross, fascinating."
    ),
    "myth_busted": (
        "Debunk a common myth or misconception that most people believe. "
        "Tone: confident, revelatory, slightly smug."
    ),
    "food_origins": (
        "Tell a surprising origin story about a common food or drink. "
        "Tone: conversational, surprising."
    ),
}

# ── Hook templates ───────────────────────────────────────────────────────────

HOOK_TEMPLATES: list[str] = [
    # DIRECT SHOCK
    "Open with the most shocking detail of the story as a bold statement. No intro.",
    "Start with a specific number or statistic that sounds impossible.",
    "State something terrifying as casually as possible, like it's common knowledge.",
    # CURIOSITY GAP
    "Start with 'Nobody talks about this, but...' and reveal something unsettling.",
    "Start with 'There's a reason why...' to create instant curiosity.",
    "Start with 'You've been told [common belief]. That's not exactly true.'",
    "Start with 'Here's something that was hidden for decades.'",
    "Start with 'Everyone assumes [X]. The truth is far stranger.'",
    # SCENE SETTING
    "Start with 'Picture this:' followed by a vivid scene that pulls the listener in.",
    "Start with a specific date, place, and action — like a documentary opening.",
    "Start with 'Right now, as you listen to this...' to create immediacy.",
    "Start with a sensory detail — what you'd smell, hear, or feel in the scene.",
    # QUESTION / CHALLENGE
    "Start with 'Have you ever noticed...' followed by something eerie.",
    "Start with 'Ever wonder why...' and then reveal something disturbing.",
    "Start with 'Can you guess what...' followed by a mind-bending fact.",
    "Start with 'Think about the last time you...' to make it personal.",
    # REVELATION
    "Start with 'Scientists still can't explain why...'",
    "Start with 'In [year], something happened that changed everything.'",
    "Start with 'The scariest part? This is completely real.'",
    "Start with 'Most people walk past this every day without knowing...'",
    "Start with 'This story was buried for years.'",
    # SECRET / FORBIDDEN
    "Start with 'This is the story they tried to erase.'",
    "Start with 'Behind closed doors, something happened that...'",
    "Start with 'There is a place where...' and describe something uncanny.",
    # VIRAL PATTERNS
    "Start mid-story as if the viewer dropped into an ongoing conversation.",
    "Start with THE most unbelievable detail, then say 'Let me back up...'",
    "Start with 'This is going to sound fake, but...'",
    "Start with 'POV:' followed by a scenario.",
    "Start with a one-word sentence for maximum impact, then expand.",
]

# ── Banned phrases ───────────────────────────────────────────────────────────

BANNED_PHRASES: list[str] = [
    "What if I told you",
    "What if I said",
    "Let me tell you",
    "Did you know",
    "Brace yourself",
    "Buckle up",
    "Here is the thing",
    "Here's the thing",
    "You won't believe",
    "Gather round",
    "Gather around",
    "Sit down for this",
]

_BANNED_RE = re.compile(
    r"^(" + "|".join(re.escape(p) for p in BANNED_PHRASES) + r")\b",
    re.IGNORECASE,
)


def _filter_banned(story: str) -> str:
    """Remove banned opener phrases from the story."""
    cleaned = _BANNED_RE.sub("", story).lstrip(" ,.:;—-")
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


# ── LLM call ─────────────────────────────────────────────────────────────────


def _call_llm(
    prompt: str,
    config: Config,
    max_tokens: int = 800,
    temperature: float = 0.8,
) -> str:
    """Send a chat completion request to the configured LLM provider."""
    if not config.has_llm:
        raise RuntimeError(
            "No LLM API key configured. Set CLIPFORGE_LLM_KEY or pass it in config."
        )

    provider = config.llm_provider

    if provider == "anthropic":
        return _call_anthropic(prompt, config, max_tokens, temperature)

    # OpenAI-compatible (Groq, OpenAI)
    payload = {
        "model": config.resolved_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {config.llm_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(3):
        try:
            resp = _requests.post(
                config.llm_endpoint,
                headers=headers,
                json=payload,
                timeout=60,
            )
            if resp.status_code == 429 and attempt < 2:
                wait = 2 ** attempt * 3
                log.warning("Rate limited (429), waiting %ds...", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
        except _requests.exceptions.HTTPError as exc:
            body = resp.text[:300] if resp is not None else str(exc)
            raise RuntimeError(f"LLM API error {resp.status_code}: {body}") from exc
        except Exception as exc:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"LLM request failed: {exc}") from exc

    raise RuntimeError("LLM: max retries exceeded")


def _call_anthropic(
    prompt: str,
    config: Config,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call the Anthropic Messages API."""
    payload = {
        "model": config.resolved_model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }

    headers = {
        "x-api-key": config.llm_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    for attempt in range(3):
        try:
            resp = _requests.post(
                config.llm_endpoint,
                headers=headers,
                json=payload,
                timeout=60,
            )
            if resp.status_code == 429 and attempt < 2:
                time.sleep(2 ** attempt * 3)
                continue
            resp.raise_for_status()
            result = resp.json()
            return result["content"][0]["text"].strip()
        except _requests.exceptions.HTTPError as exc:
            body = resp.text[:300] if resp is not None else str(exc)
            raise RuntimeError(f"Anthropic API error {resp.status_code}: {body}") from exc
        except Exception as exc:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Anthropic request failed: {exc}") from exc

    raise RuntimeError("Anthropic: max retries exceeded")


# ── Public API ───────────────────────────────────────────────────────────────


def generate_story(
    style: str = "mind_blowing",
    topic: Optional[str] = None,
    config: Optional[Config] = None,
) -> str:
    """Generate an engaging short-form video script.

    Args:
        style: Content style key (see ``STYLES``).
        topic: Optional topic hint to guide the story.
        config: Configuration instance. Uses env vars if not provided.

    Returns:
        A 140-165 word story script ready for TTS narration.

    Raises:
        RuntimeError: If the LLM call fails.
        ValueError: If the style is unknown.
    """
    config = config or get_config()

    if style not in STYLES:
        available = ", ".join(sorted(STYLES.keys()))
        raise ValueError(f"Unknown style '{style}'. Available: {available}")

    style_prompt = STYLES[style]
    hook_instruction = random.choice(HOOK_TEMPLATES)
    topic_hint = f" The topic should be related to: {topic}." if topic else ""

    prompt = f"""You are a captivating storyteller for short-form video content (TikTok/YouTube Shorts).

{style_prompt}{topic_hint}

Hook instruction: {hook_instruction}

Rules:
- Write exactly 140-165 words (this is critical for 55-65 second video duration). Count carefully — too short kills the pacing, too long loses viewers
- ABSOLUTELY FORBIDDEN phrases (instant disqualification): "What if I told you", "What if I said", "Let me tell you", "Did you know", "Brace yourself", "Buckle up", "Here is the thing", "You won't believe"
- You MUST use the hook instruction above — do NOT improvise a different opening
- Use vivid sensory language — make the listener SEE, FEEL, HEAR the story
- Vary sentence length dramatically — mix 3-word punches with longer flowing sentences
- Include one unexpected twist or reversal that reframes everything
- Build tension throughout
- End with an open loop or call to curiosity — leave them wanting more, make them save or share
- Do NOT use hashtags, emojis, or formatting
- Write in plain spoken English, as if telling someone a story
- The story should feel complete yet leave a lingering question
- Each story must feel unique — avoid formulaic structure

Write the story now, nothing else:"""

    log.info("Generating %s story (topic=%s)...", style, topic or "random")
    story = _call_llm(prompt, config)
    story = _filter_banned(story)

    word_count = len(story.split())
    log.info("Story generated: %d words", word_count)

    return story


def list_styles() -> dict[str, str]:
    """Return all available content styles with descriptions."""
    return dict(STYLES)
