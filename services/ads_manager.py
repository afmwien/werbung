"""Ads Manager service - central management for all ad providers."""
# pylint: disable=invalid-name,too-many-arguments,too-many-positional-arguments
from typing import Dict, List, Optional

from models.campaign import Campaign, CampaignCreate, CampaignUpdate
from models.report import PerformanceReport
from providers.base import AdsProvider
from providers.google_ads import GoogleAdsProvider
from providers.meta_ads import MetaAdsProvider
from providers.linkedin_ads import LinkedInAdsProvider
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

        # LinkedIn Ads
        self._providers["linkedin"] = LinkedInAdsProvider(
            access_token=settings.LINKEDIN_ACCESS_TOKEN,
            ad_account_id=settings.LINKEDIN_AD_ACCOUNT_ID
        )

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

    async def get_campaign_preview(self, provider: str, customer_id: str, campaign_id: str) -> dict:
        """Kampagnen-Vorschau mit allen Anzeigen abrufen"""
        p = self.get_provider(provider)

        preview = {
            "campaign_id": campaign_id,
            "provider": provider,
            "ad_groups": [],
            "ads": [],
            "total_ads": 0
        }

        try:
            # Kampagne abrufen
            campaign = await p.get_campaign(customer_id, campaign_id)
            if campaign:
                preview["campaign"] = {
                    "id": campaign.id,
                    "name": campaign.name,
                    "status": campaign.status,
                    "type": campaign.campaign_type
                }

            # Ad-Gruppen und Ads abrufen
            ad_groups = await p.get_ad_groups(customer_id, campaign_id)

            for ad_group in ad_groups:
                ag_data = {
                    "id": ad_group.id,
                    "name": ad_group.name,
                    "status": ad_group.status,
                    "ads": []
                }

                # Ads für diese Ad-Gruppe
                ads = await p.get_ads(customer_id, ad_group.id)
                for ad in ads:
                    ad_data = {
                        "id": ad.id,
                        "name": ad.name,
                        "status": ad.status,
                        "type": ad.ad_type,
                        "headlines": ad.headlines,
                        "descriptions": ad.descriptions,
                        "final_urls": ad.final_urls,
                        "image_url": ad.image_urls[0] if ad.image_urls else None,
                        "image_urls": ad.image_urls,
                        "video_id": ad.video_id,
                        "raw_data": ad.raw_data
                    }
                    ag_data["ads"].append(ad_data)
                    preview["ads"].append(ad_data)

                preview["ad_groups"].append(ag_data)

            preview["total_ads"] = len(preview["ads"])

        except Exception as e:
            preview["error"] = str(e)

        return preview

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
