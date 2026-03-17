from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class PerformanceMetrics(BaseModel):
    """Performance-Metriken für einen Zeitraum"""

    # Grundmetriken
    impressions: int = 0
    clicks: int = 0
    cost_micros: int = 0

    # Conversions
    conversions: float = 0.0
    conversion_value: float = 0.0

    # Berechnete Metriken
    @property
    def cost(self) -> float:
        """Kosten in Euro"""
        return self.cost_micros / 1_000_000

    @property
    def ctr(self) -> float:
        """Click-Through-Rate in %"""
        if self.impressions > 0:
            return (self.clicks / self.impressions) * 100
        return 0.0

    @property
    def cpc(self) -> float:
        """Cost per Click in Euro"""
        if self.clicks > 0:
            return self.cost / self.clicks
        return 0.0

    @property
    def conversion_rate(self) -> float:
        """Conversion Rate in %"""
        if self.clicks > 0:
            return (self.conversions / self.clicks) * 100
        return 0.0

    @property
    def cost_per_conversion(self) -> float:
        """Kosten pro Conversion in Euro"""
        if self.conversions > 0:
            return self.cost / self.conversions
        return 0.0

    @property
    def roas(self) -> float:
        """Return on Ad Spend"""
        if self.cost > 0:
            return self.conversion_value / self.cost
        return 0.0


class CampaignPerformance(BaseModel):
    """Performance einer einzelnen Kampagne"""

    campaign_id: str
    campaign_name: str
    metrics: PerformanceMetrics


class PerformanceReport(BaseModel):
    """Gesamter Performance-Bericht"""

    provider: str
    customer_id: str
    start_date: date
    end_date: date

    # Gesamt-Metriken
    total_metrics: PerformanceMetrics

    # Pro Kampagne
    campaigns: List[CampaignPerformance] = []

    # Optional: Tägliche Aufschlüsselung
    daily_metrics: Optional[List[dict]] = None
