import pytest
import asyncio
import sqlite3
import tempfile
import os
import uuid
import time
from typing import Optional

from q_scope.implementations.datastrutures import (
    OAuthClient, OAuthClientConfig, RefreshToken, AccessToken
)
from q_scope.implementations.errors import OAuthErrors
from q_scope.implementations.store.sqllite.pypika_imp.stores import (
    OAuthClientStore,
    OAuthClientConfigStore,
    AccessTokenStore,
    RefreshTokenStore,
    AuditLogStore
)
from q_scope.implementations.oauth2.oauth_flows.refresh_token_flow import RefreshTokenFlow
from q_scope.implementations.errors.exceptions import OAuthException

# ============================================================================
# Helpers & Mocks
# ============================================================================

class MockClock:
    def now(self) -> int:
        return int(time.time())

class MockLogger:
    def info(self, event, **kwargs):
        pass
    def error(self, event, **kwargs):
        pass

class MockHasher:
    def verify(self, secret, hashed_secret, user_id, client_id):
        # CMS style: secret == hashed_secret for test simplicity or specific value
        return secret == "valid_secret"

class CompositeStorage:
    def __init__(self, db_path):
        self.clients = OAuthClientStore(db_path)
        self.client_configs = OAuthClientConfigStore(db_path)
        self.access_tokens = AccessTokenStore(db_path)
        self.refresh_tokens = RefreshTokenStore(db_path)
        self.audit_logs = AuditLogStore(db_path)

