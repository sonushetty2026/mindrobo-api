from pydantic_settings import BaseSettings
import secrets

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32) if not "JWT_SECRET_KEY" in globals() else "changeme-jwt-secret"
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
    
    # Stripe Billing
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID: str = ""  # Price ID for $49/month subscription
    
    # SendGrid Email (for verification and password reset)
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@mindrobo.com"
    SENDGRID_FROM_NAME: str = "MindRobo"

    class Config:
        env_file = ".env"

settings = Settings()
