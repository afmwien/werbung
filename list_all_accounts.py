"""Liste alle verfügbaren Accounts von allen Plattformen."""
import httpx
from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv
import os

load_dotenv()


def list_google_accounts():
    """Liste Google Ads Accounts."""
    print("\n" + "=" * 60)
    print("GOOGLE ADS ACCOUNTS")
    print("=" * 60)

    try:
        client = GoogleAdsClient.load_from_storage('config/google-ads.yaml')

        query = '''
            SELECT customer.id, customer.descriptive_name, customer.currency_code
            FROM customer LIMIT 1
        '''
        ga_service = client.get_service('GoogleAdsService')

        # MCC selbst
        response = ga_service.search(customer_id='5984286476', query=query)
        for row in response:
            c = row.customer
            print(f"  [MCC] {c.id}: {c.descriptive_name} ({c.currency_code})")

        # Kunden-Accounts unter MCC
        client_query = '''
            SELECT
                customer_client.id,
                customer_client.descriptive_name,
                customer_client.currency_code,
                customer_client.manager,
                customer_client.status
            FROM customer_client
            WHERE customer_client.level > 0
        '''
        response = ga_service.search(customer_id='5984286476', query=client_query)
        for row in response:
            c = row.customer_client
            typ = 'MCC' if c.manager else 'Account'
            print(f"  [{typ}] {c.id}: {c.descriptive_name} ({c.currency_code}) - {c.status.name}")

        # Direkter Account
        response = ga_service.search(customer_id='2936775113', query=query)
        for row in response:
            c = row.customer
            print(f"  [Account] {c.id}: {c.descriptive_name} ({c.currency_code})")

    except Exception as e:
        print(f"  Fehler: {e}")


def list_meta_accounts():
    """Liste Meta/Facebook Ad Accounts."""
    print("\n" + "=" * 60)
    print("META ADS ACCOUNTS")
    print("=" * 60)

    token = os.getenv('META_ACCESS_TOKEN')
    if not token:
        print("  Kein META_ACCESS_TOKEN in .env")
        return

    status_map = {1: 'ACTIVE', 2: 'DISABLED', 3: 'UNSETTLED', 7: 'PENDING_REVIEW', 100: 'PENDING_CLOSURE', 101: 'CLOSED'}

    # Business AFM (bekannte ID)
    business_id = '1372785244559876'

    # Owned Ad Accounts
    r = httpx.get(
        f'https://graph.facebook.com/v19.0/{business_id}/owned_ad_accounts',
        params={'access_token': token, 'fields': 'id,name,account_id,currency,account_status'}
    )

    print(f"\n  Business: AFM (ID: {business_id})")

    if r.status_code == 200:
        accounts = r.json().get('data', [])
        if accounts:
            print("  Owned Ad Accounts:")
            for acc in accounts:
                status = status_map.get(acc.get('account_status'), f"Status {acc.get('account_status')}")
                print(f"      {acc['id']}: {acc.get('name', 'N/A')} ({acc.get('currency', '?')} - {status})")
        else:
            print("  (keine owned accounts)")

    # Client Ad Accounts
    r2 = httpx.get(
        f'https://graph.facebook.com/v19.0/{business_id}/client_ad_accounts',
        params={'access_token': token, 'fields': 'id,name,account_id,currency,account_status'}
    )

    if r2.status_code == 200:
        accounts = r2.json().get('data', [])
        if accounts:
            print("  Client Ad Accounts:")
            for acc in accounts:
                status = status_map.get(acc.get('account_status'), f"Status {acc.get('account_status')}")
                print(f"      {acc['id']}: {acc.get('name', 'N/A')} ({acc.get('currency', '?')} - {status})")

    # Direkt den bekannten Account pruefen
    print("\n  Bekannter Account:")
    r3 = httpx.get(
        'https://graph.facebook.com/v19.0/act_34886324',
        params={'access_token': token, 'fields': 'id,name,account_id,currency,account_status'}
    )
    if r3.status_code == 200:
        acc = r3.json()
        status = status_map.get(acc.get('account_status'), f"Status {acc.get('account_status')}")
        print(f"      {acc['id']}: {acc.get('name', 'N/A')} ({acc.get('currency', '?')} - {status})")


def list_linkedin_accounts():
    """Liste LinkedIn Ad Accounts."""
    print("\n" + "=" * 60)
    print("LINKEDIN ADS ACCOUNTS")
    print("=" * 60)

    token = os.getenv('LINKEDIN_ACCESS_TOKEN')
    if not token:
        print("  Kein LINKEDIN_ACCESS_TOKEN in .env")
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'X-Restli-Protocol-Version': '2.0.0'
    }

    # Ad Accounts abrufen
    r = httpx.get(
        'https://api.linkedin.com/v2/adAccountsV2',
        headers=headers,
        params={'q': 'search'}
    )

    if r.status_code == 200:
        data = r.json()
        accounts = data.get('elements', [])
        if accounts:
            for acc in accounts:
                status = acc.get('status', 'UNKNOWN')
                serving = ', '.join(acc.get('servingStatuses', []))
                print(f"  {acc['id']}: {acc.get('name', 'N/A')} ({acc.get('currency', '?')} - {status})")
                if serving:
                    print(f"      Serving: {serving}")
        else:
            print("  Keine Ad Accounts gefunden")

        paging = data.get('paging', {})
        total = paging.get('total', len(accounts))
        print(f"\n  Gesamt: {total} Account(s)")
    else:
        print(f"  Fehler: {r.status_code}")
        print(f"  {r.text[:500]}")


if __name__ == '__main__':
    print("\n SUCHE ALLE VERFUEGBAREN AD ACCOUNTS...")

    list_google_accounts()
    list_meta_accounts()
    list_linkedin_accounts()

    print("\n" + "=" * 60)
    print("FERTIG")
    print("=" * 60)
