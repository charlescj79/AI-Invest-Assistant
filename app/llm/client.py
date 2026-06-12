import json
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app.config import get_settings
from app.llm.prompts import SYSTEM_PROMPT

T = TypeVar("T", bound=BaseModel)


class ClaudeClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.claude_model
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def structured(self, instruction: str, context: dict, output_model: type[T]) -> T:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=16_000,
            thinking={"type": "adaptive"},
            output_format=output_model,
            output_config={"effort": "high"},
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {"instruction": instruction, "context": context},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                }
            ],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Claude refused to produce an investment research response")
        if response.parsed_output is not None:
            return response.parsed_output
        text = next((block.text for block in response.content if block.type == "text"), "{}")
        return output_model.model_validate_json(text)
