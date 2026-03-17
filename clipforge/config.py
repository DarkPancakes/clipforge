"""
Configuration management for clipforge.

Reads settings from environment variables with sensible defaults.
All config is centralized here — no hardcoded values anywhere else.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Default models per provider ──────────────────────────────────────────────

DEFAULT_MODELS: dict[str, str] = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
}

# ── API endpoints ────────────────────────────────────────────────────────────

API_ENDPOINTS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
}

# ── Available TTS voices ─────────────────────────────────────────────────────

VOICES: dict[str, str] = {
    "andrew": "en-US-AndrewMultilingualNeural",
    "brian": "en-US-BrianMultilingualNeural",
    "ava": "en-US-AvaMultilingualNeural",
    "emma": "en-US-EmmaMultilingualNeural",
    "ryan": "en-GB-RyanNeural",
    "sonia": "en-GB-SoniaNeural",
    "libby": "en-GB-LibbyNeural",
    "guy": "en-US-GuyNeural",
    "jenny": "en-US-JennyNeural",
    "aria": "en-US-AriaNeural",
    "davis": "en-US-DavisNeural",
    "jane": "en-US-JaneNeural",
    "jason": "en-US-JasonNeural",
    "tony": "en-US-TonyNeural",
    "nancy": "en-US-NancyNeural",
    "sara": "en-US-SaraNeural",
}


@dataclass
class Config:
    """Central configuration for clipforge.

    All values can be overridden via environment variables prefixed
    with ``CLIPFORGE_`` or passed directly to functions.
    """

    llm_provider: str = field(
        default_factory=lambda: os.environ.get("CLIPFORGE_LLM_PROVIDER", "groq")
    )
    llm_key: str = field(
        default_factory=lambda: os.environ.get("CLIPFORGE_LLM_KEY", "")
    )
    llm_model: Optional[str] = field(
        default_factory=lambda: os.environ.get("CLIPFORGE_LLM_MODEL")
    )
    fal_key: str = field(
        default_factory=lambda: os.environ.get("CLIPFORGE_FAL_KEY", "")
    )
    voice: str = field(
        default_factory=lambda: os.environ.get(
            "CLIPFORGE_VOICE", "en-US-AndrewMultilingualNeural"
        )
    )
    output_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("CLIPFORGE_OUTPUT_DIR", "./output")
        )
    )

    @property
    def resolved_model(self) -> str:
        """Return the LLM model name, falling back to provider default."""
        if self.llm_model:
            return self.llm_model
        return DEFAULT_MODELS.get(self.llm_provider, DEFAULT_MODELS["groq"])

    @property
    def llm_endpoint(self) -> str:
        """Return the API endpoint URL for the configured provider."""
        return API_ENDPOINTS.get(self.llm_provider, API_ENDPOINTS["groq"])

    @property
    def has_fal(self) -> bool:
        """Check if fal.ai image generation is available."""
        return bool(self.fal_key)

    @property
    def has_llm(self) -> bool:
        """Check if an LLM API key is configured."""
        return bool(self.llm_key)

    def ensure_output_dir(self) -> Path:
        """Create and return the output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    def summary(self) -> dict[str, str]:
        """Return a human-readable config summary (keys masked)."""
        return {
            "LLM Provider": self.llm_provider,
            "LLM Model": self.resolved_model,
            "LLM Key": _mask(self.llm_key),
            "FAL Key": _mask(self.fal_key),
            "Voice": self.voice,
            "Output Dir": str(self.output_dir),
        }


def _mask(key: str) -> str:
    """Mask an API key for safe display."""
    if not key:
        return "(not set)"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def get_config() -> Config:
    """Create a Config instance from current environment."""
    return Config()
