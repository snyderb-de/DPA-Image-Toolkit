"""Per-launch capability shared by the launcher and local API."""

import secrets

REQUEST_TOKEN = secrets.token_urlsafe(32)
