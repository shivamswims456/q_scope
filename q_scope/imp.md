# q_scope Framework Implementation

## Purpose

**q_scope** is a production-grade, modular OAuth2 authorization server framework for Python. It provides RFC-compliant OAuth2 functionality through a clean, extensible architecture that separates protocol logic from storage and presentation concerns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ASGI Application Layer                    │
│                   (Starlette-based, future)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   OAuth2 Core Logic                          │
│              (oauthlib wrapper, future)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Implementation Layer                        │
│  ┌──────────┬──────────┬──────────┬──────────────────────┐  │
│  │ OAuth2   │ Storage  │ Errors   │ Data Structures      │  │
│  │ Flows    │ Layer    │ Registry │ (Domain Models)      │  │
│  └──────────┴──────────┴──────────┴──────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. RFC Fidelity First
All OAuth2 semantics follow relevant RFCs (6749, 7636, 7009, 7662, 8628, 8414). Custom logic defers to RFC-defined behavior.

### 2. Storage Agnosticism
The framework provides abstract storage contracts. SQLite/Turso implementation serves as:
- Reference implementation
- Testing backend
- Documentation aid

### 3. ASGI Native
Framework is ASGI-first with Starlette as the canonical runtime, ensuring interoperability with FastAPI, Quart, and other ASGI frameworks.

### 4. Schema-First Design
SQL schema is treated as **public API**, not an internal detail. No ORM - uses PyPika for query generation.

### 5. Explicit Extensibility
All extension points are documented, contract-driven, and stable across minor versions.

## Directory Structure

```
q_scope/
├── implementations/          # Core implementation layer
│   ├── oauth2/              # OAuth2 flows, clients, secrets
│   ├── store/               # Storage abstraction & SQLite impl
│   ├── errors/              # Error registry & RFC-compliant errors
│   └── datastrutures/       # Domain models & result types
├── ai/                      # Project documentation & context
│   ├── chats/              # Agent conversation history
│   ├── flows/              # Visual flow diagrams
│   └── ci.md               # Project intent & architecture spec
└── imp.md                  # This file
```

## Supported OAuth2 Flows (v1.0)

| Grant Type | Status | RFC |
|------------|--------|-----|
| Authorization Code + PKCE | Planned | RFC 6749, 7636 |
| Client Credentials | Planned | RFC 6749 |
| Refresh Token | In Progress | RFC 6749 |
| Device Authorization | Planned | RFC 8628 |
| Resource Owner Password | Planned (deprecated) | RFC 6749 |

**Explicitly Excluded**: Implicit Grant

## Key Design Patterns

### Condition Pattern
Flows use a `Condition` abstraction for validation logic:
- Conditions are composable and chainable
- Return `Result` objects (SuccessResult/FailedResult)
- Enable clean separation of validation concerns

### Unit of Work Pattern
OAuth flows implement a lifecycle:
1. **Preconditions**: Validate input and state
2. **Run**: Execute core flow logic
3. **Postconditions**: Persist state and audit logs

### Result Pattern
All operations return typed results:
- `SuccessResult`: Operation succeeded, contains data
- `FailedResult`: Operation failed, contains error code and message
- No exceptions for business logic failures

## Token Model

### Token Types
- **Access Tokens**: Short-lived, opaque (JWT deferred to v1.1)
- **Refresh Tokens**: Long-lived, non-expiring unless revoked

### FIFO Token Limits
- Client-level: Max N refresh tokens (oldest revoked first)
- Refresh-token-level: Max M access tokens per refresh token (oldest revoked first)
- No grace period - rotation is strict

## Configuration Model

Configuration is explicit and immutable at runtime:
- Enabled grant types
- Token lifetimes (TTL)
- Token limits (max active tokens)
- Logging behavior
- Flow-specific parameters (PKCE, device flow)

## Testing Philosophy

SQLite enables:
- Full OAuth2 E2E flows
- RFC-level behavior testing
- Storage contract tests
- Deterministic CI runs

Anything passing SQLite tests is expected to work on Turso.

## Extension Points

### Storage Backends
Implement abstract base classes in `implementations/store/templates/`:
- `BaseTable[T]`: Generic CRUD interface
- `ClientTable`: Client-specific operations
- `AuthorizationCodeTable`, `AccessTokenTable`, `RefreshTokenTable`, `DeviceCodeTable`
- `AuditLogTable`: Append-only audit log

### OAuth Flows
Extend `OAuth2Authorization` base class:
- Implement `_preconditions()`, `_run()`, `_postconditions()`
- Use `Condition` pattern for validation
- Return typed `Result` objects

### Secret Management
Implement `ClientSecretGenerator` and `ClientSecretHasher` interfaces for custom secret generation and hashing strategies.

## Explicit Non-Goals (v1.0)

- ❌ OIDC (OpenID Connect)
- ❌ Admin UI
- ❌ Client management UI
- ❌ ORM-based models
- ❌ OAuth1
- ❌ Framework-specific plugins

## Related Documentation

- **Project Intent**: [ai/ci.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/ci.md) - Comprehensive architecture specification
- **Chat Histories**: [ai/chats/](file:///home/shivam/Desktop/q_scope/q_scope/ai/chats/) - Design discussions with previous agents
- **Flow Diagrams**: [ai/flows/](file:///home/shivam/Desktop/q_scope/q_scope/ai/flows/) - Visual representations of OAuth2 flows
- **Implementation Details**: [implementations/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/imp.md)

## Quick Start (Future)

```python
from q_scope import OAuth2Server
from q_scope.implementations.store.sqllite import SQLiteStorage

# Initialize storage
storage = SQLiteStorage(database_url="sqlite:///oauth2.db")

# Create OAuth2 server
oauth2 = OAuth2Server(
    storage=storage,
    token_expires_in=3600,
    supported_grants=['authorization_code', 'refresh_token']
)

# Integrate with ASGI framework (future)
# app.mount("/oauth", oauth2.asgi_app)
```

## Versioning & Compatibility

- **Semantic Versioning** enforced
- **Storage contracts** stable within major version
- **Schema changes** require migration guidance

---

**Summary**: q_scope is a protocol-first, storage-agnostic, ASGI-native, UI-neutral OAuth2 framework designed to be embedded, not operated standalone.
