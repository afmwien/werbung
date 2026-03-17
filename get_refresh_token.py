"""
Script zum Generieren des Google Ads Refresh Tokens
"""
from google_auth_oauthlib.flow import InstalledAppFlow

# OAuth Scopes für Google Ads
SCOPES = ['https://www.googleapis.com/auth/adwords']

def main():
    # Pfad zur heruntergeladenen JSON-Datei
    client_secrets_path = input("Pfad zur client_secret JSON-Datei: ").strip()

    if not client_secrets_path:
        client_secrets_path = r"C:\Users\User\Downloads\client_secret_399913375060-kj09g8phq6o042l6e9th5tdmuokf7otc.apps.googleusercontent.com.json"

    flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets_path,
        scopes=SCOPES
    )

    # Öffnet Browser für Authentifizierung
    print("\n🌐 Browser öffnet sich für Google-Anmeldung...")
    print("   Melde dich mit dem Google-Konto an, das Zugriff auf Google Ads hat.\n")

    credentials = flow.run_local_server(port=8080)

    print("\n" + "="*60)
    print("✅ ERFOLG! Hier ist dein Refresh Token:")
    print("="*60)
    print(f"\n{credentials.refresh_token}\n")
    print("="*60)
    print("\nKopiere diesen Token in deine .env oder google-ads.yaml Datei.")
    print("="*60)

if __name__ == "__main__":
    main()
