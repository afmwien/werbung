"""Liste Client-Accounts des Managers"""
from google.ads.googleads.client import GoogleAdsClient

def list_clients():
    """Alle verknüpften Client-Accounts des Managers auflisten."""
    client = GoogleAdsClient.load_from_storage("config/google-ads.yaml")

    # Manager-Account ID
    manager_id = "5984286476"

    ga_service = client.get_service("GoogleAdsService")

    # Liste alle verknüpften Kundenaccounts
    query = """
        SELECT
            customer_client.id,
            customer_client.descriptive_name,
            customer_client.level,
            customer_client.manager,
            customer_client.status
        FROM customer_client
        WHERE customer_client.level <= 1
    """

    print(f"Client-Accounts unter Manager {manager_id}:")
    print("-" * 50)

    try:
        response = ga_service.search(customer_id=manager_id, query=query)

        for row in response:
            cc = row.customer_client
            manager_label = " (Manager)" if cc.manager else ""
            print(f"  ID: {cc.id} - {cc.descriptive_name}{manager_label}")
            print(f"     Status: {cc.status.name}, Level: {cc.level}")

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Fehler: {e}")

if __name__ == "__main__":
    list_clients()
