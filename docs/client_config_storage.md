# OAuth Client Configuration Storage - Design Document

## Problem Statement

The initial implementation was storing only OAuth client **identity** data (id, client_identifier, client_secret, etc.) but losing all **configuration** data (PKCE settings, token TTLs, limits, device flow parameters, etc.) that is critical for OAuth flow behavior.

## Solution: Separate Configuration Table

### Design Decision

We implemented a **separate `oauth_client_configs` table** with a 1:1 relationship to `oauth_clients`.

#### Why This Approach?

1. ✅ **Clean Separation of Concerns**
   - Client identity (who the client is) vs. Client configuration (how the client behaves)
   - Identity rarely changes; configuration may be updated frequently

2. ✅ **Schema-First Design**
   - Explicit, typed columns for all configuration fields
   - Queryable and indexable individual config parameters
   - No JSON blob ambiguity

3. ✅ **Extensibility**
   - Can add config versioning/history later
   - Can implement config templates for common patterns
   - Can audit config changes separately from identity changes

4. ✅ **Storage Agnostic**
   - Clear abstractions via `OAuthClientConfigStore`
   - Follows the same patterns as other stores
   - PyPika-based queries with named parameters

5. ✅ **Aligns with Framework Principles**
   - Matches the pattern of separate tables for tokens, codes, etc.
   - No ORM dependencies
   - Transparent SQL schema

## Implementation Details

### Data Models

#### OAuthClient (Identity)
```python
@dataclass(kw_only=True, slots=True)
class OAuthClient(AuditFields):
    id: str
    client_identifier: str
    client_secret: str | None
    is_confidential: bool
    redirect_uris: str          # Space-separated
    grant_types: str            # Space-separated
    scopes: str | None          # Space-separated
    is_enabled: bool
    # + AuditFields (created_at, created_by, updated_at, updated_by)
```

#### OAuthClientConfig (Configuration)
```python
@dataclass(kw_only=True, slots=True)
class OAuthClientConfig(AuditFields):
    client_id: str              # FK to oauth_clients.id
    
    # Response types
    response_types: str         # Space-separated
    
    # PKCE configuration
    require_pkce: bool
    pkce_methods: str | None    # Space-separated (e.g., "S256 plain")
    
    # Token lifetimes (seconds)
    access_token_ttl: int
    refresh_token_ttl: int | None
    authorization_code_ttl: int
    
    # Token limits
    max_active_access_tokens: int | None
    max_active_refresh_tokens: int | None
    
    # Device flow
    device_code_ttl: int | None
    device_poll_interval: int | None
    
    # Metadata
    metadata: str | None        # JSON string
    # + AuditFields
```

### Database Schema

#### oauth_clients Table
```sql
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
);
```

#### oauth_client_configs Table
```sql
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
);
```

### Storage Layer

#### OAuthClientConfigStore

Complete CRUD operations with named parameters:

```python
class OAuthClientConfigStore:
    async def insert(config: OAuthClientConfig, ray_id: str) -> SuccessResult | FailedResult
    async def get_by_client_id(client_id: str, ray_id: str) -> SuccessResult | FailedResult
    async def update(config: OAuthClientConfig, ray_id: str) -> SuccessResult | FailedResult
    async def delete_by_client_id(client_id: str, ray_id: str) -> SuccessResult | FailedResult
```

All queries use **named parameters** for clarity:
```python
query = Query.into(oauth_client_configs).columns(
    "client_id", "response_types", "require_pkce", ...
).insert(
    Parameter(":client_id"), Parameter(":response_types"), Parameter(":require_pkce"), ...
)

await db.execute(str(query), {
    "client_id": config.client_id,
    "response_types": config.response_types,
    "require_pkce": config.require_pkce,
    ...
})
```

### Service Layer Updates

#### ClientRegistrar

Updated to persist **both** client identity and configuration:

```python
class ClientRegistrar:
    def __init__(
        self,
        *,
        client_store: OAuthClientStore,
        config_store: OAuthClientConfigStore,  # NEW
        secret_generator: ClientSecretGenerator,
        secret_hasher: ClientSecretHasher,
    ):
        self._client_store = client_store
        self._config_store = config_store  # NEW
        ...
```

#### Registration Flow (Enhanced)

1. Validate registration request
2. Check for duplicate client identifier
3. Generate client ID
4. Generate & hash client secret (if confidential)
5. Create `OAuthClient` record (identity)
6. Create `OAuthClientConfig` record (configuration) ← **NEW**
7. Insert client identity to database
8. Insert client config to database ← **NEW**
9. **Rollback identity if config insertion fails** ← **NEW**
10. Return `Client` object with plaintext secret

```python
# Persist client identity
insert_result = await self._client_store.insert(oauth_client, ray_id)
if not insert_result.status:
    return insert_result

# Persist client configuration
config_result = await self._config_store.insert(oauth_config, ray_id)
if not config_result.status:
    # Rollback: delete the client we just inserted
    await self._client_store.delete_by_id(client_id, ray_id)
    return config_result
```

## Data Serialization

