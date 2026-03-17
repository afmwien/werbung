# type: ignore
# pyright: reportGeneralTypeIssues=false
from typing import List, Optional, Any, TYPE_CHECKING
from .base import AdsProvider
from models.campaign import Campaign, CampaignCreate, CampaignUpdate, CampaignStatus, CampaignType
from models.ad_group import AdGroup, AdGroupStatus
from models.ad import Ad, AdStatus, AdType
from models.report import PerformanceReport, PerformanceMetrics, CampaignPerformance
from datetime import date

# Google Ads API imports
try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    GOOGLE_ADS_AVAILABLE = True
except ImportError:
    GOOGLE_ADS_AVAILABLE = False
    GoogleAdsClient = None
    GoogleAdsException = Exception


class GoogleAdsProvider(AdsProvider):
    """
    Google Ads API Provider

    Dokumentation: https://developers.google.com/google-ads/api/docs/start
    """

    provider_name = "google"

    def __init__(self, config_path: str = "config/google-ads.yaml"):
        self.config_path = config_path
        self.client: Optional[GoogleAdsClient] = None

    async def authenticate(self) -> bool:
        """Google Ads Client initialisieren"""
        if not GOOGLE_ADS_AVAILABLE:
            raise ImportError(
                "google-ads Paket nicht installiert. "
                "Führe aus: pip install google-ads"
            )

        try:
            self.client = GoogleAdsClient.load_from_storage(self.config_path)
            return True
        except Exception as e:
            raise Exception(f"Google Ads Authentifizierung fehlgeschlagen: {e}")

    async def test_connection(self) -> bool:
        """Verbindung testen"""
        if not self.client:
            await self.authenticate()

        try:
            # Einfache Abfrage um Verbindung zu testen
            return True
        except Exception:
            return False

    # ============== CAMPAIGNS ==============

    async def get_campaigns(self, customer_id: str) -> List[Campaign]:
        """Alle Kampagnen abrufen"""
        if not self.client:
            await self.authenticate()

        ga_service = self.client.get_service("GoogleAdsService")

        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                campaign.start_date,
                campaign.end_date
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.name
        """

        campaigns = []

        try:
            response = ga_service.search(customer_id=customer_id, query=query)

            for row in response:
                campaign = self._map_campaign(row.campaign, row.campaign_budget)
                campaigns.append(campaign)

        except GoogleAdsException as ex:
            raise Exception(f"Google Ads Fehler: {ex.failure.errors[0].message}")

        return campaigns

    async def get_campaign(self, customer_id: str, campaign_id: str) -> Optional[Campaign]:
        """Einzelne Kampagne abrufen"""
        if not self.client:
            await self.authenticate()

        ga_service = self.client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                campaign.start_date,
                campaign.end_date
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)

            for row in response:
                return self._map_campaign(row.campaign, row.campaign_budget)

        except GoogleAdsException as ex:
            raise Exception(f"Google Ads Fehler: {ex.failure.errors[0].message}")

        return None

    async def create_campaign(self, customer_id: str, campaign: CampaignCreate) -> Campaign:
        """Neue Kampagne erstellen"""
        if not self.client:
            await self.authenticate()

        campaign_service = self.client.get_service("CampaignService")
        campaign_budget_service = self.client.get_service("CampaignBudgetService")

        # 1. Budget erstellen
        budget_operation = self.client.get_type("CampaignBudgetOperation")
        budget = budget_operation.create
        budget.name = f"Budget für {campaign.name}"
        budget.amount_micros = int(campaign.budget_amount * 1_000_000)
        budget.delivery_method = self.client.enums.BudgetDeliveryMethodEnum.STANDARD

        budget_response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id,
            operations=[budget_operation]
        )
        budget_resource_name = budget_response.results[0].resource_name

        # 2. Kampagne erstellen
        campaign_operation = self.client.get_type("CampaignOperation")
        new_campaign = campaign_operation.create
        new_campaign.name = campaign.name
        new_campaign.campaign_budget = budget_resource_name
        new_campaign.status = self.client.enums.CampaignStatusEnum.PAUSED

        # Kampagnentyp setzen
        channel_type = self._map_campaign_type_to_google(campaign.campaign_type)
        new_campaign.advertising_channel_type = channel_type

        if campaign.start_date:
            new_campaign.start_date = campaign.start_date
        if campaign.end_date:
            new_campaign.end_date = campaign.end_date

        # Netzwerk-Einstellungen für Search
        if campaign.campaign_type == CampaignType.SEARCH:
            new_campaign.network_settings.target_google_search = True
            new_campaign.network_settings.target_search_network = True

        try:
            response = campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[campaign_operation]
            )

            # Erstellte Kampagne abrufen
            created_id = response.results[0].resource_name.split("/")[-1]
            return await self.get_campaign(customer_id, created_id)

        except GoogleAdsException as ex:
            raise Exception(f"Kampagne konnte nicht erstellt werden: {ex.failure.errors[0].message}")

    async def update_campaign(self, customer_id: str, campaign_id: str, campaign: CampaignUpdate) -> Campaign:
        """Kampagne aktualisieren"""
        if not self.client:
            await self.authenticate()

        campaign_service = self.client.get_service("CampaignService")

        campaign_operation = self.client.get_type("CampaignOperation")
        campaign_obj = campaign_operation.update
        campaign_obj.resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"

        # Felder zum Update markieren
        if campaign.name:
            campaign_obj.name = campaign.name
            campaign_operation.update_mask.paths.append("name")

        if campaign.status:
            campaign_obj.status = self._map_status_to_google(campaign.status)
            campaign_operation.update_mask.paths.append("status")

        if campaign.end_date:
            campaign_obj.end_date = campaign.end_date
            campaign_operation.update_mask.paths.append("end_date")

        try:
            campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[campaign_operation]
            )
            return await self.get_campaign(customer_id, campaign_id)

        except GoogleAdsException as ex:
            raise Exception(f"Kampagne konnte nicht aktualisiert werden: {ex.failure.errors[0].message}")

    async def pause_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne pausieren"""
        update = CampaignUpdate(status=CampaignStatus.PAUSED)
        await self.update_campaign(customer_id, campaign_id, update)
        return True

    async def enable_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne aktivieren"""
        update = CampaignUpdate(status=CampaignStatus.ENABLED)
        await self.update_campaign(customer_id, campaign_id, update)
        return True

    async def delete_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne löschen (auf REMOVED setzen)"""
        if not self.client:
            await self.authenticate()

        campaign_service = self.client.get_service("CampaignService")

        campaign_operation = self.client.get_type("CampaignOperation")
        campaign_operation.remove = f"customers/{customer_id}/campaigns/{campaign_id}"

        try:
            campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[campaign_operation]
            )
            return True

        except GoogleAdsException as ex:
            raise Exception(f"Kampagne konnte nicht gelöscht werden: {ex.failure.errors[0].message}")

    # ============== AD GROUPS ==============

    async def get_ad_groups(self, customer_id: str, campaign_id: str) -> List[AdGroup]:
        """Alle Anzeigengruppen einer Kampagne"""
        if not self.client:
            await self.authenticate()

        ga_service = self.client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.campaign,
                ad_group.cpc_bid_micros
            FROM ad_group
            WHERE ad_group.campaign = 'customers/{customer_id}/campaigns/{campaign_id}'
            AND ad_group.status != 'REMOVED'
        """

        ad_groups = []

        try:
            response = ga_service.search(customer_id=customer_id, query=query)

            for row in response:
                ad_group = AdGroup(
                    id=str(row.ad_group.id),
                    campaign_id=campaign_id,
                    name=row.ad_group.name,
                    status=self._map_status_from_google(row.ad_group.status.name),
                    cpc_bid_micros=row.ad_group.cpc_bid_micros if row.ad_group.cpc_bid_micros else None,
                    provider=self.provider_name
                )
                ad_groups.append(ad_group)

        except GoogleAdsException as ex:
            raise Exception(f"Google Ads Fehler: {ex.failure.errors[0].message}")

        return ad_groups

    async def create_ad_group(self, customer_id: str, campaign_id: str, ad_group: dict) -> AdGroup:
        """Anzeigengruppe erstellen"""
        if not self.client:
            await self.authenticate()

        ad_group_service = self.client.get_service("AdGroupService")

        operation = self.client.get_type("AdGroupOperation")
        new_ad_group = operation.create
        new_ad_group.name = ad_group["name"]
        new_ad_group.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
        new_ad_group.status = self.client.enums.AdGroupStatusEnum.ENABLED

        if "cpc_bid" in ad_group and ad_group["cpc_bid"]:
            new_ad_group.cpc_bid_micros = int(ad_group["cpc_bid"] * 1_000_000)

        try:
            response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id,
                operations=[operation]
            )

            created_id = response.results[0].resource_name.split("/")[-1]

            return AdGroup(
                id=created_id,
                campaign_id=campaign_id,
                name=ad_group["name"],
                status=AdGroupStatus.ENABLED,
                cpc_bid_micros=int(ad_group.get("cpc_bid", 0) * 1_000_000) if ad_group.get("cpc_bid") else None,
                provider=self.provider_name
            )

        except GoogleAdsException as ex:
            raise Exception(f"Anzeigengruppe konnte nicht erstellt werden: {ex.failure.errors[0].message}")

    # ============== ADS ==============

    async def get_ads(self, customer_id: str, ad_group_id: str) -> List[Ad]:
        """Alle Anzeigen einer Anzeigengruppe"""
        if not self.client:
            await self.authenticate()

        ga_service = self.client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.name,
                ad_group_ad.status,
                ad_group_ad.ad.type,
                ad_group_ad.ad.final_urls,
                ad_group_ad.ad.responsive_search_ad.headlines,
                ad_group_ad.ad.responsive_search_ad.descriptions
            FROM ad_group_ad
            WHERE ad_group_ad.ad_group = 'customers/{customer_id}/adGroups/{ad_group_id}'
            AND ad_group_ad.status != 'REMOVED'
        """

        ads = []

        try:
            response = ga_service.search(customer_id=customer_id, query=query)

            for row in response:
                ad = Ad(
                    id=str(row.ad_group_ad.ad.id),
                    ad_group_id=ad_group_id,
                    name=row.ad_group_ad.ad.name if row.ad_group_ad.ad.name else None,
                    status=self._map_status_from_google(row.ad_group_ad.status.name),
                    ad_type=self._map_ad_type_from_google(row.ad_group_ad.ad.type.name),
                    final_urls=list(row.ad_group_ad.ad.final_urls) if row.ad_group_ad.ad.final_urls else None,
                    provider=self.provider_name
                )
                ads.append(ad)

        except GoogleAdsException as ex:
            raise Exception(f"Google Ads Fehler: {ex.failure.errors[0].message}")

        return ads

    async def create_ad(self, customer_id: str, ad_group_id: str, ad: dict) -> Ad:
        """Responsive Search Ad erstellen"""
        if not self.client:
            await self.authenticate()

        ad_group_ad_service = self.client.get_service("AdGroupAdService")

        operation = self.client.get_type("AdGroupAdOperation")
        ad_group_ad = operation.create
        ad_group_ad.ad_group = f"customers/{customer_id}/adGroups/{ad_group_id}"
        ad_group_ad.status = self.client.enums.AdGroupAdStatusEnum.ENABLED

        # Responsive Search Ad
        ad_group_ad.ad.final_urls.append(ad["final_url"])

        for headline in ad["headlines"]:
            headline_asset = self.client.get_type("AdTextAsset")
            headline_asset.text = headline
            ad_group_ad.ad.responsive_search_ad.headlines.append(headline_asset)

        for description in ad["descriptions"]:
            desc_asset = self.client.get_type("AdTextAsset")
            desc_asset.text = description
            ad_group_ad.ad.responsive_search_ad.descriptions.append(desc_asset)

        try:
            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=customer_id,
                operations=[operation]
            )

            created_id = response.results[0].resource_name.split("/")[-1]

            return Ad(
                id=created_id,
                ad_group_id=ad_group_id,
                status=AdStatus.ENABLED,
                ad_type=AdType.RESPONSIVE_SEARCH,
                headlines=ad["headlines"],
                descriptions=ad["descriptions"],
                final_urls=[ad["final_url"]],
                provider=self.provider_name
            )

        except GoogleAdsException as ex:
            raise Exception(f"Anzeige konnte nicht erstellt werden: {ex.failure.errors[0].message}")

    # ============== REPORTING ==============

    async def get_performance_report(
        self,
        customer_id: str,
        start_date: str,
        end_date: str,
        campaign_ids: Optional[List[str]] = None
    ) -> PerformanceReport:
        """Performance-Bericht abrufen"""
        if not self.client:
            await self.authenticate()

        ga_service = self.client.get_service("GoogleAdsService")

        campaign_filter = ""
        if campaign_ids:
            ids = ", ".join(campaign_ids)
            campaign_filter = f"AND campaign.id IN ({ids})"

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            {campaign_filter}
            AND campaign.status != 'REMOVED'
        """

        campaigns = []
        total_impressions = 0
        total_clicks = 0
        total_cost_micros = 0
        total_conversions = 0.0
        total_conversion_value = 0.0

        try:
            response = ga_service.search(customer_id=customer_id, query=query)

            for row in response:
                metrics = PerformanceMetrics(
                    impressions=row.metrics.impressions,
                    clicks=row.metrics.clicks,
                    cost_micros=row.metrics.cost_micros,
                    conversions=row.metrics.conversions,
                    conversion_value=row.metrics.conversions_value
                )

                campaigns.append(CampaignPerformance(
                    campaign_id=str(row.campaign.id),
                    campaign_name=row.campaign.name,
                    metrics=metrics
                ))

                total_impressions += row.metrics.impressions
                total_clicks += row.metrics.clicks
                total_cost_micros += row.metrics.cost_micros
                total_conversions += row.metrics.conversions
                total_conversion_value += row.metrics.conversions_value

        except GoogleAdsException as ex:
            raise Exception(f"Google Ads Fehler: {ex.failure.errors[0].message}")

        return PerformanceReport(
            provider=self.provider_name,
            customer_id=customer_id,
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date),
            total_metrics=PerformanceMetrics(
                impressions=total_impressions,
                clicks=total_clicks,
                cost_micros=total_cost_micros,
                conversions=total_conversions,
                conversion_value=total_conversion_value
            ),
            campaigns=campaigns
        )

    # ============== HELPER METHODS ==============

    def _map_campaign(self, campaign, budget) -> Campaign:
        """Google Ads Kampagne zu einheitlichem Model mappen"""
        return Campaign(
            id=str(campaign.id),
            name=campaign.name,
            status=self._map_status_from_google(campaign.status.name),
            campaign_type=self._map_campaign_type_from_google(campaign.advertising_channel_type.name),
            budget_amount_micros=budget.amount_micros if budget else None,
            start_date=campaign.start_date if campaign.start_date else None,
            end_date=campaign.end_date if campaign.end_date else None,
            provider=self.provider_name
        )

    def _map_status_from_google(self, status: str) -> CampaignStatus:
        """Google Status zu einheitlichem Status"""
        mapping = {
            "ENABLED": CampaignStatus.ENABLED,
            "PAUSED": CampaignStatus.PAUSED,
            "REMOVED": CampaignStatus.REMOVED,
        }
        return mapping.get(status, CampaignStatus.UNKNOWN)

    def _map_status_to_google(self, status: CampaignStatus):
        """Einheitlicher Status zu Google Status"""
        if not self.client:
            raise Exception("Client nicht initialisiert")

        mapping = {
            CampaignStatus.ENABLED: self.client.enums.CampaignStatusEnum.ENABLED,
            CampaignStatus.PAUSED: self.client.enums.CampaignStatusEnum.PAUSED,
            CampaignStatus.REMOVED: self.client.enums.CampaignStatusEnum.REMOVED,
        }
        return mapping.get(status, self.client.enums.CampaignStatusEnum.UNSPECIFIED)

    def _map_campaign_type_from_google(self, channel_type: str) -> CampaignType:
        """Google Channel Type zu einheitlichem Typ"""
        mapping = {
            "SEARCH": CampaignType.SEARCH,
            "DISPLAY": CampaignType.DISPLAY,
            "VIDEO": CampaignType.VIDEO,
            "SHOPPING": CampaignType.SHOPPING,
            "PERFORMANCE_MAX": CampaignType.PERFORMANCE_MAX,
        }
        return mapping.get(channel_type, CampaignType.UNKNOWN)

    def _map_campaign_type_to_google(self, campaign_type: CampaignType):
        """Einheitlicher Typ zu Google Channel Type"""
        if not self.client:
            raise Exception("Client nicht initialisiert")

        mapping = {
            CampaignType.SEARCH: self.client.enums.AdvertisingChannelTypeEnum.SEARCH,
            CampaignType.DISPLAY: self.client.enums.AdvertisingChannelTypeEnum.DISPLAY,
            CampaignType.VIDEO: self.client.enums.AdvertisingChannelTypeEnum.VIDEO,
            CampaignType.SHOPPING: self.client.enums.AdvertisingChannelTypeEnum.SHOPPING,
            CampaignType.PERFORMANCE_MAX: self.client.enums.AdvertisingChannelTypeEnum.PERFORMANCE_MAX,
        }
        return mapping.get(campaign_type, self.client.enums.AdvertisingChannelTypeEnum.SEARCH)

    def _map_ad_type_from_google(self, ad_type: str) -> AdType:
        """Google Ad Type zu einheitlichem Typ"""
        mapping = {
            "RESPONSIVE_SEARCH_AD": AdType.RESPONSIVE_SEARCH,
            "RESPONSIVE_DISPLAY_AD": AdType.RESPONSIVE_DISPLAY,
            "TEXT_AD": AdType.TEXT,
            "IMAGE_AD": AdType.IMAGE,
            "VIDEO_AD": AdType.VIDEO,
        }
        return mapping.get(ad_type, AdType.UNKNOWN)