@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def setup_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Clients
    cursor.execute("""
        CREATE TABLE oauth_clients (
            id TEXT PRIMARY KEY,
            client_identifier TEXT UNIQUE NOT NULL,
            client_secret TEXT,
            is_confidential INTEGER NOT NULL,
            redirect_uris TEXT NOT NULL,
            grant_types TEXT NOT NULL,
            scopes TEXT,
            is_enabled INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            created_by TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            updated_by TEXT NOT NULL
        )
    """)
    
    # 2. Configs
    cursor.execute("""
        CREATE TABLE oauth_client_configs (
            client_id TEXT PRIMARY KEY,
            response_types TEXT NOT NULL,
            require_pkce INTEGER NOT NULL,
            pkce_methods TEXT,
            access_token_ttl INTEGER NOT NULL,
            refresh_token_ttl INTEGER,
            authorization_code_ttl INTEGER NOT NULL,
            max_active_access_tokens INTEGER,
            max_active_refresh_tokens INTEGER,
            device_code_ttl INTEGER,
            device_poll_interval INTEGER,
            metadata TEXT,
            created_at INTEGER NOT NULL,
            created_by TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            updated_by TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES oauth_clients(id)
        )
    """)

    # 3. Access Tokens
    cursor.execute("""
        CREATE TABLE oauth_access_tokens (
            id TEXT PRIMARY KEY,
            token TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            user_id TEXT,
            scopes TEXT,
            expires_at INTEGER NOT NULL,
            revoked_at INTEGER,
            created_at INTEGER NOT NULL,
            created_by TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            updated_by TEXT NOT NULL
        )
    """)

    # 4. Refresh Tokens
    cursor.execute("""
        CREATE TABLE oauth_refresh_tokens (
            id TEXT PRIMARY KEY,
            token TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            user_id TEXT,
            scopes TEXT,
            revoked_at INTEGER,
            created_at INTEGER NOT NULL,
            created_by TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            updated_by TEXT NOT NULL
        )
    """)

    # 5. Audit Log
    cursor.execute("""
        CREATE TABLE oauth_audit_log (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            subject TEXT,
            client_id TEXT,
            user_id TEXT,
            metadata TEXT,
            created_at INTEGER NOT NULL,
            created_by TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            updated_by TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

@pytest.fixture
def storage(db_path, setup_database):
    return CompositeStorage(db_path)

@pytest.fixture
def flow(storage):
    config = type("Config", (), {"rotate_refresh_tokens": True})()
    clock = MockClock()
    logger = MockLogger()
    hasher = MockHasher()
    return RefreshTokenFlow(storage, clock, config, logger, hasher)

# ============================================================================
# Tests
# ============================================================================

@pytest.mark.asyncio
async def test_refresh_token_success(flow, storage):
    """Test successful refresh token usage with rotation."""
    ray_id = "ray_success"
    
    # 1. Setup Client
    client_id = str(uuid.uuid4())
    await storage.clients.insert(OAuthClient(
        id=client_id,
        client_identifier="test_client",
        client_secret="hashed_secret", # MockHasher expects 'valid_secret' input to match this? No, MockHasher compares input 'valid_secret' to stored hash?
        # MockHasher logic: return secret == "valid_secret"
        # Since AuthenticateClientCondition passes context["client_secret"] as secret, 
        # I just need to pass "valid_secret" in context.
        # The stored client_secret is irrelevant for MockHasher provided logic, but needed for DB constraint.
        is_confidential=True,
        redirect_uris="", grant_types="refresh_token", scopes="read write",
        is_enabled=True, created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)
    
    await storage.client_configs.insert(OAuthClientConfig(
        client_id=client_id, response_types="token", require_pkce=False, pkce_methods=None,
        access_token_ttl=3600, refresh_token_ttl=7200, authorization_code_ttl=600,
        max_active_access_tokens=None, max_active_refresh_tokens=None,
        device_code_ttl=None, device_poll_interval=None, metadata=None,
        created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)

    # 2. Setup Existing Refresh Token
    rt_token = "valid_refresh_token"
    rt_id = str(uuid.uuid4())
    await storage.refresh_tokens.insert(RefreshToken(
        id=rt_id, token=rt_token, client_id=client_id, user_id="user_1",
        scopes="read write", revoked_at=None,
        created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)

    # 3. Execute Flow
    context = {
        "refresh_token": rt_token,
        "client_id": "test_client",
        "client_secret": "valid_secret"
    }
    
    result = await flow.execute(context=context, ray_id=ray_id)
    
    # 4. Assertions
    assert result["access_token"] is not None
    assert result["token_type"] == "Bearer"
    assert result["expires_in"] == 3600
    assert result["refresh_token"] is not None
    assert result["refresh_token"] != rt_token # Rotated
    
    # Check old token revoked
    old_rt = (await storage.refresh_tokens.get_by_id(rt_id, ray_id)).client_message
    assert old_rt.revoked_at is not None
    
    # Check new access token persisted
    at_result = await storage.access_tokens.get_by_token(result["access_token"], ray_id)
    assert at_result.status is True
    assert at_result.client_message.scopes == "read write"

@pytest.mark.asyncio
async def test_refresh_token_scope_downsizing(flow, storage):
    """Test requesting a subset of scopes."""
    ray_id = "ray_scope_down"
    
    # 1. Setup Client
    client_id = str(uuid.uuid4())
    await storage.clients.insert(OAuthClient(
        id=client_id, client_identifier="test_client_scope", client_secret="any",
        is_confidential=True, redirect_uris="", grant_types="refresh_token", scopes="read write",
        is_enabled=True, created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)
    
    await storage.client_configs.insert(OAuthClientConfig(
        client_id=client_id, response_types="token", require_pkce=False, pkce_methods=None,
        access_token_ttl=3600, refresh_token_ttl=7200, authorization_code_ttl=600,
        max_active_access_tokens=None, max_active_refresh_tokens=None,
        device_code_ttl=None, device_poll_interval=None, metadata=None,
        created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)

    # 2. Setup Refresh Token
    rt_token = "rt_scope_full"
    await storage.refresh_tokens.insert(RefreshToken(
        id=str(uuid.uuid4()), token=rt_token, client_id=client_id, user_id="user_1",
        scopes="read write", revoked_at=None,
        created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)

    # 3. Execute with Subset
    context = {
        "refresh_token": rt_token,
        "client_id": "test_client_scope",
        "client_secret": "valid_secret",
        "scope": "read"
    }
    
    result = await flow.execute(context=context, ray_id=ray_id)
    
    assert result["scope"] == "read"
    
    # Verify persisted access token has reduced scope
    at = (await storage.access_tokens.get_by_token(result["access_token"], ray_id)).client_message
    assert at.scopes == "read"


@pytest.mark.asyncio
async def test_refresh_token_invalid_scope(flow, storage):
    """Test requesting a superset of scopes (should fail)."""
    ray_id = "ray_scope_invalid"
    
    client_id = str(uuid.uuid4())
    await storage.clients.insert(OAuthClient(
        id=client_id, client_identifier="test_client_inv", client_secret="any",
        is_confidential=True, redirect_uris="", grant_types="refresh_token", scopes="read",
        is_enabled=True, created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)
    
    await storage.client_configs.insert(OAuthClientConfig(
        client_id=client_id, response_types="token", require_pkce=False, pkce_methods=None,
        access_token_ttl=3600, refresh_token_ttl=None, authorization_code_ttl=600,
        max_active_access_tokens=None, max_active_refresh_tokens=None,
        device_code_ttl=None, device_poll_interval=None, metadata=None,
        created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)

    rt_token = "rt_scope_read"
    await storage.refresh_tokens.insert(RefreshToken(
        id=str(uuid.uuid4()), token=rt_token, client_id=client_id, user_id="user_1",
        scopes="read", revoked_at=None,
        created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)

    context = {
        "refresh_token": rt_token,
        "client_id": "test_client_inv",
        "client_secret": "valid_secret",
        "scope": "read write" # 'write' is not in original 'read'
    }
    
    with pytest.raises(OAuthException) as excinfo:
        await flow.execute(context=context, ray_id=ray_id)
    
    assert excinfo.value.error_code == OAuthErrors.INVALID_SCOPE

@pytest.mark.asyncio
async def test_refresh_token_revoked(flow, storage):
    """Test using a revoked refresh token."""
    ray_id = "ray_revoked"
    
    client_id = str(uuid.uuid4())
    await storage.clients.insert(OAuthClient(
        id=client_id, client_identifier="test_client_rev", client_secret="any",
        is_confidential=True, redirect_uris="", grant_types="refresh_token", scopes="read",
        is_enabled=True, created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)
    
    await storage.client_configs.insert(OAuthClientConfig(
        client_id=client_id, response_types="token", require_pkce=False, pkce_methods=None,
        access_token_ttl=3600, refresh_token_ttl=None, authorization_code_ttl=600,
        max_active_access_tokens=None, max_active_refresh_tokens=None,
        device_code_ttl=None, device_poll_interval=None, metadata=None,
        created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)

    rt_token = "rt_revoked"
    await storage.refresh_tokens.insert(RefreshToken(
        id=str(uuid.uuid4()), token=rt_token, client_id=client_id, user_id="user_1",
        scopes="read", revoked_at=12345, # Revoked
        created_at=0, created_by="test", updated_at=0, updated_by="test"
    ), ray_id)

    context = {
        "refresh_token": rt_token,
        "client_id": "test_client_rev",
        "client_secret": "valid_secret"
    }
    
    with pytest.raises(OAuthException) as excinfo:
        await flow.execute(context=context, ray_id=ray_id)
    
    assert excinfo.value.error_code == OAuthErrors.INVALID_GRANT
