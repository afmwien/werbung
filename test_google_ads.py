"""Test Google Ads API Verbindung"""
from google.ads.googleads.client import GoogleAdsClient

def test_connection():
    try:
        # Client aus YAML laden
        client = GoogleAdsClient.load_from_storage("config/google-ads.yaml")

        # Einfache Abfrage: Accessible Customers
        customer_service = client.get_service("CustomerService")
        accessible_customers = customer_service.list_accessible_customers()

        print("✅ Verbindung erfolgreich!")
        print("\nZugängliche Kunden-IDs:")
        for resource_name in accessible_customers.resource_names:
            customer_id = resource_name.split("/")[-1]
            print(f"  - {customer_id}")

    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    test_connection()
