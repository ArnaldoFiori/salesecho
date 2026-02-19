import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_SECRET: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Stripe
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_ID: str = os.getenv("STRIPE_PRICE_ID", "")

    # Resend
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")

    # Audio
    AUDIO_TEMP_DIR: str = os.getenv("AUDIO_TEMP_DIR", "/tmp/salesecho/audio")
    AUDIO_TTL_HOURS: int = int(os.getenv("AUDIO_TTL_HOURS", "24"))

    # URLs
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    # Alertas
    ADMIN_TELEGRAM_CHAT_ID: str = os.getenv("ADMIN_TELEGRAM_CHAT_ID", "")
    ALERT_ENABLED: bool = os.getenv("ALERT_ENABLED", "false").lower() == "true"


settings = Settings()
