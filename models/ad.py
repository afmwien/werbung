from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class AdStatus(str, Enum):
    ENABLED = "enabled"
    PAUSED = "paused"
    REMOVED = "removed"
    UNKNOWN = "unknown"


class AdType(str, Enum):
    TEXT = "text"
    RESPONSIVE_SEARCH = "responsive_search"
    RESPONSIVE_DISPLAY = "responsive_display"
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    UNKNOWN = "unknown"


class Ad(BaseModel):
    """Einheitliches Ad-Model (Anzeige)"""

    id: str
    ad_group_id: str
    name: Optional[str] = None
    status: AdStatus
    ad_type: AdType = AdType.UNKNOWN

    # Text-Anzeigen
    headlines: Optional[List[str]] = None
    descriptions: Optional[List[str]] = None

    # URLs
    final_urls: Optional[List[str]] = None
    display_url: Optional[str] = None

    # Media
    image_urls: Optional[List[str]] = None
    video_id: Optional[str] = None

    # Provider-spezifisch
    provider: str
    raw_data: Optional[dict] = None


class AdCreate(BaseModel):
    """Daten zum Erstellen einer Anzeige"""

    ad_type: AdType = AdType.RESPONSIVE_SEARCH

    # Text
    headlines: List[str]  # Min 3, Max 15 bei Google
    descriptions: List[str]  # Min 2, Max 4 bei Google

    # URLs
    final_url: str
    display_path1: Optional[str] = None
    display_path2: Optional[str] = None

    # Media (für Display/Video)
    image_urls: Optional[List[str]] = None
    video_id: Optional[str] = None

    settings: Optional[dict] = None
