"""API endpoints for ad group management."""
from typing import List

from fastapi import APIRouter, HTTPException, Depends

from api.security import verify_api_key
from models.ad_group import AdGroup, AdGroupCreate
from services.ads_manager import AdsManager, get_ads_manager

router = APIRouter(prefix="/ad-groups", tags=["Ad Groups"], dependencies=[Depends(verify_api_key)])


@router.get("/{provider}/{customer_id}/{campaign_id}", response_model=List[AdGroup])
async def get_ad_groups(
    provider: str,
    customer_id: str,
    campaign_id: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Alle Anzeigengruppen einer Kampagne abrufen

    - **provider**: google, meta, linkedin etc.
    - **customer_id**: Kunden-ID des Werbekontos
    - **campaign_id**: ID der Kampagne
    """
    try:
        ad_groups = await ads_manager.get_ad_groups(provider, customer_id, campaign_id)
        return ad_groups
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{provider}/{customer_id}/{campaign_id}", response_model=AdGroup)
async def create_ad_group(
    provider: str,
    customer_id: str,
    campaign_id: str,
    ad_group: AdGroupCreate,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Neue Anzeigengruppe erstellen

    - **name**: Name der Anzeigengruppe
    - **cpc_bid**: Optionaler CPC-Gebot in Euro
    """
    try:
        created = await ads_manager.create_ad_group(
            provider, customer_id, campaign_id, ad_group.model_dump()
        )
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
