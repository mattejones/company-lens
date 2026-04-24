from typing import Type
import instructor
import openai
from pydantic import BaseModel


class OllamaAdapter:
    """LLM adapter for Ollama via the OpenAI-compatible API.

    Key differences from the OpenAI adapter:
    - Uses JSON mode for structured output (more reliable than tool-calling via Ollama)
    - Disables Qwen3 thinking tokens via extra_body to avoid interference with
      structured output parsing
    - Uses a lower temperature for deterministic structured output
    """

    def __init__(self, model: str, base_url: str):
        self._model = model
        client = openai.AsyncOpenAI(
            api_key="ollama",  # required by client, ignored by Ollama
            base_url=base_url,
        )
        self._client = instructor.from_openai(client, mode=instructor.Mode.JSON)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
    ) -> BaseModel:
        return await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_model=response_model,
            max_retries=2,
            temperature=0.1,
            # Disables Qwen3 chain-of-thought thinking tokens.
            # These appear before the JSON and break structured output parsing.
            # Safe to include for non-Qwen3 models — they ignore unknown extra_body fields.
            extra_body={"think": False},
        )
