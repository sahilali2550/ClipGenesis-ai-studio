import os
import shutil
import socket
import toml
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
CONFIG_FILE = os.path.join(ROOT_DIR, "config.toml")
EXAMPLE_FILE = os.path.join(ROOT_DIR, "config.example.toml")


class AppConfig(BaseModel):
    project_name: str = "ClipGenesis"
    project_version: str = "1.2.6"
    project_description: str = "AI Video Production Studio Engine"
    log_level: str = "DEBUG"
    listen_host: str = "0.0.0.0"
    listen_port: int = 8080
    imagemagick_path: str = ""
    ffmpeg_path: str = ""
    video_source: str = "pexels"
    subtitle_provider: str = "edge"


class AzureConfig(BaseModel):
    speech_key: str = ""
    speech_region: str = ""


class SiliconFlowConfig(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"


class WhisperConfig(BaseModel):
    model: str = "base"


class UIConfig(BaseModel):
    hide_log: bool = False
    language: str = "en-US"
    theme: str = "dark"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__"
    )

    app: AppConfig = Field(default_factory=AppConfig)
    azure: AzureConfig = Field(default_factory=AzureConfig)
    siliconflow: SiliconFlowConfig = Field(default_factory=SiliconFlowConfig)
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    @classmethod
    def load_from_toml(cls, file_path: str = CONFIG_FILE) -> "Settings":
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)

        if not os.path.isfile(file_path) and os.path.isfile(EXAMPLE_FILE):
            shutil.copyfile(EXAMPLE_FILE, file_path)
            logger.info("Copied config.example.toml to config.toml")

        raw_data: Dict[str, Any] = {}
        if os.path.isfile(file_path):
            try:
                raw_data = toml.load(file_path)
            except Exception:
                with open(file_path, mode="r", encoding="utf-8-sig") as fp:
                    raw_data = toml.loads(fp.read())

        # Construct typed settings instance
        return cls(
            app=AppConfig(**raw_data.get("app", {})),
            azure=AzureConfig(**raw_data.get("azure", {})),
            siliconflow=SiliconFlowConfig(**raw_data.get("siliconflow", {})),
            whisper=WhisperConfig(**raw_data.get("whisper", {})),
            ui=UIConfig(**raw_data.get("ui", {})),
        )

    def save_to_toml(self, file_path: str = CONFIG_FILE) -> None:
        data = {
            "app": self.app.model_dump(),
            "azure": self.azure.model_dump(),
            "siliconflow": self.siliconflow.model_dump(),
            "whisper": self.whisper.model_dump(),
            "ui": self.ui.model_dump(),
        }
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(toml.dumps(data))


# Global settings singleton
settings = Settings.load_from_toml()
