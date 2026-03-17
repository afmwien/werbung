"""Ads Manager service - central management for all ad providers."""
# pylint: disable=invalid-name,too-many-arguments,too-many-positional-arguments
from typing import Dict, List, Optional

from models.campaign import Campaign, CampaignCreate, CampaignUpdate
from models.report import PerformanceReport
from providers.base import AdsProvider
from providers.google_ads import GoogleAdsProvider
from providers.meta_ads import MetaAdsProvider
from config.settings import settings


class AdsManager:
    """
    Zentraler Manager für alle Ads-Provider

    Ermöglicht einheitlichen Zugriff auf verschiedene Werbeplattformen
    über eine gemeinsame Schnittstelle.
    """

    def __init__(self):
        self._providers: Dict[str, AdsProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Verfügbare Provider initialisieren"""

        # Google Ads
        self._providers["google"] = GoogleAdsProvider()

        # Meta Ads
        self._providers["meta"] = MetaAdsProvider(
            app_id=settings.META_APP_ID,
            app_secret=settings.META_APP_SECRET,
            access_token=settings.META_ACCESS_TOKEN
        )

        # LinkedIn Ads (später hinzufügen)
        # self._providers["linkedin"] = LinkedInAdsProvider()

        # TikTok Ads (später hinzufügen)
        # self._providers["tiktok"] = TikTokAdsProvider()

    def get_provider(self, provider_name: str) -> AdsProvider:
        """Provider nach Name abrufen"""
        provider = self._providers.get(provider_name.lower())
        if not provider:
            available = ", ".join(self._providers.keys())
            raise ValueError(
                f"Provider '{provider_name}' nicht verfügbar. "
                f"Verfügbare Provider: {available}"
            )
        return provider

    def list_providers(self) -> List[str]:
        """Liste aller verfügbaren Provider"""
        return list(self._providers.keys())

    # ============== CAMPAIGN METHODS ==============

    async def get_campaigns(self, provider: str, customer_id: str) -> List[Campaign]:
        """Kampagnen von einem Provider abrufen"""
        p = self.get_provider(provider)
        return await p.get_campaigns(customer_id)

    async def get_campaign(self, provider: str, customer_id: str, campaign_id: str) -> Optional[Campaign]:
        """Einzelne Kampagne abrufen"""
        p = self.get_provider(provider)
        return await p.get_campaign(customer_id, campaign_id)

    async def create_campaign(self, provider: str, customer_id: str, campaign: CampaignCreate) -> Campaign:
        """Kampagne erstellen"""
        p = self.get_provider(provider)
        return await p.create_campaign(customer_id, campaign)

    async def update_campaign(
        self, provider: str, customer_id: str, campaign_id: str, campaign: CampaignUpdate
    ) -> Campaign:
        """Kampagne aktualisieren"""
        p = self.get_provider(provider)
        return await p.update_campaign(customer_id, campaign_id, campaign)

    async def pause_campaign(self, provider: str, customer_id: str, campaign_id: str) -> bool:
        """Kampagne pausieren"""
        p = self.get_provider(provider)
        return await p.pause_campaign(customer_id, campaign_id)

    async def enable_campaign(self, provider: str, customer_id: str, campaign_id: str) -> bool:
        """Kampagne aktivieren"""
        p = self.get_provider(provider)
        return await p.enable_campaign(customer_id, campaign_id)

    async def delete_campaign(self, provider: str, customer_id: str, campaign_id: str) -> bool:
        """Kampagne löschen"""
        p = self.get_provider(provider)
        return await p.delete_campaign(customer_id, campaign_id)

    # ============== AD GROUP METHODS ==============

    async def get_ad_groups(self, provider: str, customer_id: str, campaign_id: str):
        """Anzeigengruppen einer Kampagne abrufen"""
        p = self.get_provider(provider)
        return await p.get_ad_groups(customer_id, campaign_id)

    async def create_ad_group(self, provider: str, customer_id: str, campaign_id: str, ad_group: dict):
        """Anzeigengruppe erstellen"""
        p = self.get_provider(provider)
        return await p.create_ad_group(customer_id, campaign_id, ad_group)

    # ============== AD METHODS ==============

    async def get_ads(self, provider: str, customer_id: str, ad_group_id: str):
        """Anzeigen einer Anzeigengruppe abrufen"""
        p = self.get_provider(provider)
        return await p.get_ads(customer_id, ad_group_id)

    async def create_ad(self, provider: str, customer_id: str, ad_group_id: str, ad: dict):
        """Anzeige erstellen"""
        p = self.get_provider(provider)
        return await p.create_ad(customer_id, ad_group_id, ad)

    # ============== REPORT METHODS ==============

    async def get_performance_report(
        self,
        provider: str,
        customer_id: str,
        start_date: str,
        end_date: str,
        campaign_ids: Optional[List[str]] = None
    ) -> PerformanceReport:
        """Performance-Bericht abrufen"""
        p = self.get_provider(provider)
        return await p.get_performance_report(customer_id, start_date, end_date, campaign_ids)


# Singleton instance
_ads_manager: Optional[AdsManager] = None


def get_ads_manager() -> AdsManager:
    """Dependency für FastAPI - gibt Singleton AdsManager zurück"""
    global _ads_manager  # pylint: disable=global-statement
    if _ads_manager is None:
        _ads_manager = AdsManager()
    return _ads_manager
