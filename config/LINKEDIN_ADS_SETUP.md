# LinkedIn Ads Setup Anleitung

Diese Anleitung erklärt, wie du LinkedIn Ads mit dem Ads Manager verbindest.

## Voraussetzungen

1. LinkedIn Unternehmensseite (Company Page)
2. LinkedIn Campaign Manager Zugang
3. Entwickler-Zugang auf [LinkedIn Developer Portal](https://www.linkedin.com/developers/)

## Schritt 1: LinkedIn App erstellen

1. Gehe zu [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Klicke auf **Create app**
3. Fülle die Felder aus:
   - **App name**: z.B. "Ads Manager Integration"
   - **LinkedIn Page**: Wähle deine Unternehmensseite
   - **App logo**: Optional
4. Akzeptiere die Nutzungsbedingungen
5. Klicke auf **Create app**

## Schritt 2: API-Berechtigungen anfordern

Nach der App-Erstellung musst du Berechtigungen beantragen:

1. Gehe zu **Products** Tab
2. Beantrage Zugriff auf:
   - **Marketing Developer Platform** (für Ads API)
   - **Advertising API** (optional, für erweiterte Funktionen)

**Hinweis**: Die Freigabe kann 1-3 Werktage dauern.

## Schritt 3: OAuth 2.0 Scopes konfigurieren

Unter **Auth** Tab, stelle sicher dass folgende Scopes aktiviert sind:

- `r_ads` - Lesen von Ad Account Daten
- `r_ads_reporting` - Lesen von Reporting Daten
- `rw_ads` - Lesen und Schreiben von Ads (optional für Kampagnen-Management)
- `r_organization_social` - Organisationsdaten lesen

## Schritt 4: Access Token generieren

### Option A: OAuth 2.0 Flow (empfohlen für Produktion)

1. Authentifiziere über den OAuth Flow:
   ```
   https://www.linkedin.com/oauth/v2/authorization?
     response_type=code&
     client_id=YOUR_CLIENT_ID&
     redirect_uri=YOUR_REDIRECT_URI&
     scope=r_ads,r_ads_reporting,rw_ads
   ```

2. Tausche den Authorization Code gegen einen Access Token:
   ```bash
   curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
     -d "grant_type=authorization_code" \
     -d "code=YOUR_AUTH_CODE" \
     -d "redirect_uri=YOUR_REDIRECT_URI" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET"
   ```

### Option B: Developer Token (für Entwicklung/Testing)

1. Gehe zum **Auth** Tab deiner App
2. Scrolle zu **OAuth 2.0 tools**
3. Generiere einen Access Token für Testing

**Wichtig**: Developer Tokens haben eine begrenzte Gültigkeit (60 Tage).

## Schritt 5: Ad Account ID finden

1. Gehe zum [LinkedIn Campaign Manager](https://www.linkedin.com/campaignmanager/)
2. Wähle deinen Ad Account
3. Die ID findest du in der URL: `https://www.linkedin.com/campaignmanager/accounts/XXXXXXXX/`
4. Die Zahlenfolge `XXXXXXXX` ist deine Ad Account ID

## Schritt 6: Konfiguration in .env

Füge folgende Zeilen zu deiner `.env` Datei hinzu:

```env
# LinkedIn Ads
LINKEDIN_ACCESS_TOKEN=dein_access_token_hier
LINKEDIN_AD_ACCOUNT_ID=508123456
```

## Schritt 7: Verbindung testen

Starte den Server und teste die Verbindung:

```bash
curl -X GET "http://localhost:8000/api/campaigns/linkedin/508123456" \
  -H "X-API-Key: dein_api_key"
```

## Token-Erneuerung

LinkedIn Access Tokens laufen nach 60 Tagen ab. Für Produktionsumgebungen empfehlen wir:

1. Implementiere Refresh Token Flow
2. Oder nutze einen Cron-Job zur regelmäßigen Token-Erneuerung

### Refresh Token verwenden

```bash
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  -d "grant_type=refresh_token" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

## API-Limits

LinkedIn Marketing API hat folgende Rate Limits:

- **Standard**: 100 Requests pro Tag und Member
- **Mit Marketing Developer Platform**: 10.000+ Requests pro Tag

## Fehlerbehebung

### "Invalid token"
- Token abgelaufen → Neuen Token generieren
- Falsche Scopes → Scopes in App-Settings überprüfen

### "Access denied"
- Marketing Developer Platform nicht freigeschaltet
- Keine Berechtigung für diesen Ad Account

### "Resource not found"
- Falsche Ad Account ID
- Account existiert nicht oder wurde gelöscht

## Hilfreiche Links

- [LinkedIn Marketing API Documentation](https://learn.microsoft.com/en-us/linkedin/marketing/)
- [Campaign Manager](https://www.linkedin.com/campaignmanager/)
- [Developer Portal](https://www.linkedin.com/developers/)
- [OAuth 2.0 Guide](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow)

## Unterstützung

Bei Problemen:
1. Überprüfe die API-Dokumentation
2. Teste mit dem LinkedIn API Explorer
3. Kontaktiere den LinkedIn Support für API-Zugang
