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
    from facebook_business.adobjects.adcreative import AdCreative
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
    AdCreative: Any = None
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
        """Alle Ads eines Ad Sets mit Creative-Details"""
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
                FBAd.Field.effective_status,
            ])

            for fb_ad in fb_ads:
                ad = self._map_ad_with_creative(fb_ad, ad_group_id)
                ads.append(ad)

        except FacebookRequestError as ex:
            raise MetaAdsError(f"Ads konnten nicht abgerufen werden: {ex.api_error_message()}") from ex

        return ads

    def _get_creative_details(self, creative_id: str) -> dict:
        """Creative-Details abrufen (Bilder, Videos, Texte)"""
        try:
            creative = AdCreative(creative_id)
            creative.api_get(fields=[
                AdCreative.Field.id,
                AdCreative.Field.name,
                AdCreative.Field.title,
                AdCreative.Field.body,
                AdCreative.Field.call_to_action_type,
                AdCreative.Field.image_url,
                AdCreative.Field.thumbnail_url,
                AdCreative.Field.video_id,
                AdCreative.Field.object_story_spec,
                AdCreative.Field.asset_feed_spec,
                AdCreative.Field.effective_object_story_id,
            ])

            details = {
                "id": creative.get("id"),
                "name": creative.get("name"),
                "title": creative.get("title"),
                "body": creative.get("body"),
                "cta": creative.get("call_to_action_type"),
                "image_url": creative.get("image_url"),
                "thumbnail_url": creative.get("thumbnail_url"),
                "video_id": creative.get("video_id"),
            }

            # Object Story Spec enthält oft mehr Details
            story_spec = creative.get("object_story_spec", {})
            if story_spec:
                # Link Ad
                link_data = story_spec.get("link_data", {})
                if link_data:
                    details["link"] = link_data.get("link")
                    details["message"] = link_data.get("message")
                    details["caption"] = link_data.get("caption")
                    details["description"] = link_data.get("description")
                    if not details["image_url"]:
                        details["image_url"] = link_data.get("image_hash") or link_data.get("picture")

                # Video Ad
                video_data = story_spec.get("video_data", {})
                if video_data:
                    details["video_id"] = video_data.get("video_id")
                    details["message"] = video_data.get("message")
                    details["title"] = video_data.get("title")
                    if not details["thumbnail_url"]:
                        details["thumbnail_url"] = video_data.get("image_url")

            # Asset Feed Spec für Dynamic Creatives
            asset_feed = creative.get("asset_feed_spec", {})
            if asset_feed:
                # Mehrere Headlines/Beschreibungen
                titles = asset_feed.get("titles", [])
                if titles:
                    details["headlines"] = [t.get("text") for t in titles if t.get("text")]

                bodies = asset_feed.get("bodies", [])
                if bodies:
                    details["descriptions"] = [b.get("text") for b in bodies if b.get("text")]

                # Bilder
                images = asset_feed.get("images", [])
                if images:
                    details["image_urls"] = [img.get("url") for img in images if img.get("url")]

                # Videos
                videos = asset_feed.get("videos", [])
                if videos:
                    details["video_ids"] = [v.get("video_id") for v in videos if v.get("video_id")]

            return details

        except Exception:
            return {}

    def _map_ad_with_creative(self, fb_ad, ad_group_id: str) -> Ad:
        """Facebook Ad mit Creative-Details mappen"""
        # Creative kann verschiedene Formate haben
        creative_data = fb_ad.get("creative")
        creative_id = None

        if creative_data:
            if isinstance(creative_data, dict):
                creative_id = creative_data.get("id")
            elif isinstance(creative_data, str):
                creative_id = creative_data
            elif hasattr(creative_data, "get_id"):
                creative_id = creative_data.get_id()
            elif hasattr(creative_data, "__getitem__"):
                try:
                    creative_id = creative_data["id"]
                except (KeyError, TypeError):
                    pass

        # Fallback: Creative-ID direkt von der Ad abrufen
        if not creative_id:
            try:
                ad_obj = FBAd(fb_ad.get_id())
                ad_obj.api_get(fields=["creative"])
                creative_ref = ad_obj.get("creative")
                if creative_ref:
                    if isinstance(creative_ref, dict):
                        creative_id = creative_ref.get("id")
                    elif hasattr(creative_ref, "get_id"):
                        creative_id = creative_ref.get_id()
            except Exception:
                pass

        # Creative-Details abrufen wenn vorhanden
        creative_details = {}
        if creative_id:
            creative_details = self._get_creative_details(creative_id)

        # Ad-Typ bestimmen
        ad_type = AdType.RESPONSIVE_DISPLAY
        if creative_details.get("video_id") or creative_details.get("video_ids"):
            ad_type = AdType.VIDEO
        elif creative_details.get("headlines") and len(creative_details.get("headlines", [])) > 1:
            ad_type = AdType.CAROUSEL

        # URLs sammeln
        final_urls = []
        if creative_details.get("link"):
            final_urls.append(creative_details["link"])

        # Bild-URLs
        image_urls = creative_details.get("image_urls", [])
        if creative_details.get("image_url") and creative_details["image_url"] not in image_urls:
            image_urls.insert(0, creative_details["image_url"])
        if creative_details.get("thumbnail_url") and creative_details["thumbnail_url"] not in image_urls:
            image_urls.append(creative_details["thumbnail_url"])

        # Headlines und Beschreibungen
        headlines = creative_details.get("headlines", [])
        if creative_details.get("title") and creative_details["title"] not in headlines:
            headlines.insert(0, creative_details["title"])

        descriptions = creative_details.get("descriptions", [])
        if creative_details.get("body") and creative_details["body"] not in descriptions:
            descriptions.insert(0, creative_details["body"])
        if creative_details.get("message") and creative_details["message"] not in descriptions:
            descriptions.insert(0, creative_details["message"])

        return Ad(
            id=fb_ad.get_id(),
            ad_group_id=ad_group_id,
            name=fb_ad.get(FBAd.Field.name, ""),
            status=self._map_meta_status_to_ad(fb_ad.get(FBAd.Field.status)),
            ad_type=ad_type,
            headlines=headlines if headlines else None,
            descriptions=descriptions if descriptions else None,
            final_urls=final_urls if final_urls else None,
            image_urls=image_urls if image_urls else None,
            video_id=creative_details.get("video_id"),
            provider="meta",
            raw_data={
                "creative_id": creative_id,
                "cta": creative_details.get("cta"),
                "effective_status": fb_ad.get("effective_status"),
            }
        )

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
