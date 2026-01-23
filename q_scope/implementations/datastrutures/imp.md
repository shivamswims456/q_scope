# Data Structures Implementation

## Purpose

The `datastrutures/` directory defines all domain models, result types, and data transfer objects used throughout the q_scope framework. These structures provide type safety, clear contracts, and consistent data representation across all components.

## Architecture Context

Data structures are the **foundation** of the entire framework - every component depends on these types:

```
┌─────────────────────────────────────────┐
│         All Framework Components        │
│  (OAuth Flows, Storage, Errors, etc.)   │
└──────────────────┬──────────────────────┘
                   │ depends on
┌──────────────────▼──────────────────────┐
│        DATA STRUCTURES LAYER            │
│  - Domain Models                        │
│  - Result Types                         │
│  - Request/Response Objects             │
│  - Audit Fields                         │
└─────────────────────────────────────────┘
```

## Key Files & Logic

### `__init__.py`
Single file containing all data structures (233 lines). Uses Python `dataclasses` with `kw_only=True` and `slots=True` for memory efficiency and clarity.

## Data Structure Categories

### 1. Result Types

#### `Result`
Base result type with status flag:
```python
@dataclass(kw_only=True, slots=True)
class Result:
    status: bool           # True = success, False = failure
    client_message: Any    # Data or error message
    ray_id: str           # Request tracking ID
```

#### `SuccessResult`
Represents successful operations:
```python
@dataclass(kw_only=True, slots=True)
class SuccessResult:
    status: bool = True
    client_message: Any = None  # Operation result data
    ray_id: str
```

#### `FailedResult`
Represents failed operations with error details:
```python
@dataclass(kw_only=True, slots=True)
class FailedResult:
    status: bool = False
    client_message: Any = None  # Error message for client
    ray_id: str
    error_code: str            # RFC-compliant error code
```

**Design Philosophy**:
- No exceptions for business logic failures
- Explicit success/failure handling
- Ray ID for distributed tracing
- Type-safe error propagation

---

### 2. Audit Fields

#### `AuditFields`
Base class for all auditable entities:
```python
@dataclass(kw_only=True, slots=True)
class AuditFields:
    created_at: int      # Unix timestamp
    created_by: str      # User/system ID
    updated_at: int      # Unix timestamp
    updated_by: str      # User/system ID
```

**Usage**: All domain models inherit from `AuditFields` to ensure consistent audit trail.

---

### 3. Domain Models (Storage Layer)

These models map directly to database tables defined in `store/sqllite/oauth.sql`.

#### `OAuthClient`
Represents an OAuth2 client identity:
```python
@dataclass(kw_only=True, slots=True)
class OAuthClient(AuditFields):
    id: str                    # Internal unique ID
    client_identifier: str     # Public OAuth2 client_id
    client_secret: str | None  # Hashed secret (null for public clients)
    is_confidential: bool      # Client type
    redirect_uris: str         # Space-separated URIs
    grant_types: str           # Space-separated grant types
    scopes: str | None         # Space-separated scopes
    is_enabled: bool           # Active status
```

**Storage**: Maps to `oauth_clients` table.

#### `OAuthClientConfig`
Client-specific configuration (1:1 with OAuthClient):
```python
@dataclass(kw_only=True, slots=True)
class OAuthClientConfig(AuditFields):
    client_id: str
    
    # Response types
    response_types: str  # Space-separated (e.g., "code token")
    
    # PKCE & security
    require_pkce: bool
    pkce_methods: str | None  # Space-separated (e.g., "S256 plain")
    
    # Token lifetimes (seconds)
    access_token_ttl: int
    refresh_token_ttl: int | None
    authorization_code_ttl: int
    
    # Token limits (FIFO)
    max_active_access_tokens: int | None  # Null = unlimited
    max_active_refresh_tokens: int | None
    
    # Device flow
    device_code_ttl: int | None
    device_poll_interval: int | None
    
    # Operational metadata
    metadata: str | None  # JSON string
```

**Storage**: Maps to `oauth_client_configs` table (not shown in current schema, but implied).

#### `OAuthUser`
Reference user entity:
```python
@dataclass(kw_only=True, slots=True)
class OAuthUser(AuditFields):
    id: str
    external_id: str  # External identity system ID
    is_active: bool
```

**Storage**: Maps to `oauth_users` table.

#### `AuthorizationCode`
OAuth2 authorization code:
```python
@dataclass(kw_only=True, slots=True)
class AuthorizationCode(AuditFields):
    id: str
    code: str                           # The authorization code
    client_id: str
    user_id: str
    redirect_uri: str
    scopes: Optional[str]
    code_challenge: Optional[str]       # PKCE challenge
    code_challenge_method: Optional[str] # PKCE method (S256, plain)
    expires_at: int                     # Unix timestamp
    consumed_at: Optional[int]          # Unix timestamp when used
```

**Storage**: Maps to `oauth_authorization_codes` table.

#### `AccessToken`
OAuth2 access token:
```python
@dataclass(kw_only=True, slots=True)
class AccessToken(AuditFields):
    id: str
    token: str              # The access token (opaque or JWT)
    client_id: str
    user_id: Optional[str]  # Null for client credentials flow
    scopes: Optional[str]
    expires_at: int         # Unix timestamp
    revoked_at: Optional[int]  # Unix timestamp if revoked
```

**Storage**: Maps to `oauth_access_tokens` table.

#### `RefreshToken`
OAuth2 refresh token:
```python
@dataclass(kw_only=True, slots=True)
class RefreshToken(AuditFields):
    id: str
    token: str              # The refresh token
    client_id: str
    user_id: Optional[str]
    scopes: Optional[str]
    revoked_at: Optional[int]  # Unix timestamp if revoked
```

