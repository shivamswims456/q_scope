# Implementations Layer

## Purpose

The `implementations/` directory contains the core implementation layer of the q_scope OAuth2 framework. This layer sits between the protocol logic (future ASGI/oauthlib integration) and provides concrete, reusable components for OAuth2 flows, storage, error handling, and data structures.

## Architecture Context

```
ASGI Layer (future)
       ↓
OAuth2 Core (future)
       ↓
┌──────────────────────────────────────┐
│    IMPLEMENTATIONS LAYER (current)   │
│  ┌────────────────────────────────┐  │
│  │ oauth2/                        │  │
│  │  - OAuth flows                 │  │
│  │  - Client registration         │  │
│  │  - Secret management           │  │
│  │  - Templates & helpers         │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ store/                         │  │
│  │  - Abstract storage contracts  │  │
│  │  - SQLite/Turso implementation │  │
│  │  - PyPika query generation     │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ errors/                        │  │
│  │  - Error registry              │  │
│  │  - RFC-compliant errors        │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ datastrutures/                 │  │
│  │  - Domain models               │  │
│  │  - Result types                │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

## Component Categories

### 1. OAuth2 (`oauth2/`)
**Purpose**: OAuth2 protocol implementation including flows, client management, and security.

**Key Responsibilities**:
- OAuth2 flow orchestration (Authorization Code, Refresh Token, etc.)
- Client registration and authentication
- Secret generation and hashing
- Condition-based validation
- Template abstractions for extensibility

**See**: [oauth2/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/imp.md)

---

### 2. Storage (`store/`)
**Purpose**: Storage abstraction layer enabling pluggable database backends.

**Key Responsibilities**:
- Abstract storage contracts (BaseTable, ClientTable, etc.)
- SQLite/Turso reference implementation
- PyPika-based query generation
- Schema management (oauth.sql, logs.sql)
- Async database operations

**Design Philosophy**:
- Storage is transparent and inspectable
- No ORM - raw SQL with PyPika
- Schema is public API
- Works cleanly with Turso/libSQL

**See**: [store/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/imp.md)

---

### 3. Errors (`errors/`)
**Purpose**: Centralized error handling with RFC-compliant error responses.

**Key Responsibilities**:
- Error registry for OAuth2, Device, Token, and Registration errors
- RFC-compliant error codes and messages
- Error namespace management
- Structured error responses

**See**: [errors/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/errors/imp.md)

---

### 4. Data Structures (`datastrutures/`)
**Purpose**: Domain models and type definitions for the entire framework.

**Key Responsibilities**:
- Domain models (OAuthClient, AccessToken, RefreshToken, etc.)
- Result types (SuccessResult, FailedResult)
- Request/Response objects (RegistrationRequest, Client)
- Audit fields and shared structures

**See**: [datastrutures/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/datastrutures/imp.md)

---

## Component Interaction

### Flow Execution Example (Refresh Token Flow)

```
1. OAuth Flow (oauth2/oauth_flows/)
   ↓ validates using Conditions
   ↓ queries storage
2. Storage Layer (store/)
   ↓ executes PyPika queries
   ↓ returns domain models
3. Data Structures (datastrutures/)
   ↓ RefreshToken, AccessToken models
   ↓ wrapped in Result types
4. Error Handling (errors/)
   ↓ if validation fails
   ↓ returns RFC-compliant error
```

### Client Registration Example

```
1. ClientRegistrar (oauth2/clients/)
   ↓ validates RegistrationRequest
   ↓ generates secret
2. Secret Management (oauth2/secrets/)
   ↓ generates + hashes secret
   ↓ returns plaintext (one-time)
3. Storage Layer (store/)
   ↓ persists OAuthClient + OAuthClientConfig
   ↓ returns SuccessResult
4. Result Types (datastrutures/)
   ↓ wraps Client object
   ↓ includes plaintext secret
```

## Design Patterns

### 1. Result Pattern
All operations return typed results instead of raising exceptions for business logic:
- `SuccessResult`: Contains data, `status=True`
- `FailedResult`: Contains error code/message, `status=False`

### 2. Condition Pattern
Validation logic is encapsulated in `Condition` objects:
- Composable and chainable via `ConditionChain`
- Returns `Result` objects
- Enables clean separation of concerns

### 3. Template Method Pattern
OAuth flows extend `OAuth2Authorization` base class:
- `_preconditions()`: Validate input
- `_run()`: Execute core logic
- `_postconditions()`: Persist state

### 4. Abstract Factory Pattern
Storage layer uses abstract base classes:
- `BaseTable[T]`: Generic CRUD
- Specialized tables: `ClientTable`, `AccessTokenTable`, etc.
- Concrete implementations: SQLite, future (Postgres, Redis, etc.)

## Extension Guidelines

### Adding a New OAuth Flow

1. Create flow class in `oauth2/oauth_flows/`
2. Extend `OAuth2Authorization` base class
3. Implement preconditions using `Condition` pattern
4. Implement core logic in `_run()`
5. Implement postconditions for persistence
6. Add flow diagram to `ai/flows/`
7. Create `imp.md` documentation

### Adding a New Storage Backend

1. Implement abstract interfaces from `store/templates/`
2. Implement all required table classes
3. Handle async operations appropriately
4. Write contract tests
5. Document in `store/imp.md`

### Adding New Error Types

1. Define errors in appropriate module (`errors/oauth.py`, etc.)
2. Register in error registry
3. Ensure RFC compliance
4. Document error codes

## Dependencies

### Internal Dependencies
- `datastrutures/`: Used by all components for domain models
- `errors/`: Used by all components for error handling
- `store/templates/`: Used by OAuth flows for storage operations

### External Dependencies
- **oauthlib** (future): RFC-compliant OAuth2 protocol logic
- **PyPika**: SQL query generation
- **aiosqlite**: Async SQLite operations
- **Starlette** (future): ASGI application layer

## Testing Strategy

Each component has its own testing approach:
- **OAuth flows**: E2E flow tests with SQLite
- **Storage**: Contract tests + implementation tests
- **Errors**: Error response format tests
- **Data structures**: Type validation tests

## Related Documentation

- **Root Overview**: [../imp.md](file:///home/shivam/Desktop/q_scope/q_scope/imp.md)
- **Project Intent**: [../ai/ci.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/ci.md)
- **Chat Histories**: [../ai/chats/](file:///home/shivam/Desktop/q_scope/q_scope/ai/chats/)

---

**Summary**: The implementations layer provides concrete, reusable components for OAuth2 functionality, storage abstraction, error handling, and domain modeling. All components follow consistent design patterns (Result, Condition, Template Method) and are designed for extensibility.
