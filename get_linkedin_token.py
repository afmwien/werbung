"""
LinkedIn OAuth 2.0 Token Generator

Dieses Skript hilft bei der Generierung eines LinkedIn Access Tokens.
"""
import os
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
import httpx
from dotenv import load_dotenv

load_dotenv()

# LinkedIn App Credentials aus .env
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI = "https://werbung.afm-software.com/callback"  # Muss in LinkedIn App registriert sein

# Benötigte Scopes für Ads API
SCOPES = [
    "r_ads",           # Ads lesen
    "r_ads_reporting", # Ads Reporting lesen
    "rw_ads",          # Ads schreiben
    "r_organization_social",  # Organization Daten
]


def get_authorization_url():
    """Generiert die Authorization URL"""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": "random_state_string"  # Für CSRF-Schutz
    }
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
    return auth_url


def exchange_code_for_token(authorization_code: str) -> dict:
    """Tauscht den Authorization Code gegen einen Access Token"""
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"

    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    response = httpx.post(token_url, data=data)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Fehler: {response.status_code}")
        print(response.text)
        return {}


def main():
    """Interaktiver LinkedIn OAuth 2.0 Token Generator."""
    print("=" * 60)
    print("LinkedIn OAuth 2.0 Token Generator")
    print("=" * 60)
    print()

    # Schritt 1: Authorization URL
    auth_url = get_authorization_url()
    print("Schritt 1: Öffne diese URL im Browser und autorisiere die App:")
    print()
    print(auth_url)
    print()

    # Browser öffnen
    open_browser = input("Browser automatisch öffnen? (j/n): ").lower()
    if open_browser == 'j':
        webbrowser.open(auth_url)

    print()
    print("Schritt 2: Nach der Autorisierung wirst du weitergeleitet.")
    print("Die URL enthält einen 'code' Parameter.")
    print()
    print("Beispiel: https://api.afm.wien/callback?code=XXXXXXXX&state=...")
    print()

    # Schritt 2: Code eingeben
    callback_url = input("Gib die komplette Redirect-URL ein (oder nur den Code): ")

    # Code extrahieren
    if "code=" in callback_url:
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)
        code = params.get("code", [""])[0]
    else:
        code = callback_url.strip()

    if not code:
        print("Kein Code gefunden!")
        return

    print()
    print(f"Code gefunden: {code[:20]}...")
    print()

    # Schritt 3: Token abrufen
    print("Schritt 3: Tausche Code gegen Access Token...")
    token_data = exchange_code_for_token(code)

    if token_data:
        print()
        print("=" * 60)
        print("SUCCESS! Access Token erhalten:")
        print("=" * 60)
        print()
        print(f"Access Token: {token_data.get('access_token', 'N/A')}")
        print(f"Token Type: {token_data.get('token_type', 'N/A')}")
        print(f"Expires In: {token_data.get('expires_in', 'N/A')} Sekunden")
        print()
        print("Füge diesen Token zu deiner .env Datei hinzu:")
        print()
        print(f"LINKEDIN_ACCESS_TOKEN={token_data.get('access_token', '')}")
        print()
    else:
        print("Token-Austausch fehlgeschlagen!")


if __name__ == "__main__":
    main()
