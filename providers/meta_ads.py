"""Meta (Facebook/Instagram) Ads API provider implementation."""
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportAttributeAccessIssue=false
# pylint: disable=broad-exception-caught,broad-exception-raised,too-many-locals
from typing import Any, List, Optional

from models.ad import Ad, AdStatus, AdType
from models.ad_group import AdGroup, AdGroupStatus
from models.campaign import Campaign, CampaignCreate, CampaignUpdate, CampaignStatus, CampaignType
from models.report import CampaignPerformance, PerformanceMetrics, PerformanceReport

from .base import AdsProvider


class MetaAdsError(Exception):
    """Custom exception for Meta Ads API errors."""


# Meta Business SDK imports
try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign as FBCampaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad as FBAd
    from facebook_business.adobjects.adsinsights import AdsInsights
    from facebook_business.exceptions import FacebookRequestError
    META_ADS_AVAILABLE = True
except ImportError:
    META_ADS_AVAILABLE = False
    FacebookAdsApi: Any = None
    AdAccount: Any = None
    FBCampaign: Any = None
    AdSet: Any = None
    FBAd: Any = None
    AdsInsights: Any = None
    FacebookRequestError: Any = Exception


class MetaAdsProvider(AdsProvider):
    """
    Meta (Facebook/Instagram) Ads API Provider

    Unterstützt mehrere Ad Accounts für die Verwaltung verschiedener Kunden.

    Dokumentation: https://developers.facebook.com/docs/marketing-apis/

    Authentifizierung:
        - App ID & App Secret von developers.facebook.com
        - Access Token (System User Token empfohlen für Server-Apps)

    customer_id Format: act_XXXXXXXXXX (Ad Account ID mit "act_" Prefix)
    """

    provider_name = "meta"

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        access_token: Optional[str] = None
    ):
        """
        Meta Ads Provider initialisieren

        Args:
            app_id: Facebook App ID
            app_secret: Facebook App Secret
            access_token: Access Token (System User oder User Token)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = access_token
        self._initialized = False

    async def authenticate(self) -> bool:
        """Facebook Ads API initialisieren"""
        if not META_ADS_AVAILABLE:
            raise ImportError(
                "facebook-business Paket nicht installiert. "
                "Führe aus: pip install facebook-business"
            )

        if not self.access_token:
            raise MetaAdsError(
                "Meta Ads Access Token fehlt. "
                "Setze META_ACCESS_TOKEN in der .env Datei."
            )

        try:
            FacebookAdsApi.init(
                app_id=self.app_id,
                app_secret=self.app_secret,
                access_token=self.access_token
            )
            self._initialized = True
            return True
        except Exception as e:
            raise MetaAdsError(f"Meta Ads Authentifizierung fehlgeschlagen: {e}") from e

    async def test_connection(self) -> bool:
        """Verbindung testen"""
        if not self._initialized:
            await self.authenticate()

        try:
            # Einfache API-Abfrage um Verbindung zu testen
            from facebook_business.adobjects.user import User
            me = User(fbid='me')
            me.api_get(fields=['id', 'name'])
            return True
        except Exception:
            return False

    def _ensure_act_prefix(self, customer_id: str) -> str:
        """Stellt sicher, dass die Ad Account ID das 'act_' Prefix hat"""
        if not customer_id.startswith("act_"):
            return f"act_{customer_id}"
        return customer_id

    # ============== CAMPAIGNS ==============

    async def get_campaigns(self, customer_id: str) -> List[Campaign]:
        """Alle Kampagnen eines Ad Accounts abrufen"""
        if not self._initialized:
            await self.authenticate()

        account_id = self._ensure_act_prefix(customer_id)
        campaigns = []

        try:
            account = AdAccount(account_id)
            fb_campaigns = account.get_campaigns(
                fields=[
                    FBCampaign.Field.id,
                    FBCampaign.Field.name,
                    FBCampaign.Field.status,
                    FBCampaign.Field.objective,
                    FBCampaign.Field.daily_budget,
                    FBCampaign.Field.lifetime_budget,
                    FBCampaign.Field.created_time,
                    FBCampaign.Field.updated_time,
                ]
            )

            for fb_campaign in fb_campaigns:
                campaign = self._map_campaign(fb_campaign)
                campaigns.append(campaign)

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Meta Ads Fehler: {ex.api_error_message()}") from ex

        return campaigns

    async def get_campaign(self, customer_id: str, campaign_id: str) -> Optional[Campaign]:
        """Einzelne Kampagne abrufen"""
        if not self._initialized:
            await self.authenticate()

        try:
            fb_campaign = FBCampaign(campaign_id)
            fb_campaign.api_get(fields=[
                FBCampaign.Field.id,
                FBCampaign.Field.name,
                FBCampaign.Field.status,
                FBCampaign.Field.objective,
                FBCampaign.Field.daily_budget,
                FBCampaign.Field.lifetime_budget,
                FBCampaign.Field.created_time,
                FBCampaign.Field.updated_time,
            ])
            return self._map_campaign(fb_campaign)

        except FacebookRequestError as ex:
            if ex.api_error_code() == 100:  # Invalid ID
                return None
            raise MetaAdsError(f"Meta Ads Fehler: {ex.api_error_message()}") from ex

    async def create_campaign(self, customer_id: str, campaign: CampaignCreate) -> Campaign:
        """Neue Kampagne erstellen"""
        if not self._initialized:
            await self.authenticate()

        account_id = self._ensure_act_prefix(customer_id)

        try:
            account = AdAccount(account_id)

            # Kampagnen-Parameter
            params = {
                FBCampaign.Field.name: campaign.name,
                FBCampaign.Field.status: FBCampaign.Status.paused,  # Immer pausiert starten
                FBCampaign.Field.objective: self._map_campaign_type_to_meta(campaign.campaign_type),
                FBCampaign.Field.special_ad_categories: [],  # Keine speziellen Kategorien
            }

            # Budget (in Cents/Centimes)
            if campaign.budget_amount:
                params[FBCampaign.Field.daily_budget] = int(campaign.budget_amount * 100)

            fb_campaign = account.create_campaign(params=params)

            # Erstellte Kampagne zurückgeben
            created = await self.get_campaign(customer_id, fb_campaign.get_id())
            if not created:
                raise MetaAdsError("Kampagne wurde erstellt, konnte aber nicht abgerufen werden")
            return created

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Kampagne konnte nicht erstellt werden: {ex.api_error_message()}") from ex

    async def update_campaign(self, customer_id: str, campaign_id: str, campaign: CampaignUpdate) -> Campaign:
        """Kampagne aktualisieren"""
        if not self._initialized:
            await self.authenticate()

        try:
            fb_campaign = FBCampaign(campaign_id)
            params = {}

            if campaign.name:
                params[FBCampaign.Field.name] = campaign.name

            if campaign.status:
                params[FBCampaign.Field.status] = self._map_status_to_meta(campaign.status)

            if campaign.budget_amount is not None:
                params[FBCampaign.Field.daily_budget] = int(campaign.budget_amount * 100)

            if params:
                fb_campaign.api_update(params=params)

            updated = await self.get_campaign(customer_id, campaign_id)
            if not updated:
                raise MetaAdsError("Kampagne wurde aktualisiert, konnte aber nicht abgerufen werden")
            return updated

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Kampagne konnte nicht aktualisiert werden: {ex.api_error_message()}") from ex

    async def pause_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne pausieren"""
        if not self._initialized:
            await self.authenticate()

        try:
            fb_campaign = FBCampaign(campaign_id)
            fb_campaign.api_update(params={
                FBCampaign.Field.status: FBCampaign.Status.paused
            })
            return True

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Kampagne konnte nicht pausiert werden: {ex.api_error_message()}") from ex

    async def enable_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne aktivieren"""
        if not self._initialized:
            await self.authenticate()

        try:
            fb_campaign = FBCampaign(campaign_id)
            fb_campaign.api_update(params={
                FBCampaign.Field.status: FBCampaign.Status.active
            })
            return True

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Kampagne konnte nicht aktiviert werden: {ex.api_error_message()}") from ex

    async def delete_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne löschen (archivieren)"""
        if not self._initialized:
            await self.authenticate()

        try:
            fb_campaign = FBCampaign(campaign_id)
            # Meta löscht nicht wirklich, sondern archiviert
            fb_campaign.api_update(params={
                FBCampaign.Field.status: FBCampaign.Status.archived
            })
            return True

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Kampagne konnte nicht gelöscht werden: {ex.api_error_message()}") from ex

    # ============== AD SETS (Ad Groups) ==============

    async def get_ad_groups(self, customer_id: str, campaign_id: str) -> List[AdGroup]:
        """Alle Ad Sets (Anzeigengruppen) einer Kampagne"""
        if not self._initialized:
            await self.authenticate()

        ad_groups = []

        try:
            fb_campaign = FBCampaign(campaign_id)
            ad_sets = fb_campaign.get_ad_sets(fields=[
                AdSet.Field.id,
                AdSet.Field.name,
                AdSet.Field.status,
                AdSet.Field.daily_budget,
                AdSet.Field.lifetime_budget,
                AdSet.Field.bid_amount,
                AdSet.Field.billing_event,
                AdSet.Field.optimization_goal,
                AdSet.Field.targeting,
            ])

            for ad_set in ad_sets:
                ad_group = self._map_ad_set(ad_set, campaign_id)
                ad_groups.append(ad_group)

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Ad Sets konnten nicht abgerufen werden: {ex.api_error_message()}") from ex

        return ad_groups

    async def create_ad_group(self, customer_id: str, campaign_id: str, ad_group: dict) -> AdGroup:
        """Ad Set (Anzeigengruppe) erstellen"""
        if not self._initialized:
            await self.authenticate()

        account_id = self._ensure_act_prefix(customer_id)

        try:
            account = AdAccount(account_id)

            params = {
                AdSet.Field.name: ad_group.get("name", "Neue Anzeigengruppe"),
                AdSet.Field.campaign_id: campaign_id,
                AdSet.Field.status: AdSet.Status.paused,
                AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
                AdSet.Field.optimization_goal: AdSet.OptimizationGoal.reach,
            }

            # Budget
            if "daily_budget" in ad_group:
                params[AdSet.Field.daily_budget] = int(ad_group["daily_budget"] * 100)

            # Targeting (minimal erforderlich)
            if "targeting" in ad_group:
                params[AdSet.Field.targeting] = ad_group["targeting"]
            else:
                # Minimales Targeting für Österreich
                params[AdSet.Field.targeting] = {
                    "geo_locations": {"countries": ["AT"]},
                }

            fb_ad_set = account.create_ad_set(params=params)

            # Ad Set abrufen und zurückgeben
            fb_ad_set.api_get(fields=[
                AdSet.Field.id,
                AdSet.Field.name,
                AdSet.Field.status,
                AdSet.Field.campaign_id,
            ])

            return self._map_ad_set(fb_ad_set, campaign_id)

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Ad Set konnte nicht erstellt werden: {ex.api_error_message()}") from ex

    # ============== ADS ==============

    async def get_ads(self, customer_id: str, ad_group_id: str) -> List[Ad]:
        """Alle Ads eines Ad Sets"""
        if not self._initialized:
            await self.authenticate()

        ads = []

        try:
            ad_set = AdSet(ad_group_id)
            fb_ads = ad_set.get_ads(fields=[
                FBAd.Field.id,
                FBAd.Field.name,
                FBAd.Field.status,
                FBAd.Field.creative,
                FBAd.Field.created_time,
            ])

            for fb_ad in fb_ads:
                ad = self._map_ad(fb_ad, ad_group_id)
                ads.append(ad)

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Ads konnten nicht abgerufen werden: {ex.api_error_message()}") from ex

        return ads

    async def create_ad(self, customer_id: str, ad_group_id: str, ad: dict) -> Ad:
        """Ad erstellen"""
        if not self._initialized:
            await self.authenticate()

        account_id = self._ensure_act_prefix(customer_id)

        try:
            account = AdAccount(account_id)

            # Zuerst Creative erstellen (wenn nicht vorhanden)
            creative_id = ad.get("creative_id")

            if not creative_id and "creative" in ad:
                creative_params = ad["creative"]
                creative = account.create_ad_creative(params=creative_params)
                creative_id = creative.get_id()

            if not creative_id:
                raise MetaAdsError("Creative ID oder Creative-Parameter erforderlich")

            # Ad erstellen
            params = {
                FBAd.Field.name: ad.get("name", "Neue Anzeige"),
                FBAd.Field.adset_id: ad_group_id,
                FBAd.Field.creative: {"creative_id": creative_id},
                FBAd.Field.status: FBAd.Status.paused,
            }

            fb_ad = account.create_ad(params=params)
            fb_ad.api_get(fields=[
                FBAd.Field.id,
                FBAd.Field.name,
                FBAd.Field.status,
                FBAd.Field.adset_id,
            ])

            return self._map_ad(fb_ad, ad_group_id)

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Ad konnte nicht erstellt werden: {ex.api_error_message()}") from ex

    # ============== REPORTING ==============

    async def get_performance_report(
        self,
        customer_id: str,
        start_date: str,
        end_date: str,
        campaign_ids: Optional[List[str]] = None
    ) -> PerformanceReport:
        """Performance-Bericht abrufen"""
        if not self._initialized:
            await self.authenticate()

        account_id = self._ensure_act_prefix(customer_id)
        campaign_performances = []

        try:
            account = AdAccount(account_id)

            # Insights für den Account abrufen
            params = {
                "time_range": {
                    "since": start_date,
                    "until": end_date
                },
                "level": "campaign",
            }

            if campaign_ids:
                params["filtering"] = [{
                    "field": "campaign.id",
                    "operator": "IN",
                    "value": campaign_ids
                }]

            insights = account.get_insights(
                fields=[
                    AdsInsights.Field.campaign_id,
                    AdsInsights.Field.campaign_name,
                    AdsInsights.Field.impressions,
                    AdsInsights.Field.clicks,
                    AdsInsights.Field.spend,
                    AdsInsights.Field.cpc,
                    AdsInsights.Field.cpm,
                    AdsInsights.Field.ctr,
                    AdsInsights.Field.reach,
                    AdsInsights.Field.frequency,
                    AdsInsights.Field.actions,
                    AdsInsights.Field.cost_per_action_type,
                ],
                params=params
            )

            for insight in insights:
                perf = self._map_insight_to_performance(insight)
                campaign_performances.append(perf)

            # Gesamtmetriken berechnen
            total_metrics = self._calculate_total_metrics(campaign_performances)

            # Datestrings in date-Objekte konvertieren
            from datetime import datetime as dt
            start_dt = dt.strptime(start_date, "%Y-%m-%d").date()
            end_dt = dt.strptime(end_date, "%Y-%m-%d").date()

            return PerformanceReport(
                provider="meta",
                customer_id=customer_id,
                start_date=start_dt,
                end_date=end_dt,
                campaigns=campaign_performances,
                total_metrics=total_metrics
            )

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Report konnte nicht abgerufen werden: {ex.api_error_message()}") from ex

    # ============== MAPPING HELPERS ==============

    def _map_campaign(self, fb_campaign) -> Campaign:
        """Facebook Campaign zu unserem Campaign-Modell mappen"""
        # Budget (in Cents gespeichert, in Euro umrechnen)
        daily_budget = fb_campaign.get(FBCampaign.Field.daily_budget)
        lifetime_budget = fb_campaign.get(FBCampaign.Field.lifetime_budget)

        budget = 0.0
        if daily_budget:
            budget = float(daily_budget) / 100
        elif lifetime_budget:
            budget = float(lifetime_budget) / 100

        return Campaign(
            id=fb_campaign.get_id(),
            name=fb_campaign.get(FBCampaign.Field.name, ""),
            status=self._map_meta_status(fb_campaign.get(FBCampaign.Field.status)),
            campaign_type=self._map_meta_objective(fb_campaign.get(FBCampaign.Field.objective)),
            budget_amount=budget,
            provider="meta",
        )

    def _map_ad_set(self, ad_set, campaign_id: str) -> AdGroup:
        """Facebook AdSet zu unserem AdGroup-Modell mappen"""
        daily_budget = ad_set.get(AdSet.Field.daily_budget)
        budget_micros = int(float(daily_budget) * 10000) if daily_budget else 0  # Cents zu Mikro

        return AdGroup(
            id=ad_set.get_id(),
            campaign_id=campaign_id,
            name=ad_set.get(AdSet.Field.name, ""),
            status=self._map_meta_status_to_ad_group(ad_set.get(AdSet.Field.status)),
            cpc_bid_micros=budget_micros,
            provider="meta",
        )

    def _map_ad(self, fb_ad, ad_group_id: str) -> Ad:
        """Facebook Ad zu unserem Ad-Modell mappen"""
        return Ad(
            id=fb_ad.get_id(),
            ad_group_id=ad_group_id,
            name=fb_ad.get(FBAd.Field.name, ""),
            status=self._map_meta_status_to_ad(fb_ad.get(FBAd.Field.status)),
            ad_type=AdType.RESPONSIVE_DISPLAY,  # Meta verwendet hauptsächlich Display
            provider="meta",
        )

    def _map_meta_status(self, status: str) -> CampaignStatus:
        """Meta Status zu unserem Status mappen"""
        status_map = {
            "ACTIVE": CampaignStatus.ENABLED,
            "PAUSED": CampaignStatus.PAUSED,
            "ARCHIVED": CampaignStatus.REMOVED,
            "DELETED": CampaignStatus.REMOVED,
        }
        return status_map.get(status, CampaignStatus.PAUSED)

    def _map_meta_status_to_ad_group(self, status: str) -> AdGroupStatus:
        """Meta Status zu AdGroup Status mappen"""
        status_map = {
            "ACTIVE": AdGroupStatus.ENABLED,
            "PAUSED": AdGroupStatus.PAUSED,
            "ARCHIVED": AdGroupStatus.REMOVED,
            "DELETED": AdGroupStatus.REMOVED,
        }
        return status_map.get(status, AdGroupStatus.PAUSED)

    def _map_meta_status_to_ad(self, status: str) -> AdStatus:
        """Meta Status zu Ad Status mappen"""
        status_map = {
            "ACTIVE": AdStatus.ENABLED,
            "PAUSED": AdStatus.PAUSED,
            "ARCHIVED": AdStatus.REMOVED,
            "DELETED": AdStatus.REMOVED,
        }
        return status_map.get(status, AdStatus.PAUSED)

    def _map_meta_objective(self, objective: str) -> CampaignType:
        """Meta Objective zu unserem CampaignType mappen"""
        objective_map = {
            "OUTCOME_AWARENESS": CampaignType.DISPLAY,
            "OUTCOME_ENGAGEMENT": CampaignType.DISPLAY,
            "OUTCOME_LEADS": CampaignType.SEARCH,  # Vereinfacht
            "OUTCOME_SALES": CampaignType.SHOPPING,
            "OUTCOME_TRAFFIC": CampaignType.DISPLAY,
            "OUTCOME_APP_PROMOTION": CampaignType.DISPLAY,
            # Legacy Objectives
            "BRAND_AWARENESS": CampaignType.DISPLAY,
            "REACH": CampaignType.DISPLAY,
            "TRAFFIC": CampaignType.DISPLAY,
            "ENGAGEMENT": CampaignType.DISPLAY,
            "LEAD_GENERATION": CampaignType.SEARCH,
            "CONVERSIONS": CampaignType.SEARCH,
            "CATALOG_SALES": CampaignType.SHOPPING,
            "STORE_TRAFFIC": CampaignType.DISPLAY,
        }
        return objective_map.get(objective, CampaignType.DISPLAY)

    def _map_campaign_type_to_meta(self, campaign_type: CampaignType) -> str:
        """Unseren CampaignType zu Meta Objective mappen"""
        type_map = {
            CampaignType.SEARCH: "OUTCOME_LEADS",
            CampaignType.DISPLAY: "OUTCOME_AWARENESS",
            CampaignType.SHOPPING: "OUTCOME_SALES",
            CampaignType.VIDEO: "OUTCOME_ENGAGEMENT",
            CampaignType.PERFORMANCE_MAX: "OUTCOME_SALES",
            CampaignType.UNKNOWN: "OUTCOME_AWARENESS",
        }
        return type_map.get(campaign_type, "OUTCOME_AWARENESS")

    def _map_status_to_meta(self, status: CampaignStatus) -> str:
        """Unseren Status zu Meta Status mappen"""
        status_map = {
            CampaignStatus.ENABLED: "ACTIVE",
            CampaignStatus.PAUSED: "PAUSED",
            CampaignStatus.REMOVED: "ARCHIVED",
        }
        return status_map.get(status, "PAUSED")

    def _map_insight_to_performance(self, insight) -> CampaignPerformance:
        """Meta Insight zu CampaignPerformance mappen"""
        # Conversions aus actions extrahieren
        conversions = 0.0
        conversion_value = 0.0
        actions = insight.get(AdsInsights.Field.actions, [])
        for action in actions:
            if action.get("action_type") in ["lead", "purchase", "complete_registration"]:
                conversions += float(action.get("value", 0))

        impressions = int(insight.get(AdsInsights.Field.impressions, 0))
        clicks = int(insight.get(AdsInsights.Field.clicks, 0))
        # Meta spend ist in der Account-Währung (z.B. Euro), wir brauchen Mikro-Einheiten
        spend = float(insight.get(AdsInsights.Field.spend, 0))
        cost_micros = int(spend * 1_000_000)

        return CampaignPerformance(
            campaign_id=insight.get(AdsInsights.Field.campaign_id),
            campaign_name=insight.get(AdsInsights.Field.campaign_name, ""),
            metrics=PerformanceMetrics(
                impressions=impressions,
                clicks=clicks,
                cost_micros=cost_micros,
                conversions=conversions,
                conversion_value=conversion_value,
            )
        )

    def _calculate_total_metrics(self, performances: List[CampaignPerformance]) -> PerformanceMetrics:
        """Gesamtmetriken aus allen Kampagnen berechnen"""
        total_impressions = sum(p.metrics.impressions for p in performances)
        total_clicks = sum(p.metrics.clicks for p in performances)
        total_cost_micros = sum(p.metrics.cost_micros for p in performances)
        total_conversions = sum(p.metrics.conversions for p in performances)
        total_conversion_value = sum(p.metrics.conversion_value for p in performances)

        return PerformanceMetrics(
            impressions=total_impressions,
            clicks=total_clicks,
            cost_micros=total_cost_micros,
            conversions=total_conversions,
            conversion_value=total_conversion_value,
        )


