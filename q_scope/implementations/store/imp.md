# Storage Layer Implementation

## Purpose

The `store/` directory provides a storage abstraction layer that enables pluggable database backends for the q_scope OAuth2 framework. It defines abstract contracts for data persistence and provides a SQLite/Turso reference implementation using PyPika for query generation.

## Architecture Context

```
OAuth2 Flows & Services
         ↓
┌────────────────────────────────────┐
│      STORAGE ABSTRACTION LAYER     │
│  ┌──────────────────────────────┐  │
│  │  templates/                  │  │
│  │  - BaseTable[T]              │  │
│  │  - ClientTable               │  │
│  │  - AccessTokenTable          │  │
│  │  - RefreshTokenTable         │  │
│  │  - AuthorizationCodeTable    │  │
│  │  - DeviceCodeTable           │  │
│  │  - AuditLogTable             │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │  sqllite/                    │  │
│  │  - oauth.sql (schema)        │  │
│  │  - logs.sql (schema)         │  │
│  │  - pypika_imp/ (impl)        │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
         ↓
   Database (SQLite/Turso)
```

## Design Philosophy

### 1. Storage Agnosticism
The framework MUST NOT assume:
- Any specific database
- Any ORM
- Any migration system

Storage is accessed exclusively through abstract contracts defined in `templates/`.

### 2. Schema as Public API
The SQL schema (`oauth.sql`, `logs.sql`) is treated as **public API**, not an internal detail. Changes to schema require migration guidance and follow semantic versioning.

### 3. No ORM
- Uses **PyPika** for SQL query generation
- Raw SQL execution via **aiosqlite**
- Transparent and inspectable queries
- No hidden ORM behavior affecting OAuth semantics

### 4. SQLite/Turso as Reference
The SQLite implementation serves as:
- **Reference implementation** for behavior
- **Testing backend** for E2E tests
- **Documentation aid** for implementors

## Directory Structure

```
store/
├── templates/              # Abstract storage contracts
│   └── __init__.py        # BaseTable, ClientTable, etc.
├── sqllite/               # SQLite/Turso implementation
│   ├── oauth.sql          # OAuth schema
│   ├── logs.sql           # Audit log schema
│   └── pypika_imp/        # PyPika-based implementation
│       ├── __init__.py    # Table definitions
│       └── stores.py      # Store implementations
└── imp.md                 # This file
```

## Key Components

### 1. Abstract Storage Contracts (`templates/`)

**See**: [templates/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/templates/imp.md)

Defines abstract base classes for all storage operations:

- **`BaseTable[T]`**: Generic CRUD interface
  - `insert(row: T, ray_id: str) -> Result`
  - `get_by_id(id: str, ray_id: str) -> Result`
  - `update(row: T, ray_id: str) -> Result`
  - `delete_by_id(id: str, ray_id: str) -> Result`

- **Specialized Tables**: Extend `BaseTable` with domain-specific methods
  - `ClientTable`: `get_by_client_identifier()`
  - `AuthorizationCodeTable`: `get_by_code()`, `delete_by_code()`
  - `AccessTokenTable`: `get_by_token()`, `delete_by_token()`
  - `RefreshTokenTable`: `get_by_token()`
  - `DeviceCodeTable`: `get_by_device_code()`, `get_by_user_code()`
  - `AuditLogTable`: Append-only (no update/delete)

### 2. SQLite/Turso Implementation (`sqllite/`)

**See**: [sqllite/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/sqllite/imp.md)

#### Schema Files

**`oauth.sql`** (163 lines):
- `oauth_clients`: Client identity and capabilities
- `oauth_users`: Reference user table
- `oauth_authorization_codes`: Authorization codes with PKCE
- `oauth_access_tokens`: Access tokens with expiry
- `oauth_refresh_tokens`: Long-lived refresh tokens
- `oauth_device_codes`: Device authorization flow

**`logs.sql`**:
- Audit log schema (append-only)

#### PyPika Implementation

**`pypika_imp/stores.py`** (549 lines):
- `OAuthClientStore`: Implements `ClientTable`
- `OAuthClientConfigStore`: Client configuration CRUD
- Uses PyPika `Query` builder for type-safe SQL generation
- Wraps all results in `SuccessResult`/`FailedResult`
- Async operations via `aiosqlite`

## Design Patterns

### 1. Generic Base Table
Uses Python generics for type safety:
```python
class BaseTable(Generic[T], ABC):
    async def insert(self, row: T, ray_id: str) -> None: ...
    async def get_by_id(self, id: str, ray_id: str) -> Optional[T]: ...
```

### 2. Result Wrapping
All storage operations return `Result` types:
- **Success**: `SuccessResult(ray_id=..., client_message=<domain_model>)`
- **Failure**: `FailedResult(ray_id=..., client_message=..., error_code=...)`

