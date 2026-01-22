"""
End-to-End Tests for ClientRegistrar

These tests verify the complete client registration flow with actual SQLite persistence.
Tests cover all success scenarios and failure modes.
"""

import pytest
import asyncio
import sqlite3
import tempfile
import os
import json
from pathlib import Path

from q_scope.implementations.datastrutures import RegistrationRequest
from q_scope.implementations.oauth2.clients.registrar import ClientRegistrar
from q_scope.implementations.store.sqllite.pypika_imp.stores import (
    OAuthClientStore,
    OAuthClientConfigStore
)
from q_scope.implementations.oauth2.secrets import (
    DefaultClientSecretGenerator,
    Argon2ClientSecretHasher
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def db_path():
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def setup_database(db_path):
    """Create the required database tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create oauth_clients table
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
    
    # Create oauth_client_configs table
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
            FOREIGN KEY (client_id) REFERENCES oauth_clients(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()


@pytest.fixture
def registrar(db_path, setup_database):
    """Create a ClientRegistrar instance with all dependencies."""
    client_store = OAuthClientStore(db_path=db_path)
    config_store = OAuthClientConfigStore(db_path=db_path)
    secret_generator = DefaultClientSecretGenerator(byte_length=32)
    secret_hasher = Argon2ClientSecretHasher()
    
    return ClientRegistrar(
        client_store=client_store,
        config_store=config_store,
        secret_generator=secret_generator,
        secret_hasher=secret_hasher
    )


@pytest.fixture
def valid_confidential_request():
    """Create a valid registration request for a confidential client."""
    return RegistrationRequest(
        user_id="user_123",
        client_identifier="confidential-app",
        is_confidential=True,
        redirect_uris=["https://app.com/callback", "https://app.com/oauth"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scopes=["read", "write", "profile"],
        require_pkce=True,
        pkce_methods=["S256"],
        access_token_ttl=3600,
        refresh_token_ttl=2592000,
        authorization_code_ttl=600,
        max_active_access_tokens=5,
        max_active_refresh_tokens=3,
        device_code_ttl=None,
        device_poll_interval=None,
        metadata={"app_name": "Confidential App", "version": "1.0"}
    )


@pytest.fixture
def valid_public_request():
    """Create a valid registration request for a public client."""
    return RegistrationRequest(
        user_id="user_456",
        client_identifier="public-mobile-app",
        is_confidential=False,
        redirect_uris=["myapp://oauth/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scopes=["read", "profile"],
        require_pkce=True,
        pkce_methods=["S256"],
        access_token_ttl=1800,
        refresh_token_ttl=None,
        authorization_code_ttl=300,
        max_active_access_tokens=10,
        max_active_refresh_tokens=None,
        device_code_ttl=None,
        device_poll_interval=None,
        metadata={"platform": "iOS", "version": "2.1"}
    )


# ============================================================================
# Success Tests
# ============================================================================

@pytest.mark.asyncio
async def test_register_confidential_client_success(registrar, valid_confidential_request, db_path):
    """Test successful registration of a confidential client with all data persisted."""
    # Register the client
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_001"
    )
    
    # Verify the result is successful
    assert result.status is True
    assert result.ray_id == "test_ray_001"
    
    # Verify the client object
    client = result.client_message
    assert client is not None
    assert client.client_identifier == "confidential-app"
    assert client.is_confidential is True
    assert client.client_secret is not None  # Has plaintext secret
    assert len(client.client_secret) > 30  # Secret should be long
    assert client.user_id == "user_123"
    assert client.redirect_uris == ["https://app.com/callback", "https://app.com/oauth"]
    assert client.grant_types == ["authorization_code", "refresh_token"]
    assert client.response_types == ["code"]
    assert client.scopes == ["read", "write", "profile"]
    assert client.require_pkce is True
    assert client.pkce_methods == ["S256"]
    assert client.access_token_ttl == 3600
    assert client.refresh_token_ttl == 2592000
    assert client.authorization_code_ttl == 600
    assert client.max_active_access_tokens == 5
    assert client.max_active_refresh_tokens == 3
    assert client.is_enabled is True
    
    # Verify data in oauth_clients table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM oauth_clients WHERE id = ?", (client.id,))
    row = cursor.fetchone()
    assert row is not None
    assert row[1] == "confidential-app"  # client_identifier
    assert row[2] is not None  # client_secret (hashed)
    assert row[2] != client.client_secret  # Should be hashed, not plaintext
    assert row[3] == 1  # is_confidential
    assert row[4] == "https://app.com/callback https://app.com/oauth"  # redirect_uris
    assert row[5] == "authorization_code refresh_token"  # grant_types
    assert row[6] == "read write profile"  # scopes
    assert row[7] == 1  # is_enabled
    
    # Verify data in oauth_client_configs table
    cursor.execute("SELECT * FROM oauth_client_configs WHERE client_id = ?", (client.id,))
    config_row = cursor.fetchone()
    assert config_row is not None
    assert config_row[0] == client.id  # client_id
    assert config_row[1] == "code"  # response_types
    assert config_row[2] == 1  # require_pkce
    assert config_row[3] == "S256"  # pkce_methods
    assert config_row[4] == 3600  # access_token_ttl
    assert config_row[5] == 2592000  # refresh_token_ttl
    assert config_row[6] == 600  # authorization_code_ttl
    assert config_row[7] == 5  # max_active_access_tokens
    assert config_row[8] == 3  # max_active_refresh_tokens
    assert config_row[9] is None  # device_code_ttl
    assert config_row[10] is None  # device_poll_interval
    
    # Verify metadata is JSON
    metadata = json.loads(config_row[11])
    assert metadata == {"app_name": "Confidential App", "version": "1.0"}
    
    conn.close()


@pytest.mark.asyncio
async def test_register_public_client_success(registrar, valid_public_request, db_path):
    """Test successful registration of a public client (no secret)."""
    # Register the client
    result = await registrar.register_client(
        request=valid_public_request,
        ray_id="test_ray_002"
    )
    
    # Verify the result is successful
    assert result.status is True
    
    # Verify the client object
    client = result.client_message
    assert client.client_identifier == "public-mobile-app"
    assert client.is_confidential is False
    assert client.client_secret is None  # Public clients have no secret
    assert client.require_pkce is True  # PKCE required for public clients
    assert client.refresh_token_ttl is None  # No refresh tokens for public clients
    
    # Verify data in oauth_clients table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT client_secret, is_confidential FROM oauth_clients WHERE id = ?", (client.id,))
    row = cursor.fetchone()
    assert row[0] is None  # No secret stored
    assert row[1] == 0  # is_confidential = False
    
    # Verify config in oauth_client_configs table
    cursor.execute("SELECT refresh_token_ttl, max_active_refresh_tokens FROM oauth_client_configs WHERE client_id = ?", (client.id,))
    config_row = cursor.fetchone()
    assert config_row[0] is None  # No refresh token TTL
    assert config_row[1] is None  # No refresh token limit
    
    conn.close()


@pytest.mark.asyncio
async def test_register_client_with_minimal_config(registrar, db_path):
    """Test registration with minimal configuration (null values for optional fields)."""
    request = RegistrationRequest(
        user_id="user_789",
        client_identifier="minimal-client",
        is_confidential=True,
        redirect_uris=["https://minimal.com/callback"],
        grant_types=["client_credentials"],
        response_types=["token"],
        scopes=["api"],
        require_pkce=False,
        pkce_methods=None,  # Optional
        access_token_ttl=3600,
        refresh_token_ttl=None,  # Optional
        authorization_code_ttl=600,
        max_active_access_tokens=None,  # Optional
        max_active_refresh_tokens=None,  # Optional
        device_code_ttl=None,  # Optional
        device_poll_interval=None,  # Optional
        metadata=None  # Optional
    )
    
    result = await registrar.register_client(request=request, ray_id="test_ray_003")
    
    assert result.status is True
    client = result.client_message
    
    # Verify optional fields are None
    assert client.pkce_methods is None
    assert client.refresh_token_ttl is None
    assert client.max_active_access_tokens is None
    assert client.max_active_refresh_tokens is None
    assert client.device_code_ttl is None
    assert client.device_poll_interval is None
    
    # Verify in database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT pkce_methods, metadata FROM oauth_client_configs WHERE client_id = ?", (client.id,))
    row = cursor.fetchone()
    assert row[0] is None  # pkce_methods
    assert row[1] is None  # metadata
    
    conn.close()


# ============================================================================
# Validation Failure Tests
# ============================================================================

@pytest.mark.asyncio
async def test_register_client_missing_user_id(registrar, valid_confidential_request):
    """Test failure when user_id is missing."""
    valid_confidential_request.user_id = ""
    
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_004"
    )
    
    assert result.status is False
    assert result.error_code == "INVALID_REQUEST"
    assert "user_id" in result.client_message


@pytest.mark.asyncio
async def test_register_client_missing_client_identifier(registrar, valid_confidential_request):
    """Test failure when client_identifier is missing."""
    valid_confidential_request.client_identifier = ""
    
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_005"
    )
    
    assert result.status is False
    assert result.error_code == "INVALID_REQUEST"
    assert "client_identifier" in result.client_message


@pytest.mark.asyncio
async def test_register_client_no_redirect_uris(registrar, valid_confidential_request):
    """Test failure when no redirect URIs are provided."""
    valid_confidential_request.redirect_uris = []
    
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_006"
    )
    
    assert result.status is False
    assert result.error_code == "INVALID_REQUEST"
    assert "redirect_uri" in result.client_message


@pytest.mark.asyncio
async def test_register_client_no_grant_types(registrar, valid_confidential_request):
    """Test failure when no grant types are provided."""
    valid_confidential_request.grant_types = []
    
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_007"
    )
    
    assert result.status is False
    assert result.error_code == "INVALID_REQUEST"
    assert "grant_type" in result.client_message


@pytest.mark.asyncio
async def test_register_client_invalid_access_token_ttl(registrar, valid_confidential_request):
    """Test failure when access_token_ttl is invalid (non-positive)."""
    valid_confidential_request.access_token_ttl = 0
    
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_008"
    )
    
    assert result.status is False
    assert result.error_code == "INVALID_REQUEST"
    assert "access_token_ttl" in result.client_message


@pytest.mark.asyncio
async def test_register_client_invalid_authorization_code_ttl(registrar, valid_confidential_request):
    """Test failure when authorization_code_ttl is invalid (negative)."""
    valid_confidential_request.authorization_code_ttl = -1
    
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_009"
    )
    
    assert result.status is False
    assert result.error_code == "INVALID_REQUEST"
    assert "authorization_code_ttl" in result.client_message


# ============================================================================
# Duplicate Client Tests
# ============================================================================

@pytest.mark.asyncio
async def test_register_duplicate_client_identifier(registrar, valid_confidential_request, db_path):
    """Test failure when attempting to register a duplicate client_identifier."""
    # Register first client
    result1 = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_010"
    )
    assert result1.status is True
    
    # Attempt to register second client with same identifier
    result2 = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_011"
    )
    
    assert result2.status is False
    assert result2.error_code == "DUPLICATE_CLIENT_IDENTIFIER"
    assert "confidential-app" in result2.client_message
    
    # Verify only one client exists in database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM oauth_clients WHERE client_identifier = ?", ("confidential-app",))
    count = cursor.fetchone()[0]
    assert count == 1
    conn.close()


# ============================================================================
# Retrieval Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_client_by_id(registrar, valid_confidential_request):
    """Test retrieving a client by its ID."""
    # Register client
    register_result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_012"
    )
    client_id = register_result.client_message.id
    
    # Retrieve by ID
    result = await registrar.get_client_by_id(
        client_id=client_id,
        ray_id="test_ray_013"
    )
    
    assert result.status is True
    oauth_client = result.client_message
    assert oauth_client.id == client_id
    assert oauth_client.client_identifier == "confidential-app"


@pytest.mark.asyncio
async def test_get_client_by_id_not_found(registrar):
    """Test retrieving a non-existent client by ID."""
    result = await registrar.get_client_by_id(
        client_id="nonexistent-id",
        ray_id="test_ray_014"
    )
    
    assert result.status is False
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_client_by_identifier(registrar, valid_confidential_request):
    """Test retrieving a client by its identifier."""
    # Register client
    await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_015"
    )
    
    # Retrieve by identifier
    result = await registrar.get_client_by_identifier(
        client_identifier="confidential-app",
        ray_id="test_ray_016"
    )
    
    assert result.status is True
    oauth_client = result.client_message
    assert oauth_client.client_identifier == "confidential-app"


@pytest.mark.asyncio
async def test_get_client_by_identifier_not_found(registrar):
    """Test retrieving a non-existent client by identifier."""
    result = await registrar.get_client_by_identifier(
        client_identifier="nonexistent-identifier",
        ray_id="test_ray_017"
    )
    
    assert result.status is False
    assert result.error_code == "NOT_FOUND"


# ============================================================================
# Data Integrity Tests
# ============================================================================

@pytest.mark.asyncio
async def test_secret_is_hashed_in_database(registrar, valid_confidential_request, db_path):
    """Test that client secrets are hashed (not plaintext) in the database."""
    # Register client
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_018"
    )
    
    plaintext_secret = result.client_message.client_secret
    client_id = result.client_message.id
    
    # Retrieve hashed secret from database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT client_secret FROM oauth_clients WHERE id = ?", (client_id,))
    hashed_secret = cursor.fetchone()[0]
    conn.close()
    
    # Verify secret is hashed
    assert hashed_secret is not None
    assert hashed_secret != plaintext_secret
    assert hashed_secret.startswith("$argon2")  # Argon2 hash format


@pytest.mark.asyncio
async def test_both_tables_populated(registrar, valid_confidential_request, db_path):
    """Test that both oauth_clients and oauth_client_configs tables are populated."""
    # Register client
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_019"
    )
    client_id = result.client_message.id
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check oauth_clients table
    cursor.execute("SELECT COUNT(*) FROM oauth_clients WHERE id = ?", (client_id,))
    clients_count = cursor.fetchone()[0]
    assert clients_count == 1
    
    # Check oauth_client_configs table
    cursor.execute("SELECT COUNT(*) FROM oauth_client_configs WHERE client_id = ?", (client_id,))
    configs_count = cursor.fetchone()[0]
    assert configs_count == 1
    
    conn.close()


@pytest.mark.asyncio
async def test_foreign_key_relationship(registrar, valid_confidential_request, db_path):
    """Test that config has proper foreign key to client."""
    # Register client
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_020"
    )
    client_id = result.client_message.id
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get client_id from config table
    cursor.execute("SELECT client_id FROM oauth_client_configs WHERE client_id = ?", (client_id,))
    config_client_id = cursor.fetchone()[0]
    
    assert config_client_id == client_id
    
    conn.close()


# ============================================================================
# Multiple Clients Tests
# ============================================================================

@pytest.mark.asyncio
async def test_register_multiple_clients(registrar, valid_confidential_request, valid_public_request, db_path):
    """Test registering multiple different clients."""
    # Register confidential client
    result1 = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_021"
    )
    assert result1.status is True
    
    # Register public client
    result2 = await registrar.register_client(
        request=valid_public_request,
        ray_id="test_ray_022"
    )
    assert result2.status is True
    
    # Verify both are in database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM oauth_clients")
    clients_count = cursor.fetchone()[0]
    assert clients_count == 2
    
    cursor.execute("SELECT COUNT(*) FROM oauth_client_configs")
    configs_count = cursor.fetchone()[0]
    assert configs_count == 2
    
    conn.close()


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_register_client_with_empty_scopes_list(registrar, valid_confidential_request, db_path):
    """Test registration with empty scopes list (should store as None)."""
    valid_confidential_request.scopes = []
    
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_023"
    )
    
    assert result.status is True
    client = result.client_message
    assert client.scopes == []
    
    # Verify in database (should be None or empty string)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT scopes FROM oauth_clients WHERE id = ?", (client.id,))
    scopes = cursor.fetchone()[0]
    # Empty list serializes to empty string, but we handle it as None
    assert scopes is None or scopes == ""
    conn.close()


@pytest.mark.asyncio
async def test_register_client_audit_fields(registrar, valid_confidential_request, db_path):
    """Test that audit fields are properly set."""
    result = await registrar.register_client(
        request=valid_confidential_request,
        ray_id="test_ray_024"
    )
    
    client = result.client_message
    assert client.created_at > 0
    assert client.created_by == "user_123"
    
    # Verify in database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT created_at, created_by, updated_at, updated_by FROM oauth_clients WHERE id = ?", (client.id,))
    row = cursor.fetchone()
    assert row[0] > 0  # created_at
    assert row[1] == "user_123"  # created_by
    assert row[2] > 0  # updated_at
    assert row[3] == "user_123"  # updated_by
    assert row[0] == row[2]  # created_at == updated_at for new record
    
    conn.close()
