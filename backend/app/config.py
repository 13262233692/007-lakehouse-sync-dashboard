import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    HIVE_METASTORE_HOST: str = "localhost"
    HIVE_METASTORE_PORT: int = 9083
    HIVE_BATCH_SIZE: int = 100
    HIVE_MAX_PARTITIONS: int = 10000
    HIVE_BATCH_SLEEP: float = 0.1

    OSS_ENDPOINT: str = ""
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET: str = ""

    TABLESTORE_ENDPOINT: str = ""
    TABLESTORE_ACCESS_KEY_ID: str = ""
    TABLESTORE_ACCESS_KEY_SECRET: str = ""
    TABLESTORE_INSTANCE: str = ""

    DATABASE_URL: str = "sqlite+aiosqlite:///./lakehouse_sync.db"
    SYNC_INTERVAL_MINUTES: int = 60
    DEBUG: bool = False


settings = Settings()
logger.info("Settings loaded successfully")
