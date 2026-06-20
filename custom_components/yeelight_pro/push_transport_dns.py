"""Source-only DNS fallback helpers kept out of Yeelight Pro runtime installs.

The production WebSocket transport does not import this module. Release and
local-HA verification guards forbid installing it so private push uses the
configured URL through Home Assistant/aiohttp directly.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import ipaddress
import socket
import struct
from urllib.parse import SplitResult, urlsplit, urlunsplit

FAKE_IP_NETWORKS = (
    ipaddress.ip_network("198.18.0.0/15"),
)
DNS_FALLBACK_SERVERS = ("1.1.1.1", "8.8.8.8")
DNS_RECORD_A = 1
DNS_RECORD_AAAA = 28
DNS_CLASS_IN = 1
DNS_FALLBACK_QUERY_TYPES = (DNS_RECORD_A, DNS_RECORD_AAAA)
DNS_QUERY_TIMEOUT_SECONDS = 1.0


@dataclass(frozen=True, slots=True)
class WebSocketIpFallback:
    """Connection target for bypassing local fake-ip DNS."""

    url: str
    headers: dict[str, str]
    server_hostname: str | None


def is_fake_ip_address(value: object) -> bool:
    """Return whether value is in the Clash fake-ip range."""
    try:
        address = ipaddress.ip_address(str(value))
    except ValueError:
        return False
    return any(address in network for network in FAKE_IP_NETWORKS)


async def websocket_ip_fallback(url: str) -> WebSocketIpFallback | None:
    """Return a direct-IP websocket target when local DNS returns fake-ip."""
    parts = urlsplit(url)
    host = parts.hostname
    if not host or _is_literal_ip(host):
        return None
    port = _url_port(parts)
    local_ips = await resolve_host_ips(host, port)
    if not any(is_fake_ip_address(ip) for ip in local_ips):
        return None
    real_ips = [
        ip for ip in await resolve_public_dns_ips(host) if not is_fake_ip_address(ip)
    ]
    if not real_ips:
        return None
    return WebSocketIpFallback(
        url=_replace_url_host(parts, real_ips[0]),
        headers={"Host": _host_header(parts)},
        server_hostname=host if parts.scheme == "wss" else None,
    )


async def resolve_host_ips(
    host: str,
    port: int | None,
    *,
    timeout: float = DNS_QUERY_TIMEOUT_SECONDS,
) -> list[str]:
    """Resolve host through the container resolver with a short timeout."""
    loop = asyncio.get_running_loop()
    try:
        infos = await asyncio.wait_for(
            loop.getaddrinfo(host, port, type=socket.SOCK_STREAM),
            timeout=timeout,
        )
    except (OSError, asyncio.TimeoutError):
        return []
    ips: list[str] = []
    for info in infos:
        try:
            ip = str(ipaddress.ip_address(info[4][0]))
        except (IndexError, ValueError):
            continue
        if ip not in ips:
            ips.append(ip)
    return ips


async def resolve_public_dns_ips(
    host: str,
    *,
    timeout: float = DNS_QUERY_TIMEOUT_SECONDS,
) -> list[str]:
    """Resolve host through direct public DNS packets, bypassing fake-ip DNS."""
    for server in DNS_FALLBACK_SERVERS:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_resolve_dns_server, host, server, timeout),
                timeout=timeout + 0.2,
            )
        except (OSError, ValueError, asyncio.TimeoutError):
            continue
    return []


def _resolve_dns_server(host: str, server: str, timeout: float) -> list[str]:
    """Resolve A/AAAA records from one DNS server using blocking UDP in a thread."""
    results: list[str] = []
    for query_type in DNS_FALLBACK_QUERY_TYPES:
        for ip in _query_dns(host, server, query_type, timeout):
            if ip not in results:
                results.append(ip)
    return results


def _query_dns(host: str, server: str, query_type: int, timeout: float) -> list[str]:
    query = _build_dns_query(host, query_type)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(query, (server, 53))
        response, _addr = sock.recvfrom(1232)
    return _parse_dns_response(response, query[:2], query_type)


def _build_dns_query(host: str, query_type: int) -> bytes:
    labels = host.encode("idna").decode("ascii").rstrip(".").split(".")
    if not labels or any(not label or len(label) > 63 for label in labels):
        raise ValueError("invalid DNS name")
    name = b"".join(bytes([len(label)]) + label.encode("ascii") for label in labels)
    header = struct.pack("!HHHHHH", 0x594C, 0x0100, 1, 0, 0, 0)
    return header + name + b"\x00" + struct.pack("!HH", query_type, DNS_CLASS_IN)


def _parse_dns_response(data: bytes, query_id: bytes, query_type: int) -> list[str]:
    if len(data) < 12 or data[:2] != query_id:
        return []
    _tid, flags, qdcount, ancount, _nscount, _arcount = struct.unpack(
        "!HHHHHH", data[:12]
    )
    if flags & 0x000F:
        return []
    offset = 12
    for _index in range(qdcount):
        offset = _skip_dns_name(data, offset) + 4
    ips: list[str] = []
    for _index in range(ancount):
        offset = _skip_dns_name(data, offset)
        if offset + 10 > len(data):
            return ips
        record_type, record_class, _ttl, data_len = struct.unpack(
            "!HHIH", data[offset : offset + 10]
        )
        offset += 10
        record_data = data[offset : offset + data_len]
        offset += data_len
        if record_class != DNS_CLASS_IN or record_type != query_type:
            continue
        if record_type == DNS_RECORD_A and data_len == 4:
            ips.append(str(ipaddress.ip_address(record_data)))
        elif record_type == DNS_RECORD_AAAA and data_len == 16:
            ips.append(str(ipaddress.ip_address(record_data)))
    return ips


def _skip_dns_name(data: bytes, offset: int) -> int:
    while offset < len(data):
        size = data[offset]
        if size == 0:
            return offset + 1
        if size & 0xC0 == 0xC0:
            return offset + 2
        offset += size + 1
    return offset


def _is_literal_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _url_port(parts: SplitResult) -> int | None:
    try:
        return parts.port
    except ValueError:
        return None


def _host_header(parts: SplitResult) -> str:
    return parts.netloc.rsplit("@", 1)[-1]


def _replace_url_host(parts: SplitResult, ip: str) -> str:
    address = ipaddress.ip_address(ip)
    host = f"[{address}]" if address.version == 6 else str(address)
    port = _url_port(parts)
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


__all__ = [
    "WebSocketIpFallback",
    "is_fake_ip_address",
    "resolve_host_ips",
    "resolve_public_dns_ips",
    "websocket_ip_fallback",
]