### Lists to Strings
```python
# Storage
redirect_uris: str = " ".join(["https://app.com/callback", "https://app.com/auth"])
# Result: "https://app.com/callback https://app.com/auth"

# Retrieval
redirect_uris: list[str] = stored_value.split()
```

### Metadata (JSON)
```python
# Storage
metadata: str = json.dumps({"app_name": "My App", "version": "1.0"})
# Result: '{"app_name": "My App", "version": "1.0"}'

# Retrieval
metadata: dict = json.loads(stored_value) if stored_value else None
```

## Usage Example

```python
from q_scope.implementations.oauth2.clients import ClientRegistrar
from q_scope.implementations.store.sqllite.pypika_imp.stores import (
    OAuthClientStore,
    OAuthClientConfigStore  # NEW
)
from q_scope.implementations.oauth2.secrets import (
    DefaultClientSecretGenerator,
    Argon2ClientSecretHasher
)

# Initialize stores
client_store = OAuthClientStore(db_path="/path/to/db.sqlite")
config_store = OAuthClientConfigStore(db_path="/path/to/db.sqlite")  # NEW

# Create registrar
registrar = ClientRegistrar(
    client_store=client_store,
    config_store=config_store,  # NEW
    secret_generator=DefaultClientSecretGenerator(),
    secret_hasher=Argon2ClientSecretHasher()
)

# Register client (config is persisted automatically)
result = await registrar.register_client(
    request=RegistrationRequest(...),
    ray_id="ray_123"
)
```

## Benefits

### For OAuth Flows

When implementing OAuth flows, you can now:

1. **Validate PKCE Requirements**
   ```python
   config = await config_store.get_by_client_id(client_id, ray_id)
   if config.require_pkce and not code_challenge:
       raise PKCERequiredError()
   ```

2. **Set Token Lifetimes**
   ```python
   config = await config_store.get_by_client_id(client_id, ray_id)
   expires_at = current_time + config.access_token_ttl
   ```

3. **Enforce Token Limits**
   ```python
   config = await config_store.get_by_client_id(client_id, ray_id)
   if config.max_active_refresh_tokens:
       # Implement FIFO token rotation
       ...
   ```

4. **Configure Device Flow**
   ```python
   config = await config_store.get_by_client_id(client_id, ray_id)
   poll_interval = config.device_poll_interval or 5
   device_code_ttl = config.device_code_ttl or 600
   ```

### For Administration

- Update client configuration without affecting identity
- Query clients by configuration parameters
- Audit configuration changes separately
- Implement configuration templates/presets

## Migration Path

### From Old Schema (No Config)

If you have existing clients without configuration, you can:

1. **Add default configurations**:
   ```python
   for client in existing_clients:
       config = OAuthClientConfig(
           client_id=client.id,
           response_types="code",
           require_pkce=not client.is_confidential,
           pkce_methods="S256" if not client.is_confidential else None,
           access_token_ttl=3600,  # Default 1 hour
           refresh_token_ttl=2592000 if client.is_confidential else None,
           authorization_code_ttl=600,  # Default 10 minutes
           max_active_access_tokens=None,
           max_active_refresh_tokens=None,
           device_code_ttl=None,
           device_poll_interval=None,
           metadata=None,
           created_at=client.created_at,
           created_by=client.created_by,
           updated_at=client.updated_at,
           updated_by=client.updated_by
       )
       await config_store.insert(config, ray_id)
   ```

## Future Enhancements

### 1. Configuration Versioning
Track config changes over time:
```sql
CREATE TABLE oauth_client_config_history (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    config_snapshot TEXT NOT NULL,  -- JSON
    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL
);
```

### 2. Configuration Templates
Reusable config presets:
```python
MOBILE_APP_CONFIG_TEMPLATE = {
    "require_pkce": True,
    "pkce_methods": ["S256"],
    "access_token_ttl": 1800,
    "refresh_token_ttl": None,
    ...
}
```

### 3. Dynamic Configuration
Hot-reload config without restarting:
```python
config_cache = ConfigCache(ttl=60)  # 60 second TTL
config = await config_cache.get_or_fetch(client_id)
```

### 4. Configuration Validation Rules
Custom validators per config field:
```python
class ConfigValidator:
    def validate_access_token_ttl(self, ttl: int) -> bool:
        return 300 <= ttl <= 86400  # 5 min to 24 hours
```

## Comparison with Alternatives

| Approach | Identity/Config Separation | Queryable | Versioning | Complexity |
|----------|---------------------------|-----------|------------|------------|
| **Separate Table** (Chosen) | ✅ | ✅ | Easy | Medium |
| Expand Main Table | ❌ | ✅ | Hard | Low |
| JSON Blob | ⚠️ Partial | ❌ | Hard | Low |
| Hybrid (Some + JSON) | ⚠️ Partial | ⚠️ Partial | Medium | Medium-High |

## Conclusion

The separate configuration table approach provides:
- ✅ **Complete data persistence** (no lost configuration)
- ✅ **Clean architecture** (separation of concerns)
- ✅ **Extensibility** (easy to add features)
- ✅ **Queryability** (can filter/search by config)
- ✅ **Transparency** (explicit schema, no hidden state)

This design ensures that all OAuth flows have access to the complete client configuration needed for proper protocol enforcement and security.
