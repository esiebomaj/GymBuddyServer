from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    openai_api_key: str
    mailchimp_api_key: str
    mailchimp_list_id: str

    debug: bool = False

    @property
    def mailchimp_dc(self) -> str:
        """Mailchimp datacenter prefix, e.g. 'us6' from API key suffix."""
        return self.mailchimp_api_key.rsplit("-", 1)[-1]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
