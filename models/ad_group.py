from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class AdGroupStatus(str, Enum):
    ENABLED = "enabled"
    PAUSED = "paused"
    REMOVED = "removed"
    UNKNOWN = "unknown"


class AdGroup(BaseModel):
    """Einheitliches AdGroup-Model (Anzeigengruppe)"""

    id: str
    campaign_id: str
    name: str
    status: AdGroupStatus

    # Bidding
    cpc_bid_micros: Optional[int] = None  # Cost per Click in Mikro
    cpm_bid_micros: Optional[int] = None  # Cost per Mille in Mikro

    # Provider-spezifisch
    provider: str
    raw_data: Optional[dict] = None

    @property
    def cpc_euros(self) -> Optional[float]:
        if self.cpc_bid_micros:
            return self.cpc_bid_micros / 1_000_000
        return None


class AdGroupCreate(BaseModel):
    """Daten zum Erstellen einer Anzeigengruppe"""

    name: str
    cpc_bid: Optional[float] = None  # In Euro

    # Targeting (Provider-spezifisch)
    targeting: Optional[dict] = None
    settings: Optional[dict] = None