### 3. PyPika Query Builder
```python
query = Query.from_(oauth_clients).select(
    "id", "client_identifier", ...
).where(oauth_clients.id == Parameter(":id"))

async with aiosqlite.connect(self.db_path) as db:
    await db.execute(str(query), {"id": id})
```

### 4. Async Context Managers
All database operations use async context managers for proper resource cleanup:
```python
async with aiosqlite.connect(self.db_path) as db:
    db.row_factory = aiosqlite.Row
    async with db.execute(query, params) as cursor:
        result = await cursor.fetchone()
```

## Storage Contract Guarantees

### Atomicity
Each operation is atomic per call. Multi-step operations (e.g., client + config insertion) handle rollback manually.

### Consistency
Foreign key constraints ensure referential integrity:
- `oauth_authorization_codes.client_id` → `oauth_clients.id`
- `oauth_access_tokens.client_id` → `oauth_clients.id`
- `oauth_refresh_tokens.client_id` → `oauth_clients.id`

### FIFO Revocation Semantics
Token limits are enforced with FIFO (First-In-First-Out) revocation:
- Client-level: Max N refresh tokens (oldest revoked first)
- Refresh-token-level: Max M access tokens (oldest revoked first)

Implementation responsibility: OAuth flows, not storage layer.

## Extension Guidelines

### Implementing a New Storage Backend

1. **Implement Abstract Interfaces**
   ```python
   from q_scope.implementations.store.templates import ClientTable
   
   class PostgresClientStore(ClientTable):
       async def insert(self, row: OAuthClient, ray_id: str) -> Result:
           # PostgreSQL-specific implementation
           ...
   ```

2. **Handle Async Operations**
   - Use appropriate async driver (asyncpg, motor, etc.)
   - Ensure proper connection pooling
   - Handle transactions appropriately

3. **Return Result Types**
   - Wrap all returns in `SuccessResult`/`FailedResult`
   - Use consistent error codes (`NOT_FOUND`, `INSERT_FAILED`, etc.)

4. **Map Domain Models**
   - Convert database rows to domain models (`OAuthClient`, `AccessToken`, etc.)
   - Handle type conversions (booleans, timestamps, etc.)

5. **Write Contract Tests**
   - Test all CRUD operations
   - Test domain-specific methods
   - Test error cases

### Adding a New Table

1. **Define Abstract Interface** in `templates/__init__.py`:
   ```python
   class NewTable(BaseTable[NewModel], ABC):
       @abstractmethod
       async def custom_query(self, param: str, ray_id: str) -> Optional[NewModel]:
           ...
   ```

2. **Update SQL Schema** in `sqllite/oauth.sql`:
   ```sql
   CREATE TABLE new_table (
       id TEXT PRIMARY KEY,
       ...
   );
   ```

3. **Implement Store** in `sqllite/pypika_imp/stores.py`:
   ```python
   class NewStore(NewTable):
       async def insert(self, row: NewModel, ray_id: str) -> Result:
           ...
   ```

## Dependencies

### Internal
- **datastrutures**: Domain models (`OAuthClient`, `AccessToken`, etc.)
- **datastrutures**: Result types (`SuccessResult`, `FailedResult`)

### External
- **PyPika**: SQL query builder
- **aiosqlite**: Async SQLite driver
- **libsql** (future): Turso/libSQL driver

## Testing Strategy

### Contract Tests
Test abstract interfaces to ensure all implementations behave consistently:
```python
async def test_client_store_contract(store: ClientTable):
    # Test insert
    result = await store.insert(client, ray_id)
    assert result.status is True
    
    # Test get_by_id
    result = await store.get_by_id(client.id, ray_id)
    assert result.status is True
    assert result.client_message.id == client.id
```

### Implementation Tests
Test SQLite-specific behavior:
- PyPika query generation
- aiosqlite integration
- Error handling
- Type conversions

### E2E Tests
Test full OAuth flows with SQLite backend to ensure storage layer integrates correctly.

## Performance Considerations

### Indexes
Schema includes indexes for common queries:
```sql
CREATE INDEX idx_clients_enabled ON oauth_clients (is_enabled);
CREATE INDEX idx_access_tokens_expires ON oauth_access_tokens (expires_at);
CREATE INDEX idx_refresh_tokens_client ON oauth_refresh_tokens (client_id);
```

### Connection Pooling
Future implementations should use connection pooling for production workloads.

### Query Optimization
PyPika allows for query inspection and optimization before execution.

## Related Documentation

- **Storage Templates**: [templates/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/templates/imp.md)
- **SQLite Implementation**: [sqllite/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/sqllite/imp.md)
- **Data Structures**: [../datastrutures/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/datastrutures/imp.md)
- **Project Intent**: [../../ai/ci.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/ci.md)

---

**Summary**: The storage layer provides a clean abstraction for data persistence with a SQLite/Turso reference implementation. It uses PyPika for query generation, async operations via aiosqlite, and wraps all results in typed Result objects. The schema is treated as public API, and the layer is designed for easy extension to other database backends.
