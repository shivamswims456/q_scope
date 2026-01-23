# OAuth2 Implementation

## Purpose

The `oauth2/` directory contains the core OAuth2 protocol implementation including flow orchestration, client management, secret handling, and validation logic. This component bridges the gap between RFC-compliant protocol logic (via oauthlib, future) and the storage/error layers.

## Architecture Context

```
ASGI Layer (future)
       ↓
OAuth2 Core (oauthlib wrapper, future)
       ↓
┌─────────────────────────────────────────┐
│        OAUTH2 IMPLEMENTATION            │
│  ┌───────────────────────────────────┐  │
│  │ oauth_flows/                      │  │
│  │  - RefreshTokenFlow (in progress) │  │
│  │  - AuthCodeFlow (planned)         │  │
│  │  - ClientCredentialsFlow (planned)│  │
│  │  - DeviceFlow (planned)           │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ clients/                          │  │
│  │  - ClientRegistrar                │  │
│  │  - Client authentication          │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ secrets/                          │  │
│  │  - Secret generation              │  │
│  │  - Secret hashing                 │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ templates/                        │  │
│  │  - OAuth2Authorization (base)     │  │
│  │  - Condition (pattern)            │  │
│  │  - Secret interfaces              │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ helpers/                          │  │
│  │  - ConditionChain executor        │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
       ↓
Storage Layer + Error Registry
```

## Key Components

### 1. OAuth Flows (`oauth_flows/`)
**See**: [oauth_flows/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/oauth_flows/imp.md)

Implements OAuth2 grant type flows:
- **Refresh Token Flow** (in progress): RFC 6749 refresh token grant
- **Authorization Code Flow** (planned): RFC 6749 + RFC 7636 (PKCE)
- **Client Credentials Flow** (planned): RFC 6749 client credentials grant
- **Device Authorization Flow** (planned): RFC 8628 device flow
- **Resource Owner Password Flow** (planned, deprecated): RFC 6749 password grant

Each flow extends `OAuth2Authorization` base class and uses the Condition pattern for validation.

---

### 2. Client Management (`clients/`)
**See**: [clients/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/clients/imp.md)

**`ClientRegistrar`** service handles:
- Client registration (manual, not dynamic per RFC 7591)
- Client authentication
- Secret generation and hashing
- Storage persistence (OAuthClient + OAuthClientConfig)
- Validation logic

**Key Features**:
- Returns plaintext secret only once during registration
- Validates registration requests
- Checks for duplicate client identifiers
- Handles rollback on config insertion failure

---

### 3. Secret Management (`secrets/`)
**See**: [secrets/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/secrets/imp.md)

Provides abstractions for:
- **Secret Generation**: High-entropy, cryptographically secure secrets
- **Secret Hashing**: Secure hashing for storage (e.g., bcrypt, argon2)

Implementations are pluggable via `ClientSecretGenerator` and `ClientSecretHasher` interfaces.

---

### 4. Templates (`templates/`)
**See**: [templates/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/templates/imp.md)

**`base.py`** defines core abstractions:

#### `OAuth2Authorization` (Base Class for Flows)
Template method pattern for OAuth flows:
```python
class OAuth2Authorization(ABC):
    async def execute(self, context, ray_id) -> Mapping[str, Any]:
        self._log_start(context)
        await self._preconditions(context, ray_id)  # Validate
        result = await self._run(context, ray_id)    # Execute
        await self._postconditions(context, result, ray_id)  # Persist
        self._log_success(context, result, ray_id)
        return result
```

#### `Condition` (Validation Pattern)
Base class for composable validation logic:
```python
class Condition(ABC):
    @abstractmethod
    async def validate(self, context, ray_id) -> Result:
        # Return SuccessResult to continue
        # Return FailedResult to stop execution
        ...
```

#### Secret Interfaces
- `ClientSecretGenerator`: Generate raw secrets
- `ClientSecretHasher`: Hash and verify secrets

---

### 5. Helpers (`helpers/`)
**See**: [helpers/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/helpers/imp.md)

**`ConditionChain`**: Executes a sequence of `Condition` objects:
```python
chain = ConditionChain([
    ValidateClientCondition(),
    ValidateTokenCondition(),
    CheckTokenLimitCondition()
])

result = await chain.execute(context=context, ray_id=ray_id)
# Stops at first FailedResult
```

---

## Design Patterns

### 1. Template Method Pattern
`OAuth2Authorization` defines the flow lifecycle:
1. **Preconditions**: Validate input and state
2. **Run**: Execute core flow logic
3. **Postconditions**: Persist state and audit logs

