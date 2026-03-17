"""Models module - Pydantic schemas."""
from .campaign import Campaign, CampaignCreate, CampaignUpdate, CampaignStatus
from .ad_group import AdGroup, AdGroupCreate
from .ad import Ad, AdCreate
from .report import PerformanceReport, PerformanceMetrics
from .recommendation import Recommendation, RecommendationsResponse, RecommendationType
