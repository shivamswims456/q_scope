# OAuth Client Registration Service

## Overview

The `ClientRegistrar` service provides a production-ready implementation for registering OAuth 2.0 clients that will be used across different OAuth flows (Authorization Code, Client Credentials, Refresh Token, Device Authorization, etc.).

## Architecture

### Components

```
┌─────────────────────────┐
│  ClientRegistrar        │
│  (Service Layer)        │
└───────────┬─────────────┘
            │
            ├──► OAuthClientStore (Storage Layer)
            ├──► ClientSecretGenerator (Security)
            └──► ClientSecretHasher (Security)
```

### Key Classes

1. **`ClientRegistrar`** - Main service for client registration
   - Location: `q_scope/implementations/oauth2/clients/registrar.py`
   
2. **`OAuthClientStore`** - Database storage abstraction
   - Location: `q_scope/implementations/store/sqllite/pypika_imp/stores.py`
   
3. **`DefaultClientSecretGenerator`** - Cryptographically secure secret generation
   - Location: `q_scope/implementations/oauth2/secrets/__init__.py`
   
4. **`Argon2ClientSecretHasher`** - Argon2-based secret hashing
   - Location: `q_scope/implementations/oauth2/secrets/__init__.py`

## Features

### ✅ Secure Registration Flow

1. **Request Validation**
   - Required field validation
   - TTL value validation
   - Redirect URI validation
   - Grant type validation

2. **Duplicate Prevention**
   - Checks for existing client identifiers
   - Returns `DUPLICATE_CLIENT_IDENTIFIER` error on conflicts

3. **ID Generation**
   - UUID4-based client ID generation
   - Extensible to distributed ID generators (Sonyflake, etc.)

4. **Secret Management**
   - Generates high-entropy secrets for confidential clients
   - Uses Argon2id for secure password hashing
   - Contextualizes secrets with user_id and client_id to prevent transplant attacks
   - Returns plaintext secret **only once** during registration

5. **Result Wrapping**
   - All operations return `SuccessResult` or `FailedResult`
   - Consistent error handling across the application
   - Proper error codes for client handling

### 🔐 Security Features

#### Secret Generation
- **32 bytes (256 bits) of entropy** by default
- URL-safe Base64 encoding
- Entropy mixing with user_id (XOR with SHA256 hash)
- Uses Python's `secrets` module for cryptographic randomness

#### Secret Hashing
- **Argon2id** algorithm (memory-hard, resistant to GPU attacks)
- Configurable parameters:
  - Time cost: 3 iterations
  - Memory cost: 64 MB
  - Parallelism: 1 thread
  - Hash length: 32 bytes
  - Salt length: 16 bytes
- Contextual hashing prevents cross-client secret reuse

## Usage

### Basic Setup

```python
from q_scope.implementations.oauth2.clients import (
    ClientRegistrar,
    OAuthClientStore,
    DefaultClientSecretGenerator,
    Argon2ClientSecretHasher
)

# Initialize dependencies
client_store = OAuthClientStore(db_path="/path/to/database.db")
secret_generator = DefaultClientSecretGenerator(byte_length=32)
secret_hasher = Argon2ClientSecretHasher()

# Create registrar
registrar = ClientRegistrar(
    client_store=client_store,
    secret_generator=secret_generator,
    secret_hasher=secret_hasher
)
```

### Register a Confidential Client (Web Application)

```python
from q_scope.implementations.datastrutures import RegistrationRequest

request = RegistrationRequest(
    user_id="user_123",
    client_identifier="my-web-app",
    is_confidential=True,
    redirect_uris=["https://myapp.com/callback"],
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

result = await registrar.register_client(
    request=request,
    ray_id="request_id_123"
)

if result.status:
    client = result.client_message
    print(f"Client ID: {client.id}")
    print(f"Client Secret: {client.client_secret}")  # ⚠️ Save this securely!
else:
    print(f"Error: {result.client_message}")
    print(f"Code: {result.error_code}")
```

### Register a Public Client (Mobile/SPA)

```python
request = RegistrationRequest(
    user_id="user_456",
    client_identifier="my-mobile-app",
    is_confidential=False,  # No secret for public clients
    redirect_uris=["myapp://oauth/callback"],
    grant_types=["authorization_code"],
    response_types=["code"],
    scopes=["read"],
    require_pkce=True,  # PKCE mandatory for public clients
    pkce_methods=["S256"],
    access_token_ttl=1800,
    refresh_token_ttl=None,
    authorization_code_ttl=300,
    max_active_access_tokens=10,
    max_active_refresh_tokens=None,
    device_code_ttl=None,
    device_poll_interval=None,
    metadata={"platform": "iOS"}
)

result = await registrar.register_client(
    request=request,
    ray_id="request_id_456"
)
```

