import os
from typing import Type, TypeVar

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

load_dotenv()

T = TypeVar("T", bound=BaseModel)


def _get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing GEMINI_API_KEY. Set it in your environment or create a local .env file."
        )
    return genai.Client(api_key=api_key)


def generate_json(
    *,
    schema: Type[T],
    prompt: str,
    model: str,
    temperature: float = 0.2,
) -> T:
    """
    Calls Gemini with structured JSON output enforced by the provided Pydantic schema.
    """
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "temperature": temperature,
            "response_mime_type": "application/json",
            "response_json_schema": schema.model_json_schema(),
        },
    )

    # The SDK returns response.text containing the JSON payload.
    return schema.model_validate_json(response.text)

