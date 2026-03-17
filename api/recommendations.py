"""API endpoints for optimization recommendations."""
from fastapi import APIRouter, HTTPException, Depends

from api.security import verify_api_key
from models.recommendation import RecommendationsResponse
from services.ads_manager import AdsManager, get_ads_manager

router = APIRouter(prefix="/recommendations", tags=["Recommendations"], dependencies=[Depends(verify_api_key)])


@router.get("/{provider}/{customer_id}", response_model=RecommendationsResponse)
async def get_recommendations(
    provider: str,
    customer_id: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Optimierungsempfehlungen abrufen.

    Google's ML-basierte Empfehlungen für:
    - Budget-Optimierung
    - Keyword-Vorschläge
    - Bidding-Strategien
    - Anzeigen-Verbesserungen

    Returns:
    - Optimization Score (0-100%)
    - Liste aller Empfehlungen mit Impact-Metriken
    """
    try:
        provider_instance = ads_manager.get_provider(provider)

        if not hasattr(provider_instance, 'get_recommendations'):
            raise HTTPException(
                status_code=501,
                detail=f"Provider '{provider}' unterstützt keine Empfehlungen"
            )

        recommendations = await provider_instance.get_recommendations(customer_id)
        return recommendations
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{provider}/{customer_id}/apply")
async def apply_recommendation(
    provider: str,
    customer_id: str,
    recommendation_resource_name: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Eine Empfehlung anwenden.

    Wendet die empfohlene Änderung automatisch an (z.B. Budget erhöhen).
    """
    try:
        provider_instance = ads_manager.get_provider(provider)

        if not hasattr(provider_instance, 'apply_recommendation'):
            raise HTTPException(
                status_code=501,
                detail=f"Provider '{provider}' unterstützt keine Empfehlungen"
            )

        success = await provider_instance.apply_recommendation(customer_id, recommendation_resource_name)
        return {"success": success, "message": "Empfehlung angewendet" if success else "Fehler beim Anwenden"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{provider}/{customer_id}/dismiss")
async def dismiss_recommendation(
    provider: str,
    customer_id: str,
    recommendation_resource_name: str,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Eine Empfehlung ablehnen/ausblenden.

    Die Empfehlung wird nicht mehr angezeigt.
    """
    try:
        provider_instance = ads_manager.get_provider(provider)

        if not hasattr(provider_instance, 'dismiss_recommendation'):
            raise HTTPException(
                status_code=501,
                detail=f"Provider '{provider}' unterstützt keine Empfehlungen"
            )

        success = await provider_instance.dismiss_recommendation(customer_id, recommendation_resource_name)
        return {"success": success, "message": "Empfehlung abgelehnt" if success else "Fehler beim Ablehnen"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
