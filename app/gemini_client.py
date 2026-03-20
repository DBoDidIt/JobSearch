import os
from pathlib import Path
from typing import Optional, Type, TypeVar

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel


def _load_env() -> None:
    """
    Always load the repo-local .env, even if uvicorn is started elsewhere.
    """
    repo_root = Path(__file__).resolve().parents[1]
    dotenv_path = repo_root / ".env"
    load_dotenv(dotenv_path=str(dotenv_path), override=False)

T = TypeVar("T", bound=BaseModel)


def _get_gemini_client() -> genai.Client:
    _load_env()
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
    max_output_tokens: Optional[int] = None,
) -> T:
    """
    Calls Gemini with structured JSON output enforced by the provided Pydantic schema.
    """
    client = _get_gemini_client()
    config: dict = {
        "temperature": temperature,
        "response_mime_type": "application/json",
        "response_json_schema": schema.model_json_schema(),
    }
    if max_output_tokens is not None:
        config["max_output_tokens"] = max_output_tokens
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )

    # The SDK returns response.text containing the JSON payload.
    return schema.model_validate_json(response.text)

