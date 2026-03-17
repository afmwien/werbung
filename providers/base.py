from abc import ABC, abstractmethod
from typing import List, Optional
from models.campaign import Campaign, CampaignCreate, CampaignUpdate
from models.ad_group import AdGroup
from models.ad import Ad
from models.report import PerformanceReport


class AdsProvider(ABC):
    """
    Abstrakte Basisklasse für alle Ads-Provider.

    Neue Provider (Meta, LinkedIn, TikTok etc.) müssen diese Klasse
    erweitern und alle abstrakten Methoden implementieren.
    """

    provider_name: str = "base"

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authentifizierung beim Provider"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verbindung testen"""
        pass

    # ============== CAMPAIGNS ==============

    @abstractmethod
    async def get_campaigns(self, customer_id: str) -> List[Campaign]:
        """Alle Kampagnen abrufen"""
        pass

    @abstractmethod
    async def get_campaign(self, customer_id: str, campaign_id: str) -> Optional[Campaign]:
        """Einzelne Kampagne abrufen"""
        pass

    @abstractmethod
    async def create_campaign(self, customer_id: str, campaign: CampaignCreate) -> Campaign:
        """Neue Kampagne erstellen"""
        pass

    @abstractmethod
    async def update_campaign(self, customer_id: str, campaign_id: str, campaign: CampaignUpdate) -> Campaign:
        """Kampagne aktualisieren"""
        pass

    @abstractmethod
    async def pause_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne pausieren"""
        pass

    @abstractmethod
    async def enable_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne aktivieren"""
        pass

    @abstractmethod
    async def delete_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne löschen"""
        pass

    # ============== AD GROUPS ==============

    @abstractmethod
    async def get_ad_groups(self, customer_id: str, campaign_id: str) -> List[AdGroup]:
        """Alle Anzeigengruppen einer Kampagne"""
        pass

    @abstractmethod
    async def create_ad_group(self, customer_id: str, campaign_id: str, ad_group: dict) -> AdGroup:
        """Anzeigengruppe erstellen"""
        pass

    # ============== ADS ==============

    @abstractmethod
    async def get_ads(self, customer_id: str, ad_group_id: str) -> List[Ad]:
        """Alle Anzeigen einer Anzeigengruppe"""
        pass

    @abstractmethod
    async def create_ad(self, customer_id: str, ad_group_id: str, ad: dict) -> Ad:
        """Anzeige erstellen"""
        pass

    # ============== REPORTING ==============

    @abstractmethod
    async def get_performance_report(
        self,
        customer_id: str,
        start_date: str,
        end_date: str,
        campaign_ids: Optional[List[str]] = None
    ) -> PerformanceReport:
        """Performance-Bericht abrufen"""
        pass
