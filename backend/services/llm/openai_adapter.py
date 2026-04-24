from typing import Type
import instructor
import openai
from pydantic import BaseModel


# Reasoning models use a different API surface to standard chat models.
# They don't support temperature, and use reasoning_effort instead.
# They also require "developer" role instead of "system".
REASONING_MODELS = {"o1", "o3", "o3-mini", "o4-mini", "o1-mini", "o1-preview"}


class OpenAIAdapter:
    """LLM adapter for OpenAI — supports both standard chat and reasoning models.

    Reasoning models (o3, o4-mini etc.) differ from chat models in three ways:
    - They use reasoning_effort (low/medium/high) instead of temperature
    - They use the "developer" role instead of "system"
    - They do not support streaming in the same way

    The adapter handles these differences internally so service code
    never needs to know which model family is in use.
    """

    def __init__(self, model: str, api_key: str, base_url: str, reasoning_effort: str | None = None):
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._is_reasoning_model = any(model.startswith(rm) for rm in REASONING_MODELS)

        client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._client = instructor.from_openai(client)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
    ) -> BaseModel:
        if self._is_reasoning_model:
            return await self._reasoning_complete(system_prompt, user_prompt, response_model)
        return await self._chat_complete(system_prompt, user_prompt, response_model)

    async def _chat_complete(
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
        )

    async def _reasoning_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
    ) -> BaseModel:
        """Reasoning models use developer role and reasoning_effort, not temperature."""
        kwargs = dict(
            model=self._model,
            messages=[
                {"role": "developer", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_model=response_model,
            max_retries=2,
        )
        if self._reasoning_effort:
            kwargs["reasoning_effort"] = self._reasoning_effort

        return await self._client.chat.completions.create(**kwargs)