# ============== MULTI-ACCOUNT HELPER ==============

class MetaAdsMultiAccountManager:
    """
    Manager für mehrere Meta Ads Accounts

    Ermöglicht die Verwaltung mehrerer Werbekonten mit verschiedenen
    Access Tokens (z.B. für verschiedene Business Manager).

    Beispiel:
        manager = MetaAdsMultiAccountManager()
        manager.add_account("kunde1", app_id="...", token="token1")
        manager.add_account("kunde2", app_id="...", token="token2")

        # Kampagnen von Kunde 1 abrufen
        provider = manager.get_provider("kunde1")
        campaigns = await provider.get_campaigns("act_123456")
    """

    def __init__(self):
        self._providers: dict[str, MetaAdsProvider] = {}

    def add_account(
        self,
        account_name: str,
        app_id: str,
        app_secret: str,
        access_token: str
    ) -> None:
        """Neuen Account hinzufügen"""
        self._providers[account_name] = MetaAdsProvider(
            app_id=app_id,
            app_secret=app_secret,
            access_token=access_token
        )

    def get_provider(self, account_name: str) -> MetaAdsProvider:
        """Provider für einen Account abrufen"""
        if account_name not in self._providers:
            raise ValueError(f"Account '{account_name}' nicht gefunden")
        return self._providers[account_name]

    def list_accounts(self) -> List[str]:
        """Liste aller konfigurierten Accounts"""
        return list(self._providers.keys())

    def remove_account(self, account_name: str) -> bool:
        """Account entfernen"""
        if account_name in self._providers:
            del self._providers[account_name]
            return True
        return False
