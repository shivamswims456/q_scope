# Client Management Implementation

## Purpose

The `clients/` directory provides client registration and management functionality for the q_scope OAuth2 framework. It handles the complete lifecycle of OAuth2 client registration, including validation, secret generation, and storage persistence.

## Architecture Context

```
Client Registration API (future)
         ↓
┌──────────────────────────────────────┐
│      CLIENT MANAGEMENT LAYER         │
│  ┌────────────────────────────────┐  │
│  │ ClientRegistrar                │  │
│  │  - Validate registration       │  │
│  │  - Generate client ID          │  │
│  │  - Generate & hash secret      │  │
│  │  - Persist to storage          │  │
│  │  - Return Client (with secret) │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
       ↓
Secret Management + Storage Layer
```

## Key Files & Logic

### `__init__.py`
Exports `ClientRegistrar`:
```python
from q_scope.implementations.oauth2.clients.registrar import ClientRegistrar

__all__ = ["ClientRegistrar"]
```

### `registrar.py` (360 lines)
Core client registration service.

## ClientRegistrar Service

### Purpose
Handles manual client registration (RFC 7591 dynamic registration is deferred to v1.1).

### Dependencies
```python
def __init__(
    self,
    *,
    client_store: OAuthClientStore,
    config_store: OAuthClientConfigStore,
    secret_generator: ClientSecretGenerator,
    secret_hasher: ClientSecretHasher,
):
    self._client_store = client_store
    self._config_store = config_store
    self._secret_generator = secret_generator
    self._secret_hasher = secret_hasher
```

**Dependency Injection**: All dependencies are injected, enabling testability and flexibility.

---

## Core Methods

### 1. `register_client()`

**Signature**:
```python
async def register_client(
    self,
    *,
    request: RegistrationRequest,
    ray_id: str
) -> Union[SuccessResult, FailedResult]:
```

**Workflow**:
1. **Validate Request**: Check required fields and constraints
2. **Check Duplicate**: Ensure `client_identifier` is unique
3. **Generate Client ID**: Create internal unique ID (UUID4)
4. **Generate Secret**: For confidential clients only
5. **Hash Secret**: Store hashed version
6. **Create OAuthClient**: Identity record
7. **Create OAuthClientConfig**: Configuration record
8. **Persist to Storage**: Insert both records (with rollback on failure)
9. **Return Client**: With plaintext secret (one-time only)

**Example**:
```python
request = RegistrationRequest(
    user_id="user123",
    client_identifier="my-app",
    is_confidential=True,
    redirect_uris=["https://app.example.com/callback"],
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    scopes=["read", "write"],
    require_pkce=True,
    pkce_methods=["S256"],
    access_token_ttl=3600,
    refresh_token_ttl=2592000,
    authorization_code_ttl=600,
    max_active_access_tokens=5,
    max_active_refresh_tokens=3,
    device_code_ttl=None,
    device_poll_interval=None,
    metadata={"app_name": "My App"}
)

result = await registrar.register_client(request=request, ray_id="ray123")

if result.status:
    client = result.client_message
    print(f"Client ID: {client.id}")
    print(f"Client Secret: {client.client_secret}")  # PLAINTEXT - save this!
else:
    print(f"Error: {result.error_code} - {result.client_message}")
```

**Critical**: The `client_secret` is returned in **plaintext** only once. It must be saved by the caller immediately.

---

### 2. `get_client_by_id()`

**Signature**:
```python
async def get_client_by_id(
    self,
    *,
    client_id: str,
    ray_id: str
) -> Union[SuccessResult, FailedResult]:
```

**Purpose**: Retrieve a client by internal ID.

**Returns**: `SuccessResult` with `OAuthClient` or `FailedResult` with `NOT_FOUND` error.

---

### 3. `get_client_by_identifier()`

**Signature**:
```python
async def get_client_by_identifier(
    self,
    *,
    client_identifier: str,
    ray_id: str
) -> Union[SuccessResult, FailedResult]:
```

**Purpose**: Retrieve a client by public identifier (OAuth2 `client_id`).

**Returns**: `SuccessResult` with `OAuthClient` or `FailedResult` with `NOT_FOUND` error.

---

## Private Methods

### `_validate_request()`
Validates `RegistrationRequest` for:
- **user_id**: Required, non-empty
- **client_identifier**: Required, non-empty
- **redirect_uris**: At least one required
- **grant_types**: At least one required
- **access_token_ttl**: Must be positive
- **authorization_code_ttl**: Must be positive

**Returns**: `SuccessResult` if valid, `FailedResult` with `INVALID_REQUEST` error otherwise.

---

### `_check_duplicate_identifier()`
Checks if `client_identifier` already exists in storage.

**Returns**:
- `SuccessResult`: Identifier is available
- `FailedResult` with `DUPLICATE_CLIENT_IDENTIFIER`: Identifier already exists
- `FailedResult` with other error: Storage failure

---

### `_generate_client_id()`
Generates a unique internal client ID using UUID4.

