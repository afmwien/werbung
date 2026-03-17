from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime


class CampaignStatus(str, Enum):
    ENABLED = "enabled"
    PAUSED = "paused"
    REMOVED = "removed"
    UNKNOWN = "unknown"


class CampaignType(str, Enum):
    SEARCH = "search"
    DISPLAY = "display"
    VIDEO = "video"
    SHOPPING = "shopping"
    PERFORMANCE_MAX = "performance_max"
    UNKNOWN = "unknown"


class Campaign(BaseModel):
    """Einheitliches Kampagnen-Model für alle Provider"""

    id: str
    name: str
    status: CampaignStatus
    campaign_type: CampaignType = CampaignType.UNKNOWN

    # Budget
    budget_amount_micros: Optional[int] = None  # In Mikro-Einheiten (1€ = 1.000.000)
    budget_amount: Optional[float] = None       # In normaler Währung

    # Dates
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Provider-spezifisch
    provider: str  # "google", "meta", "linkedin" etc.
    raw_data: Optional[dict] = None  # Original-Daten vom Provider

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def budget_euros(self) -> Optional[float]:
        """Budget in Euro"""
        if self.budget_amount_micros:
            return self.budget_amount_micros / 1_000_000
        return self.budget_amount


class CampaignCreate(BaseModel):
    """Daten zum Erstellen einer Kampagne"""

    name: str
    campaign_type: CampaignType = CampaignType.SEARCH
    budget_amount: float  # Tagesbudget in Euro
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Optional: Provider-spezifische Einstellungen
    settings: Optional[dict] = None


class CampaignUpdate(BaseModel):
    """Daten zum Aktualisieren einer Kampagne"""

    name: Optional[str] = None
    status: Optional[CampaignStatus] = None
    budget_amount: Optional[float] = None
    end_date: Optional[str] = None
    settings: Optional[dict] = None
