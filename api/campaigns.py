"""API endpoints for campaign management."""
from typing import List

from fastapi import APIRouter, HTTPException, Depends

from api.security import verify_api_key
from models.campaign import Campaign, CampaignCreate, CampaignUpdate
from services.ads_manager import AdsManager, get_ads_manager

router = APIRouter(prefix="/campaigns", tags=["Campaigns"], dependencies=[Depends(verify_api_key)])


@router.get("/{provider}/{customer_id}", response_model=List[Campaign])
async def get_campaigns(
    provider: str,
    customer_id: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Alle Kampagnen eines Kunden abrufen

    - **provider**: google, meta, linkedin etc.
    - **customer_id**: Kunden-ID des Werbekontos
    """
    try:
        campaigns = await ads_manager.get_campaigns(provider, customer_id)
        return campaigns
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{provider}/{customer_id}/{campaign_id}", response_model=Campaign)
async def get_campaign(
    provider: str,
    customer_id: str,
    campaign_id: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """Einzelne Kampagne abrufen"""
    try:
        campaign = await ads_manager.get_campaign(provider, customer_id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Kampagne nicht gefunden")
        return campaign
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{provider}/{customer_id}", response_model=Campaign)
async def create_campaign(
    provider: str,
    customer_id: str,
    campaign: CampaignCreate,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Neue Kampagne erstellen

    - Kampagne wird standardmäßig PAUSIERT erstellt
    - Budget ist das Tagesbudget in Euro
    """
    try:
        created = await ads_manager.create_campaign(provider, customer_id, campaign)
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{provider}/{customer_id}/{campaign_id}", response_model=Campaign)
async def update_campaign(
    provider: str,
    customer_id: str,
    campaign_id: str,
    campaign: CampaignUpdate,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """Kampagne aktualisieren"""
    try:
        updated = await ads_manager.update_campaign(provider, customer_id, campaign_id, campaign)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{provider}/{customer_id}/{campaign_id}/pause")
async def pause_campaign(
    provider: str,
    customer_id: str,
    campaign_id: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """Kampagne pausieren"""
    try:
        success = await ads_manager.pause_campaign(provider, customer_id, campaign_id)
        return {"success": success, "message": "Kampagne pausiert"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{provider}/{customer_id}/{campaign_id}/enable")
async def enable_campaign(
    provider: str,
    customer_id: str,
    campaign_id: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """Kampagne aktivieren"""
    try:
        success = await ads_manager.enable_campaign(provider, customer_id, campaign_id)
        return {"success": success, "message": "Kampagne aktiviert"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{provider}/{customer_id}/{campaign_id}")
async def delete_campaign(
    provider: str,
    customer_id: str,
    campaign_id: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """Kampagne löschen"""
    try:
        success = await ads_manager.delete_campaign(provider, customer_id, campaign_id)
        return {"success": success, "message": "Kampagne gelöscht"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{provider}/{customer_id}/{campaign_id}/preview")
async def get_campaign_preview(
    provider: str,
    customer_id: str,
    campaign_id: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Kampagnen-Vorschau mit allen Anzeigen

    Gibt alle Ad-Gruppen und Anzeigen einer Kampagne zurück
    für eine detaillierte Vorschau.
    """
    try:
        preview = await ads_manager.get_campaign_preview(provider, customer_id, campaign_id)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
