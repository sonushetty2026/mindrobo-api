from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"
    JWT_SECRET_KEY: str = "changeme-jwt-secret"
    DATABASE_URL: str
    RETELL_API_KEY: str = ""
    RETELL_WEBHOOK_SECRET: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    AZURE_STORAGE_ACCOUNT: str = ""
    KEY_VAULT_NAME: str = "kv-mindrobo-dev"
    
    # Azure Blob Storage
    AZURE_BLOB_CONNECTION_STRING: str = ""  # Required for call recordings/transcripts

    class Config:
        env_file = ".env"

settings = Settings()
