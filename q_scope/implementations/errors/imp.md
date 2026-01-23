# Error Handling Implementation

## Purpose

The `errors/` directory provides a centralized error handling system with RFC-compliant error responses for the q_scope OAuth2 framework. It defines error categories, error codes, and structured error messages that align with OAuth2 specifications.

## Architecture Context

```
OAuth2 Flows & Services
         ↓
   (validation fails)
         ↓
┌─────────────────────────────────────┐
│       ERROR HANDLING LAYER          │
│  ┌───────────────────────────────┐  │
│  │ Error Categories:             │  │
│  │  - OAuthErrors                │  │
│  │  - DeviceErrors               │  │
│  │  - TokenErrors                │  │
│  │  - RegistrationErrors         │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ Error Registry:               │  │
│  │  - Error code mapping         │  │
│  │  - RFC-compliant messages     │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         ↓
   FailedResult with error_code
```

## Key Files & Logic

### `__init__.py`
Exports all error categories:
```python
from q_scope.implementations.errors.oauth import OAuthErrors
from q_scope.implementations.errors.device import DeviceErrors
from q_scope.implementations.errors.token import TokenErrors
from q_scope.implementations.errors.registration import RegistrationErrors
```

### Error Category Files

#### `oauth.py`
OAuth2 protocol errors (RFC 6749):
```python
class OAuthErrors:
    INVALID_REQUEST = "invalid_request"
    INVALID_CLIENT = "invalid_client"
    INVALID_GRANT = "invalid_grant"
    UNAUTHORIZED_CLIENT = "unauthorized_client"
    UNSUPPORTED_GRANT_TYPE = "unsupported_grant_type"
    INVALID_SCOPE = "invalid_scope"
    # ... other RFC 6749 errors
```

#### `device.py`
Device authorization flow errors (RFC 8628):
```python
class DeviceErrors:
    AUTHORIZATION_PENDING = "authorization_pending"
    SLOW_DOWN = "slow_down"
    ACCESS_DENIED = "access_denied"
    EXPIRED_TOKEN = "expired_token"
```

#### `token.py`
Token-specific errors:
```python
class TokenErrors:
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REVOKED = "token_revoked"
    TOKEN_INVALID = "token_invalid"
```

#### `registration.py`
Client registration errors:
```python
class RegistrationErrors:
    INVALID_REQUEST = "invalid_request"
    DUPLICATE_CLIENT_IDENTIFIER = "duplicate_client_identifier"
    # ... other registration errors
```

### Error Registry (`helpers/registry_to_namespace.py`)
Maps error codes to error messages and HTTP status codes (implementation detail, not shown in current code).

## Design Patterns

### 1. Error Code Constants
All error codes are defined as class constants for type safety and IDE autocomplete:
```python
# Instead of magic strings:
error_code = "invalid_request"  # ❌ Typo-prone

# Use constants:
error_code = OAuthErrors.INVALID_REQUEST  # ✅ Type-safe
```

### 2. Category-Based Organization
Errors are grouped by OAuth2 flow/feature:
- **OAuthErrors**: General OAuth2 protocol errors
- **DeviceErrors**: Device authorization flow specific
- **TokenErrors**: Token lifecycle errors
- **RegistrationErrors**: Client registration errors

### 3. RFC Compliance
Error codes match RFC specifications exactly:
- RFC 6749 (OAuth 2.0): `invalid_request`, `invalid_client`, `invalid_grant`, etc.
- RFC 8628 (Device Flow): `authorization_pending`, `slow_down`, etc.

### 4. Integration with Result Pattern
Errors are returned via `FailedResult`:
```python
return FailedResult(
    ray_id=ray_id,
    client_message="Invalid client credentials",
    error_code=OAuthErrors.INVALID_CLIENT
)
```

## RFC-Compliant Error Responses

### OAuth2 Error Response Format (RFC 6749)
```json
{
  "error": "invalid_request",
  "error_description": "The request is missing a required parameter",
  "error_uri": "https://docs.example.com/errors/invalid_request"
}
```

### Device Flow Error Response (RFC 8628)
```json
{
  "error": "authorization_pending",
  "error_description": "The authorization request is still pending"
}
```

## Error Code Reference

### OAuth2 Errors (RFC 6749)

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `invalid_request` | Missing or invalid parameter | 400 |
| `invalid_client` | Client authentication failed | 401 |
| `invalid_grant` | Authorization grant is invalid | 400 |
| `unauthorized_client` | Client not authorized for grant type | 400 |
| `unsupported_grant_type` | Grant type not supported | 400 |
| `invalid_scope` | Requested scope is invalid | 400 |

