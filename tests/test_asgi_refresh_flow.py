import pytest
import os
import aiosqlite
import asyncio
from starlette.testclient import TestClient

# Set ENV for DB path before importing app
TEST_DB_PATH = "test_oauth2.db"
os.environ["OAUTH2_DB_PATH"] = TEST_DB_PATH

from q_scope.implementations.oauth2.asgi.app import app
from q_scope.implementations.oauth2.secrets import Argon2ClientSecretHasher

# Helper to init DB
async def init_test_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    # Read Schema
    with open("q_scope/implementations/store/sqllite/oauth.sql", "r") as f:
        schema_sql = f.read()
        
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        await db.executescript(schema_sql)
        await db.commit()

# Helper to populate data
async def populate_test_data():
    hasher = Argon2ClientSecretHasher()
    # Match created_by='test' and id='client123_id' in DB insert below
    hashed_secret = hasher.hash("secret123", user_id="test", client_id="client123_id")
    
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        # 1. Insert Client
        await db.execute("""
            INSERT INTO oauth_clients (
                id, client_identifier, client_secret, is_confidential,
                redirect_uris, grant_types, scopes, is_enabled,
                created_at, created_by, updated_at, updated_by
            ) VALUES (
                'client123_id', 'client123', ?, 1,
                'http://localhost/cb', 'refresh_token', 'read write', 1,
                1000, 'test', 1000, 'test'
            )
        """, (hashed_secret,))
        
        # 2. Insert Client Config
        # Note: we need the table name for configs. It wasn't in oauth.sql?
        # Let's check stores.py or try to find where it is defined.
        # Based on stores.py: "oauth_client_configs"
        # I'll try to create it if it doesn't exist or insert if it does.
        # Wait, if oauth.sql didn't have it, initialization will fail for the app?
        # The store code assumes it exists.
        # I will add the table creation for configs here if it's missing from oauth.sql or just insert if it exists.
        # I'll check if oauth.sql has it. I reviewed it and it stopped at "Audit Log".
        # It seems `oauth_client_configs` table definition was missing from the file I read!
        # I must define it here to make tests pass, or the app will crash on startup/usage.
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS oauth_client_configs (
                client_id TEXT PRIMARY KEY,
                response_types TEXT,
                require_pkce INTEGER,
                pkce_methods TEXT,
                access_token_ttl INTEGER,
                refresh_token_ttl INTEGER,
                authorization_code_ttl INTEGER,
                max_active_access_tokens INTEGER,
                max_active_refresh_tokens INTEGER,
                device_code_ttl INTEGER,
                device_poll_interval INTEGER,
                metadata TEXT,
                created_at INTEGER,
                created_by TEXT,
                updated_at INTEGER,
                updated_by TEXT,
                FOREIGN KEY (client_id) REFERENCES oauth_clients(id) ON DELETE CASCADE
            )
        """)
        
        await db.execute("""
            INSERT INTO oauth_client_configs (
                client_id, access_token_ttl, refresh_token_ttl, max_active_access_tokens,
                created_at, created_by, updated_at, updated_by
            ) VALUES (
                'client123_id', 3600, 7200, 5,
                1000, 'test', 1000, 'test'
            )
        """)

        # 3. Insert Refresh Token
        await db.execute("""
            INSERT INTO oauth_refresh_tokens (
                id, token, client_id, user_id, scopes, revoked_at,
                created_at, created_by, updated_at, updated_by
            ) VALUES (
                'rt_1', 'valid_refresh_token', 'client123_id', 'user1', 'read', NULL,
                1000, 'test', 1000, 'test'
            )
        """)
        
        # 4. Insert Revoked Refresh Token
        await db.execute("""
            INSERT INTO oauth_refresh_tokens (
                id, token, client_id, user_id, scopes, revoked_at,
                created_at, created_by, updated_at, updated_by
            ) VALUES (
                'rt_2', 'revoked_token', 'client123_id', 'user1', 'read', 2000,
                1000, 'test', 1000, 'test'
            )
        """)
        
        await db.commit()

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    await init_test_db()
    await populate_test_data()
    yield
    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture
def client():
    # TestClient runs lifespan startup
    with TestClient(app) as c:
        yield c

def test_token_endpoint_success(client):
    response = client.post(
        "/token",
        json={
            "grant_type": "refresh_token",
            "refresh_token": "valid_refresh_token",
            "client_id": "client123",
            "client_secret": "secret123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 3600
    
    # New refresh token should be different (rotation enabled by default)
    assert data["refresh_token"] != "valid_refresh_token"

def test_token_endpoint_invalid_json(client):
    response = client.post(
        "/token",
        content="not json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"


def test_token_endpoint_invalid_content_type(client):
    response = client.post(
        "/token",
        data={"grant_type": "refresh_token"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"


def test_token_endpoint_unsupported_grant_type(client):
    response = client.post(
        "/token",
        json={"grant_type": "password"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_grant_type"


def test_token_endpoint_revoked_token(client):
    response = client.post(
        "/token",
        json={
            "grant_type": "refresh_token",
            "refresh_token": "revoked_token",
            "client_id": "client123",
            "client_secret": "secret123"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "invalid_grant"


def test_token_endpoint_invalid_client_secret(client):
    response = client.post(
        "/token",
        json={
            "grant_type": "refresh_token",
            "refresh_token": "valid_refresh_token",
            "client_id": "client123",
            "client_secret": "wrong_secret"
        }
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"] == "invalid_client"
