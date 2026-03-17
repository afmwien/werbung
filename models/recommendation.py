"""Google Ads Recommendations models."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class RecommendationType(str, Enum):
    """Types of Google Ads recommendations."""

    CAMPAIGN_BUDGET = "campaign_budget"
    KEYWORD = "keyword"
    TEXT_AD = "text_ad"
    TARGET_CPA_OPT_IN = "target_cpa_opt_in"
    MAXIMIZE_CONVERSIONS_OPT_IN = "maximize_conversions_opt_in"
    ENHANCED_CPC_OPT_IN = "enhanced_cpc_opt_in"
    SEARCH_PARTNERS_OPT_IN = "search_partners_opt_in"
    MAXIMIZE_CLICKS_OPT_IN = "maximize_clicks_opt_in"
    OPTIMIZE_AD_ROTATION = "optimize_ad_rotation"
    KEYWORD_MATCH_TYPE = "keyword_match_type"
    MOVE_UNUSED_BUDGET = "move_unused_budget"
    FORECASTING_CAMPAIGN_BUDGET = "forecasting_campaign_budget"
    TARGET_ROAS_OPT_IN = "target_roas_opt_in"
    RESPONSIVE_SEARCH_AD = "responsive_search_ad"
    MARGINAL_ROI_CAMPAIGN_BUDGET = "marginal_roi_campaign_budget"
    USE_BROAD_MATCH_KEYWORD = "use_broad_match_keyword"
    RESPONSIVE_SEARCH_AD_ASSET = "responsive_search_ad_asset"
    UPGRADE_SMART_SHOPPING_CAMPAIGN_TO_PERFORMANCE_MAX = "upgrade_smart_shopping_campaign_to_performance_max"
    RESPONSIVE_SEARCH_AD_IMPROVE_AD_STRENGTH = "responsive_search_ad_improve_ad_strength"
    DISPLAY_EXPANSION_OPT_IN = "display_expansion_opt_in"
    UPGRADE_LOCAL_CAMPAIGN_TO_PERFORMANCE_MAX = "upgrade_local_campaign_to_performance_max"
    RAISE_TARGET_CPA_BID_TOO_LOW = "raise_target_cpa_bid_too_low"
    FORECASTING_SET_TARGET_ROAS = "forecasting_set_target_roas"
    CALLOUT_ASSET = "callout_asset"
    SITELINK_ASSET = "sitelink_asset"
    CALL_ASSET = "call_asset"
    SHOPPING_ADD_AGE_GROUP = "shopping_add_age_group"
    SHOPPING_ADD_COLOR = "shopping_add_color"
    SHOPPING_ADD_GENDER = "shopping_add_gender"
    SHOPPING_ADD_SIZE = "shopping_add_size"
    SHOPPING_ADD_GTIN = "shopping_add_gtin"
    SHOPPING_ADD_MORE_IDENTIFIERS = "shopping_add_more_identifiers"
    SHOPPING_ADD_PRODUCTS_TO_CAMPAIGN = "shopping_add_products_to_campaign"
    SHOPPING_FIX_DISAPPROVED_PRODUCTS = "shopping_fix_disapproved_products"
    SHOPPING_MIGRATE_REGULAR_SHOPPING_CAMPAIGN_OFFERS_TO_PERFORMANCE_MAX = "shopping_migrate_regular_shopping_campaign_offers_to_performance_max"
    UNKNOWN = "unknown"


class RecommendationImpact(BaseModel):
    """Impact metrics for a recommendation."""

    base_metrics_impressions: Optional[int] = None
    base_metrics_clicks: Optional[int] = None
    base_metrics_cost_micros: Optional[int] = None
    base_metrics_conversions: Optional[float] = None

    potential_metrics_impressions: Optional[int] = None
    potential_metrics_clicks: Optional[int] = None
    potential_metrics_cost_micros: Optional[int] = None
    potential_metrics_conversions: Optional[float] = None

    @property
    def impressions_uplift(self) -> Optional[float]:
        """Prozentuale Steigerung der Impressionen."""
        if self.base_metrics_impressions and self.potential_metrics_impressions:
            return ((self.potential_metrics_impressions - self.base_metrics_impressions) / self.base_metrics_impressions) * 100
        return None

    @property
    def clicks_uplift(self) -> Optional[float]:
        """Prozentuale Steigerung der Klicks."""
        if self.base_metrics_clicks and self.potential_metrics_clicks:
            return ((self.potential_metrics_clicks - self.base_metrics_clicks) / self.base_metrics_clicks) * 100
        return None

    @property
    def conversions_uplift(self) -> Optional[float]:
        """Prozentuale Steigerung der Conversions."""
        if self.base_metrics_conversions and self.potential_metrics_conversions:
            return ((self.potential_metrics_conversions - self.base_metrics_conversions) / self.base_metrics_conversions) * 100
        return None


class BudgetRecommendation(BaseModel):
    """Budget-specific recommendation details."""

    current_budget_micros: Optional[int] = None
    recommended_budget_micros: Optional[int] = None
    budget_increase_micros: Optional[int] = None

    @property
    def current_budget_euros(self) -> Optional[float]:
        """Aktuelles Budget in Euro."""
        if self.current_budget_micros:
            return self.current_budget_micros / 1_000_000
        return None

    @property
    def recommended_budget_euros(self) -> Optional[float]:
        """Empfohlenes Budget in Euro."""
        if self.recommended_budget_micros:
            return self.recommended_budget_micros / 1_000_000
        return None


class KeywordRecommendation(BaseModel):
    """Keyword-specific recommendation details."""

    keyword: Optional[str] = None
    match_type: Optional[str] = None
    estimated_weekly_clicks: Optional[int] = None
    estimated_weekly_cost_micros: Optional[int] = None


class Recommendation(BaseModel):
    """Google Ads Recommendation."""

    resource_name: str
    recommendation_type: RecommendationType
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    ad_group_id: Optional[str] = None

    # Impact
    impact: Optional[RecommendationImpact] = None

    # Type-specific details
    budget_recommendation: Optional[BudgetRecommendation] = None
    keyword_recommendation: Optional[KeywordRecommendation] = None

    # Human-readable
    description: Optional[str] = None
    dismissed: bool = False

    class Config:
        """Pydantic config."""

        from_attributes = True


class RecommendationsResponse(BaseModel):
    """Response containing list of recommendations."""

    customer_id: str
    total_count: int
    recommendations: List[Recommendation]
    optimization_score: Optional[float] = None  # 0-100%
