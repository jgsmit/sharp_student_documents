"""
Custom middleware for SharpDocs.

CanonicalDomainMiddleware
--------------------------
Enforces a single canonical domain so Google never sees duplicate content
across http/https or www/non-www variants.

Rules (only active when DEBUG=False):
  1. http://  → 301 redirect to https://
  2. www.sharpstudentdoc.com → 301 redirect to sharpstudentdoc.com
"""

from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CanonicalDomainMiddleware:
    """
    Redirects all traffic to the single canonical HTTPS non-www domain.
    Only active in production (DEBUG=False) to avoid breaking local dev.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip in DEBUG mode (local development)
        if settings.DEBUG:
            return self.get_response(request)

        host = request.get_host().lower()
        # Strip port if present (e.g. example.com:443)
        hostname = host.split(":")[0]

        needs_redirect = False
        canonical_host = hostname

        # Rule 1: Force non-www
        if hostname.startswith("www."):
            canonical_host = hostname[4:]  # strip "www."
            needs_redirect = True

        # Rule 2: Force HTTPS
        is_https = (
            request.is_secure()
            or request.META.get("HTTP_X_FORWARDED_PROTO", "").lower() == "https"
        )
        if not is_https:
            needs_redirect = True

        if needs_redirect:
            url = f"https://{canonical_host}{request.get_full_path()}"
            return HttpResponsePermanentRedirect(url)

        return self.get_response(request)
