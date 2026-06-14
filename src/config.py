from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    LOG_LEVEL: str = Field(default="INFO")
    
    # Linear credentials
    LINEAR_API_KEY: SecretStr
    LINEAR_ORGANIZATION_SLUG: str
    
    # Discord credentials
    DISCORD_TOKEN: SecretStr
    DISCORD_CHANNEL_ID: int
    
    # Cloud Storage
    GDRIVE_FOLDER_ID: str
    GOOGLE_APPLICATION_CREDENTIALS: str

    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_INTERNAL_URL: str = Field(default="http://localhost:8000")

# Instantiate a global validated configuration object
settings = Settings()
