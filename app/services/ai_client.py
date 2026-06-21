import json
import logging
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class AIClient:
    """Thin wrapper around OpenAI with graceful fallback when unconfigured."""

    def __init__(self) -> None:
        self._client: OpenAI | None = None
        if settings.openai_api_key:
            self._client = OpenAI(api_key=settings.openai_api_key)

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        if not self._client:
            return None

        try:
            response = self._client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            content = response.choices[0].message.content
            if not content:
                return None
            return json.loads(content)
        except Exception:
            logger.exception("OpenAI request failed")
            return None
