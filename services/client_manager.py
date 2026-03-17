"""Client Manager service - manages multi-client configuration."""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class PlatformConfig:
    """Platform configuration for a client."""
    customer_id: Optional[str] = None  # Google
    ad_account_id: Optional[str] = None  # Meta/LinkedIn
    campaign_prefix: str = ""


@dataclass
class Client:
    """Client/Company configuration."""
    id: str
    name: str
    short: str
    icon: str
    color: str
    description: str
    platforms: Dict[str, Optional[PlatformConfig]]

    def get_platform(self, platform: str) -> Optional[PlatformConfig]:
        """Get platform config, returns None if not configured."""
        return self.platforms.get(platform)

    def has_platform(self, platform: str) -> bool:
        """Check if client has this platform configured."""
        return self.platforms.get(platform) is not None


class ClientManager:
    """
    Manages multi-client configuration for ad management.

    Loads client definitions from config/clients.json and provides
    methods to access client info and filter campaigns by prefix.
    """

    def __init__(self, config_path: Optional[str] = None):
        self._clients: Dict[str, Client] = {}
        self._config_path = config_path or str(
            Path(__file__).parent.parent / "config" / "clients.json"
        )
        self._load_clients()

    def _load_clients(self):
        """Load clients from JSON config file."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for client_id, client_data in data.items():
                platforms = {}
                for platform, config in client_data.get("platforms", {}).items():
                    if config is None:
                        platforms[platform] = None
                    else:
                        platforms[platform] = PlatformConfig(
                            customer_id=config.get("customer_id"),
                            ad_account_id=config.get("ad_account_id"),
                            campaign_prefix=config.get("campaign_prefix", "")
                        )

                self._clients[client_id] = Client(
                    id=client_id,
                    name=client_data.get("name", client_id),
                    short=client_data.get("short", client_id[:3].upper()),
                    icon=client_data.get("icon", "🏢"),
                    color=client_data.get("color", "#6B7280"),
                    description=client_data.get("description", ""),
                    platforms=platforms
                )
        except FileNotFoundError:
            print(f"Warning: Client config not found at {self._config_path}")
        except json.JSONDecodeError as e:
            print(f"Error parsing client config: {e}")

    def get_client(self, client_id: str) -> Optional[Client]:
        """Get a client by ID."""
        return self._clients.get(client_id)

    def list_clients(self) -> List[Client]:
        """Get all clients."""
        return list(self._clients.values())

    def get_client_ids(self) -> List[str]:
        """Get all client IDs."""
        return list(self._clients.keys())

    def get_clients_for_platform(self, platform: str) -> List[Client]:
        """Get all clients that have a specific platform configured."""
        return [c for c in self._clients.values() if c.has_platform(platform)]

    def get_account_id(self, client_id: str, platform: str) -> Optional[str]:
        """Get the account ID for a client/platform combination."""
        client = self.get_client(client_id)
        if not client:
            return None

        platform_config = client.get_platform(platform)
        if not platform_config:
            return None

        if platform == "google":
            return platform_config.customer_id
        else:
            return platform_config.ad_account_id

    def get_campaign_prefix(self, client_id: str, platform: str) -> str:
        """Get the campaign prefix for a client/platform."""
        client = self.get_client(client_id)
        if not client:
            return ""

        platform_config = client.get_platform(platform)
        if not platform_config:
            return ""

        return platform_config.campaign_prefix

    def filter_campaigns_by_client(
        self,
        campaigns: List[Any],
        client_id: str,
        platform: str,
        name_field: str = "name"
    ) -> List[Any]:
        """
        Filter a list of campaigns to only those belonging to a client.

        Matches campaigns whose name starts with the client's prefix.
        """
        prefix = self.get_campaign_prefix(client_id, platform)
        if not prefix:
            return campaigns

        return [
            c for c in campaigns
            if hasattr(c, name_field) and getattr(c, name_field, "").startswith(prefix)
            or isinstance(c, dict) and c.get(name_field, "").startswith(prefix)
        ]

    def identify_client_from_campaign(
        self,
        campaign_name: str,
        platform: str
    ) -> Optional[str]:
        """
        Identify which client a campaign belongs to based on its name prefix.

        Returns client_id or None if no match.
        """
        for client_id, _ in self._clients.items():
            prefix = self.get_campaign_prefix(client_id, platform)
            if prefix and campaign_name.startswith(prefix):
                return client_id
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert all clients to a dictionary for JSON serialization."""
        return {
            client_id: {
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
            for client_id, client in self._clients.items()
        }


# Global instance
client_manager = ClientManager()
