"""Thin Gemini wrapper.

Isolates all network + SDK details behind two methods (`plan` and
`critique`) that return already-parsed JSON. Responsibilities:
  - lazy-import the SDK so the rest of the app runs without it installed
  - report `available` (False when no key or SDK missing) so callers can
    fall back gracefully
  - request JSON output, parse it, and retry once on transient/parse errors
  - never log or expose the API key
"""

from __future__ import annotations

import json
from typing import Any

from config import Settings
from logging_config import get_logger

logger = get_logger()


class LLMError(RuntimeError):
    """Raised when the LLM call fails or returns unparseable output."""


def _extract_json(text: str) -> Any:
    """Parse JSON from model text, tolerating ```json code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Drop the opening fence line and any trailing fence.
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    return json.loads(cleaned.strip())


class GeminiClient:
    """Wrapper around google-genai with graceful degradation."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = None
        self._available = False

        if not settings.has_api_key:
            logger.info("Gemini disabled: no API key configured (fallback mode).")
            return

        try:
            from google import genai  # type: ignore

            self._client = genai.Client(api_key=settings.gemini_api_key)
            self._available = True
            logger.info("Gemini client initialized (model=%s).", settings.model)
        except ImportError:
            logger.warning("google-genai not installed; running in fallback mode.")
        except Exception as exc:  # pragma: no cover - defensive init guard
            logger.warning("Gemini init failed (%s); running in fallback mode.", type(exc).__name__)

    @property
    def available(self) -> bool:
        """True only when a usable client was constructed."""
        return self._available

    def _generate_json(self, system_instruction: str, prompt: str) -> Any:
        """Call Gemini asking for JSON, parse it, retry once on failure."""
        if not self._available:
            raise LLMError("LLM not available")

        from google.genai import types  # type: ignore

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.2,
        )

        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                response = self._client.models.generate_content(
                    model=self._settings.model,
                    contents=prompt,
                    config=config,
                )
                return _extract_json(response.text or "")
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                logger.warning("LLM parse error on attempt %d: %s", attempt, exc)
            except Exception as exc:  # network / SDK / quota errors
                last_error = exc
                logger.warning("LLM call error on attempt %d: %s", attempt, type(exc).__name__)

        raise LLMError(f"LLM failed after retries: {last_error}")

    def plan(self, system_instruction: str, prompt: str) -> Any:
        """Run the planning prompt; return parsed JSON (expected: a list)."""
        return self._generate_json(system_instruction, prompt)

    def critique(self, system_instruction: str, prompt: str) -> Any:
        """Run the critique prompt; return parsed JSON (expected: an object)."""
        return self._generate_json(system_instruction, prompt)
