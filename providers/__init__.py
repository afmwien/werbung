"""Providers module - Ads platform integrations."""
from .base import AdsProvider
from .google_ads import GoogleAdsProvider
from .meta_ads import MetaAdsProvider, MetaAdsMultiAccountManager
from .linkedin_ads import LinkedInAdsProvider

# Später hinzufügen:
# from .tiktok_ads import TikTokAdsProvider
