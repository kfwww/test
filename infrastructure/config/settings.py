from sqlalchemy.engine import URL
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    VLLM_HOST: str
    VLLM_PORT: int
    VLLM_MODEL: str

    API_HOST: str
    API_PORT: int

    HF_TOKEN: str
    VLLM_LOGGING_LEVEL: str
    
    @property
    def DATABASE_URL(self) -> str:
        return str(
            URL.create(
                drivername="postgresql+asyncpg",
                username=self.DB_USER,
                password=self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT,
                database=self.DB_NAME,
            )
        )

    @property
    def VLLM_URL(self) -> str:
        return f"http://{self.VLLM_HOST}:{self.VLLM_PORT}/v1"
    
    @property
    def API_URL(self) -> str:
        return f"http://{self.API_HOST}:{self.API_PORT}"
    

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()