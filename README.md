# Ads Manager

Einheitliche API zur Verwaltung von Werbekampagnen auf verschiedenen Plattformen.

## Quick Start

1. **Dependencies installieren**
   ```bash
   pip install -r requirements.txt
   ```

2. **Konfiguration**
   ```bash
   cp .env.example .env
   cp config/google-ads.yaml.example config/google-ads.yaml
   # Werte in beiden Dateien ausfüllen
   ```

3. **Server starten**
   ```bash
   python main.py
   # oder
   uvicorn main:app --reload
   ```

4. **API Docs öffnen**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Projektstruktur

```
werbung/
├── main.py                 # FastAPI App Einstiegspunkt
├── requirements.txt
├── .env.example
│
├── config/                 # Konfiguration
│   ├── settings.py        # App Settings (aus .env)
│   └── google-ads.yaml    # Google Ads Credentials
│
├── models/                 # Datenmodelle (Pydantic)
│   ├── campaign.py        # Kampagnen-Model
│   ├── ad_group.py        # Anzeigengruppen-Model
│   ├── ad.py              # Anzeigen-Model
│   └── report.py          # Report-Models
│
├── providers/              # Ads-Plattform-Integrationen
│   ├── base.py            # Abstrakte Basis-Klasse
│   ├── google_ads.py      # Google Ads Provider
│   └── [meta_ads.py]      # [Später] Meta Provider
│
├── services/               # Business Logic
│   └── ads_manager.py     # Zentraler Provider-Manager
│
└── api/                    # API Endpoints
    ├── campaigns.py       # Kampagnen-Routes
    └── reports.py         # Report-Routes
```

## API Endpoints

### Kampagnen
- `GET    /api/campaigns/{provider}/{customer_id}` - Alle Kampagnen
- `GET    /api/campaigns/{provider}/{customer_id}/{id}` - Eine Kampagne
- `POST   /api/campaigns/{provider}/{customer_id}` - Erstellen
- `PUT    /api/campaigns/{provider}/{customer_id}/{id}` - Aktualisieren
- `POST   /api/campaigns/{provider}/{customer_id}/{id}/pause` - Pausieren
- `POST   /api/campaigns/{provider}/{customer_id}/{id}/enable` - Aktivieren
- `DELETE /api/campaigns/{provider}/{customer_id}/{id}` - Löschen

### Reports
- `GET /api/reports/{provider}/{customer_id}/performance` - Performance-Bericht

## Neuen Provider hinzufügen

1. Neue Datei in `providers/` erstellen (z.B. `meta_ads.py`)
2. `AdsProvider` Basis-Klasse erweitern
3. Alle abstrakten Methoden implementieren
4. In `services/ads_manager.py` registrieren

Beispiel:
```python
# providers/meta_ads.py
from providers.base import AdsProvider

class MetaAdsProvider(AdsProvider):
    provider_name = "meta"

    async def get_campaigns(self, customer_id: str):
        # Meta API aufrufen...
        pass
```

## Google Ads Setup

1. Google Cloud Projekt erstellen
2. Google Ads API aktivieren
3. OAuth 2.0 Credentials erstellen
4. Developer Token beantragen (kann Wochen dauern!)
5. Refresh Token generieren

Docs: https://developers.google.com/google-ads/api/docs/first-call/overview

## Lizenz

MIT
