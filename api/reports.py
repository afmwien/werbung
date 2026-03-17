from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from models.report import PerformanceReport
from services.ads_manager import AdsManager, get_ads_manager

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{provider}/{customer_id}/performance", response_model=PerformanceReport)
async def get_performance_report(
    provider: str,
    customer_id: str,
    start_date: str,
    end_date: str,
    campaign_ids: Optional[str] = None,
    ads_manager: AdsManager = Depends(get_ads_manager)
):
    """
    Performance-Bericht abrufen

    - **start_date**: Startdatum (YYYY-MM-DD)
    - **end_date**: Enddatum (YYYY-MM-DD)
    - **campaign_ids**: Optionale Kampagnen-IDs (kommagetrennt)
    """
    try:
        campaign_id_list = None
        if campaign_ids:
            campaign_id_list = [cid.strip() for cid in campaign_ids.split(",")]

        report = await ads_manager.get_performance_report(
            provider=provider,
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
            campaign_ids=campaign_id_list
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
