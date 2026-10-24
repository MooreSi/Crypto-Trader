"""Who this client will send its token to.

Same rules as FOREX Trader's client (`cluster/remote/tls.py`, bugs/014):

* the internet path (`SERVER_HOST`) verifies the server against the private
  certificate authority bundled with the build (`ca_cert.pem`, copied
  verbatim from FOREX Trader -- it is the same server);
* the LAN path cannot (no certificate for the public address validates a
  local one), so it is trust-on-first-use: the first fingerprint seen for a
  host is pinned in this app's database and any change is refused.
"""
from __future__ import annotations

import hashlib
import ssl
from pathlib import Path

from backend.src.services.remote import pins_repo

SERVER_HOST = "217.155.25.160"
SERVER_PORT = 8443
BUNDLED_CA = Path(__file__).with_name("ca_cert.pem")


def is_ca_verified(host: str) -> bool:
    return host == SERVER_HOST and BUNDLED_CA.exists()


def client_ssl_context(host: str) -> ssl.SSLContext:
    if is_ca_verified(host):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_verify_locations(cafile=str(BUNDLED_CA))
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        return ctx
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def peer_fingerprint(ws) -> str:
    """SHA-256 of the certificate the peer presented, or "" if unreadable."""
    try:
        ssl_object = ws.transport.get_extra_info("ssl_object")
        der = ssl_object.getpeercert(binary_form=True)
        return hashlib.sha256(der).hexdigest() if der else ""
    except Exception:
        return ""


def peer_is_acceptable(host: str, presented: str) -> tuple[bool, str]:
    if is_ca_verified(host):
        return True, "verified against the bundled certificate authority"
    if not presented:
        return False, "no certificate presented"
    pinned = pins_repo.get(host)
    if not pinned:
        pins_repo.set(host, presented)
        return True, "pinned on first use"
    if pinned == presented:
        return True, "matches pinned certificate"
    return False, "certificate changed since it was pinned"
