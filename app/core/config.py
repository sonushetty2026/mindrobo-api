from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"
    DATABASE_URL: str
    RETELL_API_KEY: str = ""
    RETELL_WEBHOOK_SECRET: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    AZURE_STORAGE_ACCOUNT: str = ""
    KEY_VAULT_NAME: str = "kv-mindrobo-dev"

    class Config:
        env_file = ".env"

settings = Settings()
