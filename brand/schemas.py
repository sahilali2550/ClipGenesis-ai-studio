from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class BrandColors(BaseModel):
    primary: str = "#FF6B35"
    secondary: str = "#00E5A0"
    background: str = "#161616"
    text: str = "#FFFFFF"


class BrandFonts(BaseModel):
    title_font: str = "MicrosoftYaHeiBold.ttc"
    subtitle_font: str = "arial.ttf"


class BrandKit(BaseModel):
    brand_id: str
    name: str
    description: str = ""
    logo_path: str = ""
    logo_position: str = "top_right"
    logo_size: int = 120
    logo_opacity: float = 0.90
    watermark_enabled: bool = True
    watermark_text: str = ""
    watermark_position: str = "bottom_right"
    watermark_color: str = "#FFFFFF"
    colors: BrandColors = Field(default_factory=BrandColors)
    fonts: BrandFonts = Field(default_factory=BrandFonts)
    intro_video: str = ""
    outro_video: str = ""