### Device Flow Errors (RFC 8628)

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `authorization_pending` | User hasn't authorized yet | 400 |
| `slow_down` | Client polling too frequently | 400 |
| `access_denied` | User denied authorization | 400 |
| `expired_token` | Device code expired | 400 |

### Token Errors

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `token_expired` | Token has expired | 401 |
| `token_revoked` | Token has been revoked | 401 |
| `token_invalid` | Token is malformed or invalid | 401 |

### Registration Errors

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `invalid_request` | Registration request is invalid | 400 |
| `duplicate_client_identifier` | Client identifier already exists | 409 |

## Usage Examples

### In OAuth Flow
```python
from q_scope.implementations.errors import OAuthErrors

class RefreshTokenFlow(OAuth2Authorization):
    async def _preconditions(self, context, ray_id):
        if not context.get("refresh_token"):
            return FailedResult(
                ray_id=ray_id,
                client_message="refresh_token is required",
                error_code=OAuthErrors.INVALID_REQUEST
            )
```

### In Client Registration
```python
from q_scope.implementations.errors import RegistrationErrors

class ClientRegistrar:
    async def register_client(self, request, ray_id):
        if await self._client_exists(request.client_identifier):
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Client '{request.client_identifier}' already exists",
                error_code=RegistrationErrors.DUPLICATE_CLIENT_IDENTIFIER
            )
```

### In Device Flow
```python
from q_scope.implementations.errors import DeviceErrors

class DeviceFlow(OAuth2Authorization):
    async def _check_device_code(self, device_code, ray_id):
        if device_code.state == "pending":
            return FailedResult(
                ray_id=ray_id,
                client_message="Authorization pending",
                error_code=DeviceErrors.AUTHORIZATION_PENDING
            )
```

## Extension Guidelines

### Adding a New Error Category

1. **Create Error Module** in `errors/`:
   ```python
   # errors/new_category.py
   class NewCategoryErrors:
       ERROR_CODE_1 = "error_code_1"
       ERROR_CODE_2 = "error_code_2"
   ```

2. **Export in `__init__.py`**:
   ```python
   from q_scope.implementations.errors.new_category import NewCategoryErrors
   
   __all__ = [
       "OAuthErrors",
       "DeviceErrors",
       "TokenErrors",
       "RegistrationErrors",
       "NewCategoryErrors"  # Add here
   ]
   ```

3. **Document Error Codes** in this file

### Adding a New Error Code

1. **Add to Appropriate Category**:
   ```python
   class OAuthErrors:
       # ... existing errors
       NEW_ERROR = "new_error"  # Add here
   ```

2. **Ensure RFC Compliance**: If the error is defined in an RFC, use the exact error code from the specification.

3. **Document**: Add to error code reference table in this file.

## Security Considerations

### Error Message Sanitization
- **Never leak secrets** in error messages
- **Avoid information disclosure**: Don't reveal whether a user/client exists
- **Generic messages for auth failures**: Use `invalid_client` instead of "client not found" vs "wrong password"

### Error Logging
- **Log detailed errors** internally for debugging
- **Return generic errors** to clients
- **Include ray_id** for tracing

Example:
```python
# Internal log (detailed)
logger.error(f"Client authentication failed: {ray_id}, client_id={client_id}, reason=invalid_secret")

# Client response (generic)
return FailedResult(
    ray_id=ray_id,
    client_message="Client authentication failed",
    error_code=OAuthErrors.INVALID_CLIENT
)
```

## Dependencies

### Internal
- **datastrutures**: `FailedResult` type

### External
None - this is a pure constants/registry module.

## Testing Strategy

### Error Code Tests
- Verify all error codes are RFC-compliant
- Test error code constants are accessible
- Ensure no duplicate error codes

### Integration Tests
- Test error responses in OAuth flows
- Verify HTTP status codes
- Test error message formatting

## Related Documentation

- **Data Structures**: [../datastrutures/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/datastrutures/imp.md) - `FailedResult` type
- **OAuth2 Flows**: [../oauth2/oauth_flows/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/oauth_flows/imp.md) - Error usage in flows
- **RFC 6749**: OAuth 2.0 error codes
- **RFC 8628**: Device flow error codes

---

**Summary**: The error handling layer provides RFC-compliant error codes organized by category (OAuth, Device, Token, Registration). All errors are returned via `FailedResult` objects with consistent error codes, enabling proper error handling and client communication while maintaining security through generic error messages.
