================================================================================
META ADS API - EINRICHTUNGSANLEITUNG
================================================================================

Diese Anleitung beschreibt, wie du die Meta (Facebook/Instagram) Ads API
für die Management-App einrichtest.


1. FACEBOOK DEVELOPER APP ERSTELLEN
────────────────────────────────────────────────────────────────────────────────

1. Gehe zu: https://developers.facebook.com/
2. Erstelle einen Developer Account (falls nicht vorhanden)
3. Klicke auf "Meine Apps" → "App erstellen"
4. Wähle "Business" als App-Typ
5. Gib einen App-Namen ein (z.B. "Ads Manager API")
6. Notiere dir:
   - App-ID
   - App-Secret (unter Einstellungen → Allgemein)


2. MARKETING API AKTIVIEREN
────────────────────────────────────────────────────────────────────────────────

1. In deiner App: "Produkte hinzufügen"
2. Suche "Marketing API" und klicke "Einrichten"
3. Die Marketing API ist jetzt für deine App aktiviert


3. ACCESS TOKEN ERSTELLEN
────────────────────────────────────────────────────────────────────────────────

OPTION A: System User Token (EMPFOHLEN für Server-Apps)
───────────────────────────────────────────────────────

1. Gehe zum Business Manager: https://business.facebook.com/
2. Einstellungen → Benutzer → Systembenutzer
3. "Hinzufügen" → Namen eingeben → "Admin" Rolle wählen
4. "Assets hinzufügen" → Werbekonten auswählen → Volle Kontrolle
5. "Token generieren" → App auswählen → Berechtigung "ads_management" auswählen
6. Token kopieren und sicher speichern!

   ⚠️ WICHTIG: System User Tokens laufen NICHT ab!


OPTION B: User Access Token (für Tests)
───────────────────────────────────────

1. Gehe zu: https://developers.facebook.com/tools/explorer/
2. Wähle deine App aus
3. Klicke "Generate Access Token"
4. Erteile die Berechtigungen:
   - ads_management
   - ads_read
   - business_management
5. Token kopieren

   ⚠️ User Tokens laufen nach ~60 Tagen ab!


4. WERBEKONTO-ID FINDEN
────────────────────────────────────────────────────────────────────────────────

1. Gehe zum Werbeanzeigenmanager: https://www.facebook.com/adsmanager/
2. Die Account-ID steht in der URL: act=XXXXXXXXXX
3. Format für die API: act_XXXXXXXXXX (mit "act_" Prefix)


5. .ENV KONFIGURATION
────────────────────────────────────────────────────────────────────────────────

Erstelle/erweitere die .env Datei im Projektverzeichnis:

```
# Meta Ads API
META_APP_ID=123456789012345
META_APP_SECRET=abcdef1234567890abcdef1234567890
META_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxx

# Mehrere Accounts (optional, JSON-Format)
META_ACCOUNTS={"kunde1": {"app_id": "123", "app_secret": "abc", "token": "xxx"}}
```


6. API VERWENDEN
────────────────────────────────────────────────────────────────────────────────

REST API Endpoints:

# Alle Kampagnen eines Accounts abrufen
GET /api/campaigns/meta/act_XXXXXXXXXX

# Einzelne Kampagne abrufen
GET /api/campaigns/meta/act_XXXXXXXXXX/{campaign_id}

# Neue Kampagne erstellen
POST /api/campaigns/meta/act_XXXXXXXXXX
Content-Type: application/json
{
    "name": "Meine Kampagne",
    "campaign_type": "display",
    "budget_amount": 20.0
}

# Kampagne pausieren
POST /api/campaigns/meta/act_XXXXXXXXXX/{campaign_id}/pause

# Kampagne aktivieren
POST /api/campaigns/meta/act_XXXXXXXXXX/{campaign_id}/enable

# Performance Report
GET /api/reports/meta/act_XXXXXXXXXX?start_date=2024-01-01&end_date=2024-01-31


7. MEHRERE ACCOUNTS VERWALTEN
────────────────────────────────────────────────────────────────────────────────

Wenn du mehrere Business Manager / Kundenkonten verwalten willst:

Python Code Beispiel:

```python
from providers.meta_ads import MetaAdsMultiAccountManager

# Manager initialisieren
manager = MetaAdsMultiAccountManager()

# Accounts hinzufügen
manager.add_account(
    account_name="kunde_abc",
    app_id="123456",
    app_secret="secret123",
    access_token="EAAxxxx_kunde_abc"
)

manager.add_account(
    account_name="kunde_xyz",
    app_id="789012",
    app_secret="secret456",
    access_token="EAAxxxx_kunde_xyz"
)

# Kampagnen von Kunde ABC abrufen
provider_abc = manager.get_provider("kunde_abc")
campaigns = await provider_abc.get_campaigns("act_111111111")

# Kampagnen von Kunde XYZ abrufen
provider_xyz = manager.get_provider("kunde_xyz")
campaigns = await provider_xyz.get_campaigns("act_222222222")
```


8. BERECHTIGUNGEN (PERMISSIONS)
────────────────────────────────────────────────────────────────────────────────

Erforderliche Berechtigungen für den Access Token:

LESEN:
- ads_read              → Anzeigen und Kampagnen lesen
- read_insights         → Performance-Daten abrufen

SCHREIBEN:
- ads_management        → Kampagnen erstellen/bearbeiten/löschen

BUSINESS:
- business_management   → Mehrere Werbekonten im Business Manager


9. RATE LIMITS
────────────────────────────────────────────────────────────────────────────────

Meta API Rate Limits:
- Standard: 200 Calls pro Stunde pro User
- Bei hoher App-Nutzung: Automatisch erhöht

Best Practices:
- Batch-Requests verwenden wenn möglich
- Caching für häufig abgerufene Daten
- Exponential Backoff bei 429 Errors


10. TROUBLESHOOTING
────────────────────────────────────────────────────────────────────────────────

Fehler: "Invalid OAuth access token"
→ Token ist abgelaufen oder ungültig. Neuen Token generieren.

Fehler: "User does not have permission"
→ System User hat keine Berechtigung für das Werbekonto.
  Im Business Manager unter Assets dem User Zugriff geben.

Fehler: "Application does not have the capability"
→ Marketing API ist nicht für die App aktiviert.
  In der App unter "Produkte" die Marketing API hinzufügen.

Fehler: "Ad account is disabled"
→ Das Werbekonto wurde deaktiviert (Zahlung/Policy).
  Im Werbeanzeigenmanager prüfen.


================================================================================
LINKS
================================================================================

- Meta Marketing API Docs: https://developers.facebook.com/docs/marketing-apis/
- Graph API Explorer: https://developers.facebook.com/tools/explorer/
- Business Manager: https://business.facebook.com/
- Werbeanzeigenmanager: https://www.facebook.com/adsmanager/

================================================================================
