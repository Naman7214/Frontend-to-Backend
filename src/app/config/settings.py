from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Groq settings
    GROQ_API_KEY: str
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_COMPLETION_ENDPOINT: str = "/chat/completions"
    GROQ_MODEL: str = "meta-llama/llama-4-maverick-17b-128e-instruct"

    # OpenAI settings
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_COMPLETION_ENDPOINT: str = "/chat/completions"
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_API_KEY: str

    # Anthropic settings
    ANTHROPIC_API_KEY: str
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_MESSAGES_ENDPOINT: str = "/v1/messages"
    ANTHROPIC_MODEL: str = "claude-3-7-sonnet-20250219"

    # MongoDB settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "F2B"
    ERROR_COLLECTION_NAME: str = "error_logs"
    LLM_USAGE_COLLECTION_NAME: str = "llm_usage_logs"

    # LangFuse settings
    APP_VERSION: str = "1.0.0"
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_HOST: str = "http://localhost:3000"


    class Config:
        env_file = ".env"


settings = Settings()
