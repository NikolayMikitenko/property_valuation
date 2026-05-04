from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM model
    openai_api_key: SecretStr
    openai_api_base: str
    openai_eval_model: str

    # Langfuse
    langfuse_public_key: SecretStr
    langfuse_secret_key: SecretStr
    langfuse_base_url: str = "https://us.cloud.langfuse.com"
    langfuse_prompt_label: str = "production"
    langfuse_environment: str = "production"        

    model_config = {"env_file": ".env", "extra":"ignore"}    

settings = Settings()