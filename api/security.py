"""
API Security - API-Key Authentifizierung
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from config.settings import settings

# API Key kann im Header oder Query-Parameter übergeben werden
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def verify_api_key(
    header_key: str = Security(api_key_header),
    query_key: str = Security(api_key_query),
) -> str:
    """
    Verifiziert den API-Key aus Header oder Query-Parameter.

    Verwendung:
    - Header: X-API-Key: <your-api-key>
    - Query: ?api_key=<your-api-key>
    """
    api_key = header_key or query_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API-Key fehlt. Übergebe ihn als 'X-API-Key' Header oder 'api_key' Query-Parameter."
        )

    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ungültiger API-Key"
        )

    return api_key