Subclasses implement the abstract methods.

### 2. Condition Pattern
Validation logic is encapsulated in `Condition` objects:
- **Composable**: Chain multiple conditions
- **Reusable**: Share conditions across flows
- **Testable**: Test conditions in isolation
- **Explicit**: Clear separation of validation concerns

### 3. Dependency Injection
Flows and services receive dependencies via constructor:
```python
class RefreshTokenFlow(OAuth2Authorization):
    def __init__(self, storage, clock, config, logger):
        super().__init__(storage=storage, clock=clock, config=config, logger=logger)
```

### 4. Result Pattern
All operations return `SuccessResult` or `FailedResult` instead of raising exceptions for business logic.

## RFC Compliance

### Supported RFCs
- **RFC 6749**: OAuth 2.0 Authorization Framework
- **RFC 7636**: Proof Key for Code Exchange (PKCE)
- **RFC 7009**: Token Revocation
- **RFC 7662**: Token Introspection
- **RFC 8628**: Device Authorization Grant
- **RFC 8414**: Authorization Server Metadata

### Compliance Strategy
- Use **oauthlib** as source of truth for RFC behavior (future)
- Custom logic only wraps/adapts oauthlib
- Explicitly NOT inventing OAuth semantics

## Token Strategy

### Token Types
- **Access Tokens**: Short-lived, opaque (JWT deferred to v1.1)
- **Refresh Tokens**: Long-lived, non-expiring unless revoked

### FIFO Token Limits
Implemented in flows, not storage:
- **Client-level**: Max N refresh tokens (oldest revoked first)
- **Refresh-token-level**: Max M access tokens per refresh token (oldest revoked first)
- **No grace period**: Rotation is strict

## Extension Guidelines

### Adding a New OAuth Flow

1. **Create Flow Class** in `oauth_flows/`:
   ```python
   class NewFlow(OAuth2Authorization):
       async def _preconditions(self, context, ray_id):
           # Validate using Condition pattern
           chain = ConditionChain([...])
           result = await chain.execute(context=context, ray_id=ray_id)
           if not result.status:
               raise OAuthError(...)
       
       async def _run(self, context, ray_id):
           # Core flow logic
           return {...}
       
       async def _postconditions(self, context, result, ray_id):
           # Persist tokens, audit logs
           ...
   ```

2. **Create Flow Diagram** in `ai/flows/new_flow.md`

3. **Write Tests** for E2E flow with SQLite backend

4. **Document** in `oauth_flows/imp.md`

### Adding a New Condition

1. **Implement Condition Interface**:
   ```python
   class ValidateNewThingCondition(Condition):
       async def validate(self, context, ray_id) -> Result:
           if context.get("new_thing") is None:
               return FailedResult(
                   ray_id=ray_id,
                   client_message="new_thing is required",
                   error_code="INVALID_REQUEST"
               )
           return SuccessResult(ray_id=ray_id, client_message=None)
   ```

2. **Use in Flow Preconditions**:
   ```python
   chain = ConditionChain([
       ValidateNewThingCondition(),
       # ... other conditions
   ])
   ```

## Dependencies

### Internal
- **datastrutures**: Domain models, Result types
- **store**: Storage layer for persistence
- **errors**: Error registry for RFC-compliant errors

### External
- **oauthlib** (future): RFC-compliant OAuth2 logic
- **Starlette** (future): ASGI integration

## Testing Strategy

### Unit Tests
- Test individual conditions
- Test secret generation/hashing
- Test client registration logic

### Integration Tests
- Test flows with SQLite backend
- Test condition chains
- Test error handling

### E2E Tests
- Full OAuth2 flows (authorize → token → refresh)
- RFC compliance tests
- Token limit enforcement

## Related Documentation

- **OAuth Flows**: [oauth_flows/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/oauth_flows/imp.md)
- **Client Management**: [clients/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/clients/imp.md)
- **Templates**: [templates/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/templates/imp.md)
- **Helpers**: [helpers/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/helpers/imp.md)
- **Flow Diagrams**: [../../ai/flows/](file:///home/shivam/Desktop/q_scope/q_scope/ai/flows/)
- **Project Intent**: [../../ai/ci.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/ci.md)

---

**Summary**: The OAuth2 implementation layer provides flow orchestration, client management, and validation logic using the Template Method and Condition patterns. It bridges RFC-compliant protocol logic with storage and error handling, ensuring extensibility and testability.
