import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_model: str
    max_input_chars: int
    google_api_key: str | None
    openai_api_key: str | None


def _positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "ollama").strip().lower(),
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        max_input_chars=_positive_int(os.getenv("MAX_INPUT_CHARS"), 20000),
        google_api_key=os.getenv("GOOGLE_API_KEY") or None,
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
    )