**Future**: Could be replaced with distributed ID generator (e.g., Sonyflake).

---

### `_serialize_list()`
Converts Python lists to space-separated strings for storage:
```python
["read", "write"] → "read write"
```

---

## Data Flow

### Registration Flow

```
RegistrationRequest
       ↓
1. Validate Request
       ↓
2. Check Duplicate Identifier
       ↓
3. Generate Client ID (UUID4)
       ↓
4. Generate Secret (if confidential)
       ↓
5. Hash Secret
       ↓
6. Create OAuthClient (hashed secret)
       ↓
7. Create OAuthClientConfig
       ↓
8. Insert OAuthClient to storage
       ↓
9. Insert OAuthClientConfig to storage
   (rollback OAuthClient if fails)
       ↓
10. Return Client (plaintext secret)
```

### Rollback Handling

If `OAuthClientConfig` insertion fails:
```python
# Rollback: delete the client we just inserted
await self._client_store.delete_by_id(client_id, ray_id)
return config_insert_result  # Return the FailedResult
```

**Note**: This is manual rollback. Future implementations may use database transactions.

---

## Design Patterns

### 1. Service Layer Pattern
`ClientRegistrar` is a service that orchestrates multiple operations:
- Validation
- Secret generation
- Storage persistence
- Error handling

### 2. Dependency Injection
All dependencies are injected via constructor, enabling:
- Testability (mock dependencies)
- Flexibility (swap implementations)
- Clear contracts

### 3. Result Pattern
All methods return `SuccessResult` or `FailedResult` instead of raising exceptions.

### 4. Separation of Concerns
- **ClientRegistrar**: Orchestration and business logic
- **ClientSecretGenerator**: Secret generation
- **ClientSecretHasher**: Secret hashing
- **OAuthClientStore**: Storage persistence

---

## Security Considerations

### Secret Handling
1. **Generation**: High-entropy, cryptographically secure (via `ClientSecretGenerator`)
2. **Hashing**: Secure hashing algorithm (e.g., bcrypt, argon2) via `ClientSecretHasher`
3. **Storage**: Only hashed secrets are stored
4. **Transmission**: Plaintext secret returned only once during registration
5. **Logging**: Never log plaintext secrets

### Client Identifier Uniqueness
Prevents duplicate client identifiers to avoid confusion and potential security issues.

### Validation
Strict validation of registration requests prevents invalid or malicious client configurations.

---

## Extension Guidelines

### Adding Custom Validation

1. **Extend `_validate_request()`**:
   ```python
   def _validate_request(self, request, ray_id):
       # Call parent validation
       result = super()._validate_request(request, ray_id)
       if not result.status:
           return result
       
       # Add custom validation
       if request.client_identifier.startswith("admin-"):
           return FailedResult(
               ray_id=ray_id,
               client_message="Client identifier cannot start with 'admin-'",
               error_code="INVALID_REQUEST"
           )
       
       return SuccessResult(ray_id=ray_id, client_message="Validation successful")
   ```

### Using Custom Secret Generator

```python
from q_scope.implementations.oauth2.templates.base import ClientSecretGenerator

class CustomSecretGenerator(ClientSecretGenerator):
    def generate_secret(self, *, user_id: str) -> str:
        # Custom secret generation logic
        return secrets.token_urlsafe(32)

registrar = ClientRegistrar(
    client_store=client_store,
    config_store=config_store,
    secret_generator=CustomSecretGenerator(),  # Custom generator
    secret_hasher=secret_hasher
)
```

---

## Dependencies

### Internal
- **datastrutures**: `OAuthClient`, `OAuthClientConfig`, `RegistrationRequest`, `Client`, `SuccessResult`, `FailedResult`
- **store**: `OAuthClientStore`, `OAuthClientConfigStore`
- **templates/base**: `ClientSecretGenerator`, `ClientSecretHasher`

### External
- **uuid**: Client ID generation
- **time**: Timestamps
- **json**: Metadata serialization

---

## Testing Strategy

### Unit Tests
- Test validation logic
- Test duplicate identifier checking
- Test client ID generation
- Test list serialization

### Integration Tests
- Test full registration flow with real storage
- Test rollback on config insertion failure
- Test secret generation and hashing integration

### Security Tests
- Verify secrets are never logged
- Verify only hashed secrets are stored
- Verify plaintext secret is returned only once

---

## Related Documentation

- **OAuth2 Layer**: [../imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/imp.md)
- **Secret Management**: [../secrets/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/secrets/imp.md)
- **Templates**: [../templates/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/templates/imp.md)
- **Data Structures**: [../../datastrutures/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/datastrutures/imp.md)
- **Storage Layer**: [../../store/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/imp.md)

---

**Summary**: The client management layer provides a `ClientRegistrar` service for manual OAuth2 client registration. It handles validation, secret generation/hashing, storage persistence, and returns the plaintext secret only once during registration. The service uses dependency injection for flexibility and the Result pattern for error handling.
