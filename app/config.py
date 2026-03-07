from pydantic_settings import BaseSettings
from pydantic import Field
import yaml
from pathlib import Path

class Settings(BaseSettings):
    blockchain_api_base_url: str = Field(..., alias="BLOCKCHAIN_API_BASE_URL")
    request_timeout_seconds: int = Field(8, alias="REQUEST_TIMEOUT_SECONDS")

    class Config:
        env_file = ".env"
        extra = "ignore"

def load_produce_standards(path: str = "config/produce_standards.yml") -> dict:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)