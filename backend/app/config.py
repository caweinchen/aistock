import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "127.0.0.1")
    port: int = int(os.getenv("DB_PORT", "3306"))
    username: str = os.getenv("DB_USERNAME", "aistock")
    password: str = os.getenv("DB_PASSWORD", "AI@stock!234")
    database: str = os.getenv("DB_NAME", "ai_stock")
    dialect: str = os.getenv("DB_DIALECT", "mysql")
    driver: str = os.getenv("DB_DRIVER", "mysqlconnector")

    @property
    def url(self) -> str:
        if self.dialect == "sqlite":
            return f"sqlite:///{self.database}"
        encoded_password = urllib.parse.quote_plus(self.password)
        return f"{self.dialect}+{self.driver}://{self.username}:{encoded_password}@{self.host}:{self.port}/{self.database}"


class AppConfig:
    host: str = os.getenv("APP_HOST", "0.0.0.0")
    port: int = int(os.getenv("APP_PORT", "8000"))
    debug: bool = os.getenv("APP_DEBUG", "false").lower() == "true"


db_config = DatabaseConfig()
app_config = AppConfig()
