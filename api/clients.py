"""API endpoints for multi-client management."""
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query

from api.security import verify_api_key
from services.client_manager import client_manager, Client
from services.ads_manager import AdsManager, get_ads_manager

router = APIRouter(prefix="/clients", tags=["Clients"], dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=Dict[str, Any])
async def list_clients():
    """
    Liste aller konfigurierten Clients/Unternehmen

    Gibt alle Clients mit ihren Plattform-Konfigurationen zurück.
    """
    return {
        "clients": client_manager.to_dict(),
        "count": len(client_manager.list_clients())
    }


@router.get("/{client_id}")
async def get_client(client_id: str):
    """
    Einzelnen Client abrufen

    - **client_id**: z.B. afm_screenshot, rechnungseintreibung, spr_kanzlei, 911_abfluss
    """
    client = client_manager.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' nicht gefunden")

    return {
        "id": client.id,
        "name": client.name,
        "short": client.short,
        "icon": client.icon,
        "color": client.color,
        "description": client.description,
        "platforms": {
            platform: {
                "customer_id": config.customer_id,
                "ad_account_id": config.ad_account_id,
                "campaign_prefix": config.campaign_prefix
            } if config else None
            for platform, config in client.platforms.items()
        }
    }


@router.get("/{client_id}/campaigns")
async def get_client_campaigns(
    client_id: str,
    platform: Optional[str] = Query(None, description="Filter by platform: google, meta, linkedin"),
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Alle Kampagnen eines Clients abrufen

    Filtert Kampagnen automatisch nach dem Client-Präfix (z.B. [AFM], [SPR]).
    Optional nach Plattform filtern.
    """
    client = client_manager.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' nicht gefunden")

    result = {
        "client_id": client_id,
        "client_name": client.name,
        "campaigns": {}
    }

    platforms_to_check = [platform] if platform else ["google", "meta", "linkedin"]

    for plat in platforms_to_check:
        platform_config = client.get_platform(plat)
        if not platform_config:
            continue

        try:
            # Get account ID
            account_id = client_manager.get_account_id(client_id, plat)
            if not account_id:
                continue

            # Fetch campaigns from the platform
            all_campaigns = await ads_manager.get_campaigns(plat, account_id)

            # Filter by client prefix
            prefix = platform_config.campaign_prefix
            client_campaigns = [
                c for c in all_campaigns
                if c.name.startswith(prefix)
            ] if prefix else all_campaigns

            result["campaigns"][plat] = {
                "account_id": account_id,
                "prefix": prefix,
                "count": len(client_campaigns),
                "campaigns": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "status": c.status,
                        "budget": c.budget,
                        "currency": c.currency
                    }
                    for c in client_campaigns
                ]
            }
        except Exception as e:
            result["campaigns"][plat] = {
                "error": str(e)
            }

    return result


@router.get("/{client_id}/stats")
async def get_client_stats(
    client_id: str,
    date_range: str = Query("LAST_7_DAYS", description="Date range: LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH"),
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Aggregierte Statistiken eines Clients über alle Plattformen
    """
    client = client_manager.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' nicht gefunden")

    stats = {
        "client_id": client_id,
        "client_name": client.name,
        "date_range": date_range,
        "platforms": {},
        "totals": {
            "impressions": 0,
            "clicks": 0,
            "cost": 0.0,
            "conversions": 0,
            "campaigns_active": 0,
            "campaigns_paused": 0
        }
    }

    for plat in ["google", "meta", "linkedin"]:
        platform_config = client.get_platform(plat)
        if not platform_config:
            continue

        try:
            account_id = client_manager.get_account_id(client_id, plat)
            if not account_id:
                continue

            # Get campaigns
            all_campaigns = await ads_manager.get_campaigns(plat, account_id)
            prefix = platform_config.campaign_prefix
            client_campaigns = [
                c for c in all_campaigns
                if c.name.startswith(prefix)
            ] if prefix else all_campaigns

            # Count active/paused
            active = sum(1 for c in client_campaigns if c.status == "ENABLED")
            paused = sum(1 for c in client_campaigns if c.status == "PAUSED")

            # Get performance report
            try:
                report = await ads_manager.get_performance_report(
                    plat, account_id, date_range
                )

                # Filter report data by client campaigns
                client_campaign_ids = {c.id for c in client_campaigns}

                platform_stats = {
                    "impressions": 0,
                    "clicks": 0,
                    "cost": 0.0,
                    "conversions": 0
                }

                if hasattr(report, 'campaign_metrics'):
                    for metric in report.campaign_metrics:
                        if metric.campaign_id in client_campaign_ids:
                            platform_stats["impressions"] += metric.impressions or 0
                            platform_stats["clicks"] += metric.clicks or 0
                            platform_stats["cost"] += metric.cost or 0.0
                            platform_stats["conversions"] += metric.conversions or 0

            except Exception:
                platform_stats = {"impressions": 0, "clicks": 0, "cost": 0.0, "conversions": 0}

            stats["platforms"][plat] = {
                "account_id": account_id,
                "campaigns_active": active,
                "campaigns_paused": paused,
                **platform_stats
            }

            # Add to totals
            stats["totals"]["campaigns_active"] += active
            stats["totals"]["campaigns_paused"] += paused
            stats["totals"]["impressions"] += platform_stats["impressions"]
            stats["totals"]["clicks"] += platform_stats["clicks"]
            stats["totals"]["cost"] += platform_stats["cost"]
            stats["totals"]["conversions"] += platform_stats["conversions"]

        except Exception as e:
            stats["platforms"][plat] = {"error": str(e)}

    # Calculate CTR
    if stats["totals"]["impressions"] > 0:
        stats["totals"]["ctr"] = round(
            stats["totals"]["clicks"] / stats["totals"]["impressions"] * 100, 2
        )
    else:
        stats["totals"]["ctr"] = 0.0

    return stats


@router.get("/{client_id}/accounts")
async def get_client_accounts(client_id: str):
    """
    Alle Account-IDs eines Clients für jede Plattform
    """
    client = client_manager.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' nicht gefunden")

    accounts = {}
    for platform in ["google", "meta", "linkedin"]:
        account_id = client_manager.get_account_id(client_id, platform)
        prefix = client_manager.get_campaign_prefix(client_id, platform)
        if account_id:
            accounts[platform] = {
                "account_id": account_id,
                "campaign_prefix": prefix
            }

    return {
        "client_id": client_id,
        "client_name": client.name,
        "accounts": accounts
    }