### Retrieve Clients

```python
# By client identifier
result = await registrar.get_client_by_identifier(
    client_identifier="my-web-app",
    ray_id="request_id_789"
)

# By internal client ID
result = await registrar.get_client_by_id(
    client_id="550e8400-e29b-41d4-a716-446655440000",
    ray_id="request_id_790"
)
```

## Client Types

### Confidential Clients
- **Use Cases**: Server-side web applications, backend services
- **Has Secret**: Yes (generated and hashed)
- **PKCE**: Optional but recommended
- **Grant Types**: Authorization Code, Client Credentials, Refresh Token
- **Storage**: Secret hash stored in database

### Public Clients
- **Use Cases**: Mobile apps, SPAs, native applications
- **Has Secret**: No
- **PKCE**: **Mandatory** (security requirement)
- **Grant Types**: Authorization Code (with PKCE)
- **Storage**: No secret stored

## Database Schema

The `OAuthClient` record stored in the database contains:

```python
OAuthClient(
    id: str,                    # Unique client ID (UUID)
    client_identifier: str,     # Public identifier
    client_secret: str | None,  # Hashed secret (null for public clients)
    is_confidential: bool,      # Client type
    redirect_uris: str,         # Space-separated URIs
    grant_types: str,           # Space-separated grant types
    scopes: str | None,         # Space-separated scopes
    is_enabled: bool,           # Active status
    created_at: int,            # Unix timestamp
    created_by: str,            # User ID
    updated_at: int,            # Unix timestamp
    updated_by: str             # User ID
)
```

## Error Handling

### Error Codes

- `INVALID_REQUEST` - Missing or invalid required fields
- `DUPLICATE_CLIENT_IDENTIFIER` - Client identifier already exists
- `INSERT_FAILED` - Database insertion failed
- `NOT_FOUND` - Client not found during retrieval
- `FETCH_FAILED` - Database query failed

### Example Error Handling

```python
result = await registrar.register_client(request=request, ray_id=ray_id)

if not result.status:
    if result.error_code == "DUPLICATE_CLIENT_IDENTIFIER":
        # Handle duplicate
        print("Client already exists, choose a different identifier")
    elif result.error_code == "INVALID_REQUEST":
        # Handle validation error
        print(f"Validation failed: {result.client_message}")
    else:
        # Handle other errors
        print(f"Unexpected error: {result.error_code}")
```

## Integration with OAuth Flows

The registered clients are used by various OAuth 2.0 flows:

1. **Authorization Code Flow** - Web applications, mobile apps
2. **Client Credentials Flow** - Machine-to-machine authentication
3. **Refresh Token Flow** - Token renewal
4. **Device Authorization Flow** - Smart TVs, IoT devices
5. **Resource Owner Password Flow** - Legacy applications (deprecated)

## Best Practices

### 1. Secret Handling
- **Never log plaintext secrets**
- Store the secret securely (environment variables, secrets manager)
- The plaintext secret is returned **only once** during registration
- Use HTTPS for all redirect URIs

### 2. PKCE Configuration
- **Always enable PKCE** for public clients
- **Recommend PKCE** for confidential clients
- Use `S256` method (SHA-256) over `plain`

### 3. Token TTLs
- **Access tokens**: Short-lived (15-60 minutes)
- **Refresh tokens**: Long-lived (days/months) or use rotation
- **Authorization codes**: Very short (5-10 minutes)
- **Device codes**: Moderate (10-15 minutes)

### 4. Redirect URI Validation
- Use exact matching (no wildcards)
- Require HTTPS in production
- Validate all redirect URIs during registration

### 5. Scope Management
- Define scopes based on API resources
- Use space-separated format
- Validate requested scopes against registered scopes

## Testing

See `examples/client_registration_example.py` for comprehensive examples including:
- Confidential client registration
- Public client registration
- Duplicate detection
- Client retrieval

## Future Enhancements

1. **Dynamic Client Registration (RFC 7591)**
   - Public API for client registration
   - Client metadata updates
   - Client deletion

2. **Client Authentication Methods**
   - JWT-based client authentication
   - mTLS client authentication
   - Private key JWT

3. **Advanced ID Generation**
   - Sonyflake integration
   - Distributed ID generation
   - Custom ID formats

4. **Client Management**
   - Client rotation
   - Secret rotation
   - Client status updates (enable/disable)

## References

- [RFC 6749 - OAuth 2.0 Framework](https://datatracker.ietf.org/doc/html/rfc6749)
- [RFC 7636 - PKCE](https://datatracker.ietf.org/doc/html/rfc7636)
- [RFC 7591 - Dynamic Client Registration](https://datatracker.ietf.org/doc/html/rfc7591)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
