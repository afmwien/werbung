"""
API Security - API-Key Authentifizierung und IP-Whitelist
"""
from fastapi import Security, HTTPException, status, Request
from fastapi.security import APIKeyHeader, APIKeyQuery
from config.settings import settings

# API Key kann im Header oder Query-Parameter übergeben werden
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


def get_allowed_ips() -> set:
    """Gibt die erlaubten IPs als Set zurück."""
    if not settings.ALLOWED_IPS:
        return set()  # Leer = keine IP-Einschränkung
    return {ip.strip() for ip in settings.ALLOWED_IPS.split(",") if ip.strip()}


def get_client_ip(request: Request) -> str:
    """Ermittelt die echte Client-IP (auch hinter Proxy)."""
    # X-Forwarded-For Header (von Reverse Proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Erste IP in der Kette ist die echte Client-IP
        return forwarded.split(",")[0].strip()
    # X-Real-IP Header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    # Fallback: Direkte Client-IP
    return request.client.host if request.client else "unknown"


async def verify_ip(request: Request) -> str:
    """
    Prüft nur die IP-Whitelist (ohne API-Key).
    Für Dashboard, Docs und andere geschützte Seiten.
    """
    allowed_ips = get_allowed_ips()
    if allowed_ips:
        client_ip = get_client_ip(request)
        if client_ip not in allowed_ips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"IP {client_ip} nicht erlaubt"
            )
    return get_client_ip(request)


async def verify_api_key(
    request: Request,
    header_key: str = Security(api_key_header),
    query_key: str = Security(api_key_query),
) -> str:
    """
    Verifiziert den API-Key und optional die Client-IP.

    Verwendung:
    - Header: X-API-Key: <your-api-key>
    - Query: ?api_key=<your-api-key>
    """
    # IP-Whitelist prüfen (falls konfiguriert)
    allowed_ips = get_allowed_ips()
    if allowed_ips:
        client_ip = get_client_ip(request)
        if client_ip not in allowed_ips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"IP {client_ip} nicht erlaubt"
            )

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
