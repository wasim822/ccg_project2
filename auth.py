import os
from auth0_server_python.auth_server.server_client import ServerClient
from dotenv import load_dotenv

load_dotenv()


class MemoryStateStore:
    """In-memory state store for session data (development only)."""

    def __init__(self):
        self._data = {}

    async def get(self, key, options=None):
        return self._data.get(key)

    async def set(self, key, value, options=None):
        self._data[key] = value

    async def delete(self, key, options=None):
        self._data.pop(key, None)

    async def delete_by_logout_token(self, claims, options=None):
        # Backchannel logout support (not required for dev)
        pass


class MemoryTransactionStore:
    """In-memory transaction store for OAuth flows (development only)."""

    def __init__(self):
        self._data = {}

    async def get(self, key, options=None):
        return self._data.get(key)

    async def set(self, key, value, options=None):
        self._data[key] = value

    async def delete(self, key, options=None):
        self._data.pop(key, None)


# Singleton stores (live for the duration of the process)
state_store = MemoryStateStore()
transaction_store = MemoryTransactionStore()

# Auth0 ServerClient – reads credentials from .env
auth0_domain = os.getenv("AUTH0_DOMAIN")
auth0_client_id = os.getenv("AUTH0_CLIENT_ID")
auth0_client_secret = os.getenv("AUTH0_CLIENT_SECRET")
auth0_secret = os.getenv("AUTH0_SECRET")
auth0_redirect_uri = os.getenv("AUTH0_REDIRECT_URI")

if not all([auth0_domain, auth0_client_id, auth0_client_secret, auth0_secret, auth0_redirect_uri]):
    raise ValueError("Missing required Auth0 environment variables. Please check your .env file.")

auth0 = ServerClient(
    domain=str(auth0_domain),
    client_id=str(auth0_client_id),
    client_secret=str(auth0_client_secret),
    secret=str(auth0_secret),
    redirect_uri=str(auth0_redirect_uri),
    state_store=state_store,
    transaction_store=transaction_store,
    authorization_params={
        "scope": "openid profile email",
    },
)
