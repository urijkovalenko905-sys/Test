from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    # ── Telegram ──
    bot_token: SecretStr
    admin_ids: list[int] = [123456789]  # Замените на реальные Telegram ID

    # ── База данных ──
    db_url: str = "sqlite+aiosqlite:///school_bot.db"

    # ── AI-ассистент (DeepSeek) ──
    # Получить ключ: https://platform.deepseek.com → API Keys
    # Добавить в .env: DEEPSEEK_API_KEY=sk-...
    deepseek_api_key: str = ""

    # ── Telegram Mini App ──
    # Публичный URL вашего webapp/index.html (GitHub Pages, Vercel и т.д.)
    # Добавить в .env: WEBAPP_URL=https://your-domain.com/webapp/
    webapp_url: str = ""

    # ── Класс по умолчанию ──
    default_grade: str = "9"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


config = Settings()
