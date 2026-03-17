from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models.ad import Ad, AdCreate
from services.ads_manager import AdsManager, get_ads_manager
from api.security import verify_api_key

router = APIRouter(prefix="/ads", tags=["Ads"], dependencies=[Depends(verify_api_key)])


@router.get("/{provider}/{customer_id}/{ad_group_id}", response_model=List[Ad])
async def get_ads(
    provider: str,
    customer_id: str,
    ad_group_id: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Alle Anzeigen einer Anzeigengruppe abrufen

    - **provider**: google, meta, linkedin etc.
    - **customer_id**: Kunden-ID des Werbekontos
    - **ad_group_id**: ID der Anzeigengruppe
    """
    try:
        ads = await ads_manager.get_ads(provider, customer_id, ad_group_id)
        return ads
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider}/{customer_id}/{ad_group_id}", response_model=Ad)
async def create_ad(
    provider: str,
    customer_id: str,
    ad_group_id: str,
    ad: AdCreate,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Neue Responsive Search Ad erstellen

    - **headlines**: Liste von Headlines (min. 3, max. 15)
    - **descriptions**: Liste von Descriptions (min. 2, max. 4)
    - **final_url**: Ziel-URL der Anzeige
    """
    try:
        created = await ads_manager.create_ad(
            provider, customer_id, ad_group_id, ad.model_dump()
        )
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