**Storage**: Maps to `oauth_refresh_tokens` table.

**Note**: Refresh tokens don't have `expires_at` - they're long-lived until revoked.

#### `DeviceCode`
OAuth2 device authorization code:
```python
@dataclass(kw_only=True, slots=True)
class DeviceCode(AuditFields):
    id: str
    device_code: str        # Device polling code
    user_code: str          # User-friendly code
    client_id: str
    user_id: Optional[str]  # Set when user approves
    scopes: Optional[str]
    expires_at: int
    interval: int           # Polling interval in seconds
    state: str              # pending, approved, denied, consumed, expired
```

**Storage**: Maps to `oauth_device_codes` table.

#### `AuditLog`
Append-only audit log:
```python
@dataclass(kw_only=True, slots=True)
class AuditLog(AuditFields):
    id: str
    event_type: str         # e.g., "token.issued", "authorization.granted"
    subject: Optional[str]  # What was acted upon
    client_id: Optional[str]
    user_id: Optional[str]
    metadata: Optional[str] # JSON string with additional context
```

**Storage**: Maps to audit log table (separate from oauth.sql).

---

### 4. Request/Response Objects

These objects are used for API interactions and don't map directly to storage.

#### `RegistrationRequest`
Client registration request:
```python
@dataclass(kw_only=True, slots=True)
class RegistrationRequest:
    # Ownership
    user_id: str
    
    # Client identity
    client_identifier: str
    is_confidential: bool
    
    # OAuth capabilities
    redirect_uris: list[str]
    grant_types: list[str]
    response_types: list[str]
    scopes: list[str]
    
    # PKCE
    require_pkce: bool
    pkce_methods: list[str] | None
    
    # Token lifetimes
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
    metadata: dict[str, str] | None
```

**Usage**: Input to `ClientRegistrar.register_client()`.

#### `Client`
Client registration response (includes plaintext secret):
```python
@dataclass(kw_only=True, slots=True)
class Client:
    # Identity
    id: str                    # Internal ID
    client_identifier: str     # Public identifier
    
    # Ownership
    user_id: str
    
    # Security
    is_confidential: bool
    client_secret: str | None  # PLAINTEXT - only on creation!
    
    # OAuth capabilities (lists, not space-separated)
    redirect_uris: list[str]
    grant_types: list[str]
    response_types: list[str]
    scopes: list[str]
    
    # PKCE
    require_pkce: bool
    pkce_methods: list[str] | None
    
    # Token lifetimes
    access_token_ttl: int
    refresh_token_ttl: int | None
    authorization_code_ttl: int
    
    # Token limits
    max_active_access_tokens: int | None
    max_active_refresh_tokens: int | None
    
    # Device flow
    device_code_ttl: int | None
    device_poll_interval: int | None
    
    # Status
    is_enabled: bool
    
    # Audit
    created_at: int
    created_by: str
```

**Critical**: `client_secret` is **plaintext** and only returned once during registration. Storage models use hashed secrets.

---

## Design Patterns

### 1. Dataclass with Slots
All structures use `@dataclass(kw_only=True, slots=True)`:
- **kw_only=True**: Forces keyword arguments for clarity
- **slots=True**: Reduces memory footprint, prevents dynamic attributes

### 2. Inheritance for Audit Trail
All domain models inherit from `AuditFields` to ensure consistent audit metadata.

### 3. Optional Types for Nullable Fields
Uses `Optional[T]` or `T | None` for fields that can be null, matching database schema.

### 4. Space-Separated Strings for Lists
Storage models use space-separated strings (e.g., `"scope1 scope2"`) for lists, while request/response objects use Python lists for ergonomics.

### 5. Unix Timestamps
All timestamps are `int` (Unix epoch seconds) for simplicity and database compatibility.

## Type Safety

### String vs List Conversion
- **Storage models**: Use space-separated strings (`redirect_uris: str`)
- **Request/Response objects**: Use lists (`redirect_uris: list[str]`)
- **Conversion**: Handled by service layer (e.g., `ClientRegistrar._serialize_list()`)

### Null Handling
- **Confidential clients**: `client_secret` is required
- **Public clients**: `client_secret` is `None`
- **Optional features**: `refresh_token_ttl`, `device_code_ttl`, etc. can be `None`

## Dependencies

### Internal
None - this is the foundation layer.

### External
- **dataclasses**: Python standard library
- **typing**: Python standard library (Optional, Any)

## Implementation Guidelines

### Adding a New Domain Model

1. Define as `@dataclass(kw_only=True, slots=True)`
2. Inherit from `AuditFields` if auditable
3. Use appropriate types (`str`, `int`, `bool`, `Optional[T]`)
4. Add docstring explaining purpose and storage mapping
5. Update corresponding SQL schema in `store/sqllite/oauth.sql`

### Adding a New Result Type

1. Inherit from `Result` base class
2. Set appropriate default for `status`
3. Define specific fields for the result type
4. Document usage in docstring

### Modifying Existing Structures

⚠️ **Breaking Changes**: Modifying existing fields is a breaking change. Follow semantic versioning:
- Adding optional fields: Minor version bump
- Removing fields or changing types: Major version bump

## Related Documentation

- **Storage Layer**: [../store/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/imp.md) - How these models map to database tables
- **Client Registration**: [../oauth2/clients/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/clients/imp.md) - How `RegistrationRequest` and `Client` are used
- **Error Handling**: [../errors/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/errors/imp.md) - How `FailedResult` integrates with error registry

---

**Summary**: The data structures layer provides type-safe, memory-efficient domain models and result types that serve as the foundation for the entire framework. All structures use dataclasses with slots for efficiency and follow consistent patterns for audit trails, null handling, and type safety.
