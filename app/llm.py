from app.config import get_settings


class LLMConfigurationError(RuntimeError):
    """Raised when the selected provider cannot be configured safely."""


def validate_provider_configuration() -> str | None:
    settings = get_settings()
    if settings.llm_provider not in {"ollama", "gemini", "openai"}:
        return "Unsupported LLM_PROVIDER. Choose ollama, gemini, or openai."
    if not settings.llm_model:
        return "LLM_MODEL is not configured."
    if settings.llm_provider == "gemini" and not settings.google_api_key:
        return "GOOGLE_API_KEY is required for the gemini provider."
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        return "OPENAI_API_KEY is required for the openai provider."
    return None


def create_chat_model():
    settings = get_settings()
    configuration_error = validate_provider_configuration()
    if configuration_error:
        raise LLMConfigurationError(configuration_error)

    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.llm_model)
    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
        )
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key)
    raise LLMConfigurationError("Unsupported LLM_PROVIDER. Choose ollama, gemini, or openai.")
