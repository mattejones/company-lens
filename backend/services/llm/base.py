from typing import Protocol, Type, runtime_checkable
from pydantic import BaseModel


@runtime_checkable
class LLMAdapter(Protocol):
    """Protocol defining the interface all LLM adapters must satisfy.

    Using Protocol (structural subtyping) rather than ABC means adapters
    don't need to inherit from a base class — they just need to implement
    the right methods. This makes adding new providers straightforward
    and keeps the adapter implementations decoupled from each other.
    """

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
    ) -> BaseModel:
        """Send a structured completion request and return a validated Pydantic model.

        Args:
            system_prompt: The system instruction string
            user_prompt: The user message string
            response_model: The Pydantic model class to validate the response against

        Returns:
            A validated instance of response_model
        """
        ...
