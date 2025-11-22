from typing import Set, List, Optional
import os
import ipaddress
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


def get_allowed_networks() -> List[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """
    Get allowed IP networks from environment variable.
    """
    allowed_ips_str = os.getenv("PROMETHEUS_ALLOWED_IPS", "127.0.0.1")
    networks = []

    for ip_str in allowed_ips_str.split(","):
        ip_str = ip_str.strip()
        if not ip_str:
            continue

        try:
            if "/" in ip_str:
                networks.append(ipaddress.ip_network(ip_str, strict=False))
            else:
                networks.append(ipaddress.ip_network(ip_str, strict=False))
        except ValueError as e:
            print(f"Warning: Invalid IP/network '{ip_str}': {e}")

    return networks


def is_ip_allowed(client_ip: str, allowed_networks: List) -> bool:
    """
    Check if client IP is in any of the allowed networks.

    Args:
        client_ip: Client IP address as string
        allowed_networks: List of IPv4Network/IPv6Network objects

    Returns:
        True if IP is allowed, False otherwise
    """
    try:
        ip_obj = ipaddress.ip_address(client_ip)
        return any(ip_obj in network for network in allowed_networks)
    except ValueError:
        return False


class MetricsSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict /metrics endpoint to allowed IPs/networks only.
    """

    def __init__(self, app, allowed_networks: Optional[List[ipaddress.IPv4Network | ipaddress.IPv6Network]] = None):
        super().__init__(app)
        self.allowed_networks = allowed_networks or get_allowed_networks()

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            client_ip = self.get_client_ip(request)

            if not is_ip_allowed(client_ip, self.allowed_networks):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied to /metrics from {client_ip}"
                )

        return await call_next(request)

    def get_client_ip(self, request: Request) -> str:
        """
        Extract client IP, handling reverse proxy headers.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        if request.client:
            return request.client.host
        
        return "unknown"
