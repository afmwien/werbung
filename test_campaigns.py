"""Test Google Ads API - Kampagnen abrufen"""
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

def test_campaigns():
    try:
        # Client aus YAML laden
        client = GoogleAdsClient.load_from_storage("config/google-ads.yaml")

        # Teste Zugriff auf Account 2936775113 (ohne Manager)
        customer_id = "2936775113"

        ga_service = client.get_service("GoogleAdsService")

        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.name
        """

        print(f"Frage Kampagnen für Customer {customer_id} ab...")
        response = ga_service.search(customer_id=customer_id, query=query)

        campaigns = []
        for row in response:
            campaigns.append({
                "id": row.campaign.id,
                "name": row.campaign.name,
                "status": row.campaign.status.name
            })

        print(f"✅ {len(campaigns)} Kampagnen gefunden:")
        for c in campaigns:
            print(f"  - {c['name']} (Status: {c['status']})")

    except GoogleAdsException as ex:
        print(f"❌ Google Ads Fehler: {ex.failure.errors[0].message}")
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    test_campaigns()
