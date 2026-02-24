"""
Application configuration.
Secrets are loaded from Azure Key Vault (kv-mindrobo-dev) via the VM's
Managed Identity at startup, then fallen back to environment variables /
.env file so local development still works without Key Vault access.
"""
import os
import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key Vault → environment variable mapping
# Secret names in Key Vault use lowercase-dashes; env vars use UPPER_SNAKE.
# Add new entries here whenever a new secret is stored in Key Vault.
# ---------------------------------------------------------------------------
_KV_TO_ENV: dict[str, str] = {
    "database-url":           "DATABASE_URL",
    "jwt-secret-key":         "JWT_SECRET_KEY",
    "sendgrid-api-key":       "SENDGRID_API_KEY",
    "sendgrid-from-email":    "SENDGRID_FROM_EMAIL",
    "sendgrid-from-name":     "SENDGRID_FROM_NAME",
    "stripe-secret-key":      "STRIPE_API_KEY",
    "stripe-publishable-key": "STRIPE_PUBLISHABLE_KEY",
    "stripe-webhook-secret":  "STRIPE_WEBHOOK_SECRET",
    "stripe-price-id":        "STRIPE_PRICE_ID",
    "retell-api-key":         "RETELL_API_KEY",
    "storage-connection-string": "AZURE_BLOB_CONNECTION_STRING",
    "azure-storage-account":  "AZURE_STORAGE_ACCOUNT",
    "twilio-account-sid":     "TWILIO_ACCOUNT_SID",
    "twilio-auth-token":      "TWILIO_AUTH_TOKEN",
    "twilio-phone-number":    "TWILIO_PHONE_NUMBER",
    "github-webhook-secret":  "GITHUB_WEBHOOK_SECRET",
    "pg-host":                "PG_HOST",
    "pg-db":                  "PG_DB",
    "pg-user":                "PG_USER",
    "pg-password":            "PG_PASSWORD",
}


def _load_from_key_vault(vault_name: str) -> int:
    """
    Fetch secrets from Azure Key Vault and inject them into os.environ.
    Uses ManagedIdentityCredential so no passwords are needed on the VM.
    Returns the number of secrets successfully loaded.
    """
    try:
        from azure.identity import ManagedIdentityCredential, DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        from azure.core.exceptions import ResourceNotFoundError

        vault_url = f"https://{vault_name}.vault.azure.net/"

        # ManagedIdentityCredential works on the VM; DefaultAzureCredential
        # also covers local dev (az login, VS Code, etc.)
        try:
            credential = ManagedIdentityCredential()
            # Quick test – will raise if no managed identity
            credential.get_token("https://vault.azure.net/.default")
        except Exception:
            credential = DefaultAzureCredential()

        client = SecretClient(vault_url=vault_url, credential=credential)
        loaded = 0

        for kv_name, env_name in _KV_TO_ENV.items():
            # Key Vault always wins — it is the source of truth.
            # Env vars / db.env are the local-dev fallback only.
            try:
                secret = client.get_secret(kv_name)
                if secret.value:
                    os.environ[env_name] = secret.value
                    loaded += 1
            except ResourceNotFoundError:
                pass  # Secret doesn't exist yet — that's fine
            except Exception as e:
                logger.warning("KV: could not load '%s': %s", kv_name, e)

        return loaded

    except ImportError:
        logger.warning("azure-keyvault-secrets / azure-identity not installed; skipping Key Vault load.")
        return 0
    except Exception as e:
        logger.warning("Key Vault load failed (%s); falling back to environment / .env file.", e)
        return 0


# ---------------------------------------------------------------------------
# Load from Key Vault before Pydantic reads env vars
# ---------------------------------------------------------------------------
_kv_name = os.environ.get("KEY_VAULT_NAME", "kv-mindrobo-dev")
_n = _load_from_key_vault(_kv_name)
if _n:
    logger.info("Loaded %d secrets from Key Vault '%s'", _n, _kv_name)


# ---------------------------------------------------------------------------
# Pydantic Settings — reads from os.environ (now populated from KV above)
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "")
    DATABASE_URL: str
    RETELL_API_KEY: str = ""
    RETELL_WEBHOOK_SECRET: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    AZURE_STORAGE_ACCOUNT: str = ""
    KEY_VAULT_NAME: str = "kv-mindrobo-dev"

    # Azure Blob Storage
    AZURE_BLOB_CONNECTION_STRING: str = ""

    # Stripe Billing
    STRIPE_API_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID: str = ""

    # SendGrid Email
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@mindrobo.com"
    SENDGRID_FROM_NAME: str = "MindRobo"

    # GitHub
    GITHUB_WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

# Validate critical security settings
if not settings.JWT_SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY is not set. It must exist in Key Vault ('jwt-secret-key') "
        "or as a JWT_SECRET_KEY environment variable. "
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )
