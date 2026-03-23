"""LinkedIn Ads API provider implementation."""
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pylint: disable=broad-exception-caught,broad-exception-raised,too-many-locals
from datetime import datetime
from typing import Any, List, Optional

from models.ad import Ad, AdStatus, AdType
from models.ad_group import AdGroup
from models.campaign import Campaign, CampaignCreate, CampaignUpdate, CampaignStatus, CampaignType
from models.report import CampaignPerformance, PerformanceMetrics, PerformanceReport

from .base import AdsProvider


class LinkedInAdsError(Exception):
    """Custom exception for LinkedIn Ads API errors."""


# httpx für REST API calls
try:
    import httpx
    LINKEDIN_ADS_AVAILABLE = True
except ImportError:
    LINKEDIN_ADS_AVAILABLE = False
    httpx: Any = None


class LinkedInAdsProvider(AdsProvider):
    """
    LinkedIn Marketing API Provider

    LinkedIn nutzt REST API ohne offizielles Python SDK.
    Wir verwenden httpx für asynchrone HTTP-Anfragen.

    Dokumentation: https://learn.microsoft.com/en-us/linkedin/marketing/

    Authentifizierung:
        - OAuth 2.0 Access Token
        - Scopes: r_ads, r_ads_reporting, rw_ads (für Schreibzugriff)

    customer_id Format: Sponsored Account ID (z.B. 508123456)
    """

    provider_name = "linkedin"
    BASE_URL = "https://api.linkedin.com/rest"  # REST API mit Versionierung
    API_VERSION = "202503"  # LinkedIn API Version (YYYYMM Format)

    def __init__(
        self,
        access_token: Optional[str] = None,
        ad_account_id: Optional[str] = None
    ):
        """
        LinkedIn Ads Provider initialisieren

        Args:
            access_token: OAuth 2.0 Access Token
            ad_account_id: Standard Ad Account ID (optional)
        """
        self.access_token = access_token
        self.ad_account_id = ad_account_id
        self._initialized = False
        self._client: "Optional[httpx.AsyncClient]" = None  # type: ignore[valid-type]

    def _get_headers(self) -> dict:
        """Standard Header für LinkedIn REST API Anfragen"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": self.API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def _ensure_client(self):
        """HTTP Client initialisieren wenn nötig"""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self._get_headers(),
                timeout=30.0
            )

    async def authenticate(self) -> bool:
        """LinkedIn API Verbindung initialisieren"""
        if not LINKEDIN_ADS_AVAILABLE:
            raise ImportError(
                "httpx Paket nicht installiert. "
                "Führe aus: pip install httpx"
            )

        if not self.access_token:
            raise LinkedInAdsError(
                "LinkedIn Access Token fehlt. "
                "Setze LINKEDIN_ACCESS_TOKEN in der .env Datei."
            )

        try:
            await self._ensure_client()
            self._initialized = True
            return True
        except Exception as e:
            raise LinkedInAdsError(f"LinkedIn Ads Authentifizierung fehlgeschlagen: {e}") from e

    async def test_connection(self) -> bool:
        """Verbindung testen durch Abruf der Ad Accounts"""
        if not self._initialized:
            await self.authenticate()

        try:
            # Ad Accounts abrufen um Verbindung zu testen
            response = await self._client.get(
                "/adAccounts",
                params={"q": "search"},
                headers=self._get_headers()
            )
            if response.status_code == 200:
                return True
            return False
        except Exception:
            return False

    async def get_user_info(self) -> dict:
        """LinkedIn Ad Account Info abrufen"""
        if not self._initialized:
            await self.authenticate()

        # Nutze Ad Accounts statt userinfo (braucht andere Scopes)
        accounts = await self.get_ad_accounts()
        if accounts:
            return {"ad_accounts": accounts}
        return {}

    async def get_ad_accounts(self) -> List[dict]:
        """Alle Ad Accounts des Users abrufen"""
        if not self._initialized:
            await self.authenticate()

        response = await self._client.get(
            "/adAccounts",
            params={"q": "search"},
            headers=self._get_headers()
        )

        if response.status_code != 200:
            raise LinkedInAdsError(f"Fehler beim Abrufen der Ad Accounts: {response.text}")

        data = response.json()
        return data.get("elements", [])

    # ============== CAMPAIGNS ==============

    async def get_campaigns(self, customer_id: str) -> List[Campaign]:
        """Alle Kampagnen eines Ad Accounts abrufen"""
        if not self._initialized:
            await self.authenticate()

        campaigns = []

        try:
            # REST API Endpunkt für Kampagnen (Account-ID im Pfad)
            response = await self._client.get(
                f"/adAccounts/{customer_id}/adCampaigns",
                headers=self._get_headers()
            )

            # 404 = keine Kampagnen vorhanden
            if response.status_code == 404:
                return []

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise LinkedInAdsError(
                    f"Fehler beim Abrufen der Kampagnen: {error_data.get('message', response.text)}"
                )

            data = response.json()

            for li_campaign in data.get("elements", []):
                campaign = self._map_campaign(li_campaign)
                campaigns.append(campaign)

        except LinkedInAdsError:
            raise
        except Exception as e:
            raise LinkedInAdsError(f"LinkedIn API Fehler: {str(e)}") from e

        return campaigns

    async def get_campaign(self, customer_id: str, campaign_id: str) -> Optional[Campaign]:
        """Einzelne Kampagne abrufen"""
        if not self._initialized:
            await self.authenticate()

        try:
            response = await self._client.get(
                f"/adAccounts/{customer_id}/adCampaigns/{campaign_id}",
                headers=self._get_headers()
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                raise LinkedInAdsError(f"Fehler beim Abrufen der Kampagne: {response.text}")

            data = response.json()
            return self._map_campaign(data)

        except LinkedInAdsError:
            raise
        except Exception as e:
            raise LinkedInAdsError(f"LinkedIn API Fehler: {str(e)}") from e

    async def create_campaign(self, customer_id: str, campaign: CampaignCreate) -> Campaign:
        """Neue Kampagne erstellen"""
        if not self._initialized:
            await self.authenticate()

        try:
            campaign_data = {
                "account": f"urn:li:sponsoredAccount:{customer_id}",
                "name": campaign.name,
                "status": "PAUSED",  # Startet immer pausiert
                "type": self._map_campaign_type_to_linkedin(campaign.campaign_type),
                "costType": "CPM",
                "dailyBudget": {
                    "currencyCode": "EUR",
                    "amount": str(int(campaign.budget_amount * 100))  # In Cents
                },
                "runSchedule": {
                    "start": int(datetime.now().timestamp() * 1000)
                }
            }

            response = await self._client.post(
                f"/adAccounts/{customer_id}/adCampaigns",
                json=campaign_data,
                headers=self._get_headers()
            )

            if response.status_code not in (200, 201):
                raise LinkedInAdsError(f"Fehler beim Erstellen der Kampagne: {response.text}")

            # Kampagne ID aus Header extrahieren
            campaign_id = response.headers.get("x-restli-id", "")

            # Neue Kampagne abrufen
            result = await self.get_campaign(customer_id, campaign_id)
            if result is None:
                raise LinkedInAdsError(f"Kampagne {campaign_id} konnte nicht abgerufen werden")
            return result

        except LinkedInAdsError:
            raise
        except Exception as e:
            raise LinkedInAdsError(f"LinkedIn API Fehler: {str(e)}") from e

    async def update_campaign(
        self, customer_id: str, campaign_id: str, campaign: CampaignUpdate
    ) -> Campaign:
        """Kampagne aktualisieren"""
        if not self._initialized:
            await self.authenticate()

        try:
            update_data = {}

            if campaign.name:
                update_data["name"] = campaign.name
            if campaign.budget_amount:
                update_data["dailyBudget"] = {
                    "currencyCode": "EUR",
                    "amount": str(int(campaign.budget_amount * 100))
                }

            if update_data:
                response = await self._client.post(
                    f"/adAccounts/{customer_id}/adCampaigns/{campaign_id}",
                    json=update_data,
                    headers={
                        **self._get_headers(),
                        "X-RestLi-Method": "PARTIAL_UPDATE"
                    }
                )

                if response.status_code not in (200, 204):
                    raise LinkedInAdsError(f"Fehler beim Aktualisieren: {response.text}")

            result = await self.get_campaign(customer_id, campaign_id)
            if result is None:
                raise LinkedInAdsError(f"Kampagne {campaign_id} konnte nicht abgerufen werden")
            return result

        except LinkedInAdsError:
            raise
        except Exception as e:
            raise LinkedInAdsError(f"LinkedIn API Fehler: {str(e)}") from e

    async def pause_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne pausieren"""
        if not self._initialized:
            await self.authenticate()

        try:
            response = await self._client.post(
                f"/adAccounts/{customer_id}/adCampaigns/{campaign_id}",
                json={"status": "PAUSED"},
                headers={
                    **self._get_headers(),
                    "X-RestLi-Method": "PARTIAL_UPDATE"
                }
            )

            return response.status_code in (200, 204)

        except Exception:
            return False

    async def enable_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne aktivieren"""
        if not self._initialized:
            await self.authenticate()

        try:
            response = await self._client.post(
                f"/adAccounts/{customer_id}/adCampaigns/{campaign_id}",
                json={"status": "ACTIVE"},
                headers={
                    **self._get_headers(),
                    "X-RestLi-Method": "PARTIAL_UPDATE"
                }
            )

            return response.status_code in (200, 204)

        except Exception:
            return False

    async def delete_campaign(self, customer_id: str, campaign_id: str) -> bool:
        """Kampagne archivieren (LinkedIn löscht nicht wirklich)"""
        if not self._initialized:
            await self.authenticate()

        try:
            response = await self._client.post(
                f"/adAccounts/{customer_id}/adCampaigns/{campaign_id}",
                json={"status": "ARCHIVED"},
                headers={
                    **self._get_headers(),
                    "X-RestLi-Method": "PARTIAL_UPDATE"
                }
            )

            return response.status_code in (200, 204)

        except Exception:
            return False

    # ============== AD GROUPS (Campaign Groups bei LinkedIn) ==============

    async def get_ad_groups(self, customer_id: str, campaign_id: str) -> List[AdGroup]:
        """Ad Groups abrufen (bei LinkedIn sind das die Creatives einer Campaign)"""
        if not self._initialized:
            await self.authenticate()

        # LinkedIn hat keine Ad Groups wie Google/Meta
        # Creatives sind direkt der Campaign zugeordnet
        return []

    async def create_ad_group(self, customer_id: str, campaign_id: str, ad_group: dict) -> AdGroup:
        """AdGroup erstellen - nicht direkt unterstützt bei LinkedIn"""
        raise LinkedInAdsError(
            "LinkedIn verwendet keine Ad Groups. "
            "Creatives werden direkt der Campaign zugeordnet."
        )

    # ============== ADS (Creatives bei LinkedIn) ==============

    async def get_ads(self, customer_id: str, ad_group_id: str) -> List[Ad]:
        """Creatives einer Campaign abrufen"""
        if not self._initialized:
            await self.authenticate()

        ads = []

        try:
            # ad_group_id ist hier die campaign_id
            response = await self._client.get(
                "/adCreatives",
                params={
                    "q": "search",
                    "search": f"(campaign:(values:List(urn:li:sponsoredCampaign:{ad_group_id})))"
                },
                headers=self._get_headers()
            )

            if response.status_code != 200:
                return []

            data = response.json()

            for creative in data.get("elements", []):
                ad = self._map_ad(creative, ad_group_id)
                ads.append(ad)

        except Exception:
            pass

        return ads

    async def create_ad(self, customer_id: str, ad_group_id: str, ad: dict) -> Ad:
        """Creative erstellen"""
        if not self._initialized:
            await self.authenticate()

        # Hier würde die Creative-Erstellung implementiert
        raise LinkedInAdsError("Creative-Erstellung noch nicht implementiert")

    # ============== REPORTING ==============

    async def get_performance_report(
        self,
        customer_id: str,
        start_date: str,
        end_date: str,
        campaign_ids: Optional[List[str]] = None
    ) -> PerformanceReport:
        """Performance Report abrufen"""
        if not self._initialized:
            await self.authenticate()

        campaigns_performance = []

        try:
            # LinkedIn Analytics API
            response = await self._client.get(
                "/adAnalytics",
                params={
                    "q": "analytics",
                    "pivot": "CAMPAIGN",
                    "dateRange": (
                        f"(start:(year:{start_date[:4]},month:{start_date[5:7]},"
                        f"day:{start_date[8:10]}),end:(year:{end_date[:4]},"
                        f"month:{end_date[5:7]},day:{end_date[8:10]}))"
                    ),
                    "accounts": f"urn:li:sponsoredAccount:{customer_id}",
                    "fields": "impressions,clicks,costInLocalCurrency,conversions"
                },
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()

                for element in data.get("elements", []):
                    # Campaign URN parsen
                    campaign_urn = element.get("pivotValue", "")
                    campaign_id = campaign_urn.split(":")[-1] if campaign_urn else "unknown"

                    # Filter by campaign_ids if provided
                    if campaign_ids and campaign_id not in campaign_ids:
                        continue

                    impressions = element.get("impressions", 0)
                    clicks = element.get("clicks", 0)
                    # LinkedIn gibt Kosten in Cents zurück, wir brauchen Micros
                    cost_cents = float(element.get("costInLocalCurrency", 0))
                    cost_micros = int(cost_cents * 10000)  # Cents zu Micros
                    conversions = float(element.get("conversions", 0))

                    campaigns_performance.append(CampaignPerformance(
                        campaign_id=campaign_id,
                        campaign_name=f"Campaign {campaign_id}",
                        metrics=PerformanceMetrics(
                            impressions=impressions,
                            clicks=clicks,
                            cost_micros=cost_micros,
                            conversions=conversions
                        )
                    ))

        except Exception as e:
            raise LinkedInAdsError(f"Fehler beim Abrufen des Reports: {str(e)}") from e

        # Gesamtmetriken berechnen
        total_impressions = sum(c.metrics.impressions for c in campaigns_performance)
        total_clicks = sum(c.metrics.clicks for c in campaigns_performance)
        total_cost_micros = sum(c.metrics.cost_micros for c in campaigns_performance)
        total_conversions = sum(c.metrics.conversions for c in campaigns_performance)

        from datetime import date as date_type
        return PerformanceReport(
            provider="linkedin",
            customer_id=customer_id,
            start_date=date_type.fromisoformat(start_date),
            end_date=date_type.fromisoformat(end_date),
            total_metrics=PerformanceMetrics(
                impressions=total_impressions,
                clicks=total_clicks,
                cost_micros=total_cost_micros,
                conversions=total_conversions
            ),
            campaigns=campaigns_performance
        )

    async def get_recommendations(self, customer_id: str):
        """Empfehlungen abrufen - LinkedIn bietet keine direkte API hierfür"""
        from models.recommendation import RecommendationsResponse
        return RecommendationsResponse(
            customer_id=customer_id,
            recommendations=[],
            total_count=0
        )

    # ============== MAPPING HELPERS ==============

    def _map_campaign(self, li_campaign: dict) -> Campaign:
        """LinkedIn Campaign zu internem Campaign-Modell mappen"""
        # Status mappen
        status_map = {
            "ACTIVE": CampaignStatus.ENABLED,
            "PAUSED": CampaignStatus.PAUSED,
            "ARCHIVED": CampaignStatus.REMOVED,
            "CANCELED": CampaignStatus.REMOVED,
            "DRAFT": CampaignStatus.PAUSED,
            "PENDING_DELETION": CampaignStatus.REMOVED,
        }

        # Kampagnentyp mappen
        type_map = {
            "TEXT_AD": CampaignType.DISPLAY,
            "SPONSORED_UPDATES": CampaignType.DISPLAY,
            "SPONSORED_INMAILS": CampaignType.DISPLAY,
            "DYNAMIC": CampaignType.DISPLAY,
        }

        # Budget extrahieren
        daily_budget = li_campaign.get("dailyBudget", {})
        budget_amount = float(daily_budget.get("amount", "0")) / 100 if daily_budget else 0

        # ID extrahieren (kann URN oder direkte ID sein)
        campaign_id = str(li_campaign.get("id", ""))
        if "urn:li:" in campaign_id:
            campaign_id = campaign_id.rsplit(":", maxsplit=1)[-1]

        return Campaign(
            id=campaign_id,
            name=li_campaign.get("name", "Unbekannte Kampagne"),
            status=status_map.get(li_campaign.get("status", ""), CampaignStatus.UNKNOWN),
            campaign_type=type_map.get(li_campaign.get("type", ""), CampaignType.UNKNOWN),
            budget_amount=budget_amount,
            provider="linkedin"
        )

    def _map_campaign_type_to_linkedin(self, campaign_type: CampaignType) -> str:
        """Internes CampaignType zu LinkedIn Type mappen"""
        type_map = {
            CampaignType.SEARCH: "TEXT_AD",
            CampaignType.DISPLAY: "SPONSORED_UPDATES",
            CampaignType.VIDEO: "SPONSORED_UPDATES",
            CampaignType.SHOPPING: "SPONSORED_UPDATES",
        }
        return type_map.get(campaign_type, "SPONSORED_UPDATES")

    def _map_ad(self, creative: dict, campaign_id: str = "unknown") -> Ad:
        """LinkedIn Creative zu internem Ad-Modell mappen"""
        creative_id = str(creative.get("id", ""))
        if "urn:li:" in creative_id:
            creative_id = creative_id.rsplit(":", maxsplit=1)[-1]

        status_map = {
            "ACTIVE": AdStatus.ENABLED,
            "PAUSED": AdStatus.PAUSED,
            "ARCHIVED": AdStatus.REMOVED,
        }

        return Ad(
            id=creative_id,
            ad_group_id=campaign_id,  # Bei LinkedIn gibt es keine AdGroups, Campaign dient als Container
            name=creative.get("reference", "Creative"),
            status=status_map.get(creative.get("status", ""), AdStatus.UNKNOWN),
            ad_type=AdType.IMAGE,  # LinkedIn Creatives sind meist Bild-basiert
            provider="linkedin"
        )

    async def close(self):
        """HTTP Client schließen"""
        if self._client:
            await self._client.aclose()
            self._client = None
