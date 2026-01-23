# SQLite/Turso Storage Implementation

## Purpose

The `sqllite/` directory provides the reference implementation of the storage layer using SQLite (and Turso/libSQL). It includes SQL schema definitions and PyPika-based query implementations that serve as both a production-ready backend and a reference for other storage implementations.

## Architecture Context

```
Storage Templates (Abstract Contracts)
         ↓
┌──────────────────────────────────────┐
│    SQLITE/TURSO IMPLEMENTATION       │
│  ┌────────────────────────────────┐  │
│  │ Schema Files:                  │  │
│  │  - oauth.sql                   │  │
│  │  - logs.sql                    │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ PyPika Implementation:         │  │
│  │  - OAuthClientStore            │  │
│  │  - OAuthClientConfigStore      │  │
│  │  - (Future: Token stores, etc.)│  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
         ↓
   SQLite/Turso Database
```

## Key Files & Logic

### Schema Files

#### `oauth.sql` (163 lines)
Defines the complete OAuth2 schema:

**Tables**:
1. **`oauth_clients`**: Client identity and capabilities
   - Primary key: `id` (internal UUID)
   - Unique: `client_identifier` (public OAuth2 client_id)
   - Foreign keys: None
   - Indexes: `is_enabled`

2. **`oauth_users`**: Reference user table
   - Primary key: `id`
   - Unique: `external_id`
   - Foreign keys: None

3. **`oauth_authorization_codes`**: Authorization codes with PKCE
   - Primary key: `id`
   - Unique: `code`
   - Foreign keys: `client_id`, `user_id`
   - Indexes: `client_id`, `expires_at`

4. **`oauth_access_tokens`**: Access tokens
   - Primary key: `id`
   - Unique: `token`
   - Foreign keys: `client_id`, `user_id`
   - Indexes: `client_id`, `user_id`, `expires_at`, `created_at`

5. **`oauth_refresh_tokens`**: Refresh tokens
   - Primary key: `id`
   - Unique: `token`
   - Foreign keys: `client_id`, `user_id`
   - Indexes: `client_id`, `user_id`, `created_at`

6. **`oauth_device_codes`**: Device authorization codes
   - Primary key: `id`
   - Unique: `device_code`, `user_code`
   - Foreign keys: `client_id`, `user_id` (nullable)
   - Indexes: `state`, `expires_at`
   - Check constraint: `state IN ('pending', 'approved', 'denied', 'consumed', 'expired')`

**Schema Features**:
- **Foreign Keys**: Enabled with `PRAGMA foreign_keys = ON`
- **Cascading Deletes**: Client deletion cascades to tokens/codes
- **Check Constraints**: Boolean values, device code states
- **Audit Fields**: All tables have `created_at`, `created_by`, `updated_at`, `updated_by`

---

#### `logs.sql` (426 bytes)
Defines the audit log schema (append-only):

**Table**: `oauth_audit_logs`
- Primary key: `id`
- Fields: `event_type`, `subject`, `client_id`, `user_id`, `metadata`
- Audit fields: `created_at`, `created_by`, `updated_at`, `updated_by`

**Note**: No update or delete operations allowed (append-only).

---

### PyPika Implementation

#### `pypika_imp/__init__.py`
Defines PyPika table objects for query building:
```python
from pypika import Table

oauth_clients = Table("oauth_clients")
oauth_client_configs = Table("oauth_client_configs")
oauth_users = Table("oauth_users")
oauth_authorization_codes = Table("oauth_authorization_codes")
oauth_access_tokens = Table("oauth_access_tokens")
oauth_refresh_tokens = Table("oauth_refresh_tokens")
oauth_device_codes = Table("oauth_device_codes")
```

---

#### `pypika_imp/stores.py` (549 lines)
Implements storage contracts using PyPika and aiosqlite.

**Implemented Stores**:
1. **`OAuthClientStore`**: Implements `ClientTable`
2. **`OAuthClientConfigStore`**: Client configuration CRUD

**Future Stores** (planned):
- `AuthorizationCodeStore`
- `AccessTokenStore`
- `RefreshTokenStore`
- `DeviceCodeStore`
- `AuditLogStore`

---

## OAuthClientStore Implementation

### Structure
```python
class OAuthClientStore(ClientTable):
    def __init__(self, db_path: str):
        self.db_path = db_path
```

### Methods

#### `insert()`
```python
async def insert(self, row: OAuthClient, ray_id: str) -> Union[SuccessResult, FailedResult]:
    query = Query.into(oauth_clients).columns(...).insert(...)
    
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(str(query), {...})
        await db.commit()
    
    return SuccessResult(ray_id=ray_id, client_message="...")
```

**Features**:
- Uses PyPika `Query.into()` for INSERT
- Uses `Parameter(":name")` for parameterized queries
- Wraps result in `SuccessResult` or `FailedResult`
- Handles exceptions and returns `FailedResult` with error code

---

#### `get_by_id()`
```python
async def get_by_id(self, id: str, ray_id: str) -> Union[SuccessResult, FailedResult]:
    query = Query.from_(oauth_clients).select(...).where(...)
    
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row  # Enable column access by name
        async with db.execute(str(query), {"id": id}) as cursor:
            result = await cursor.fetchone()
            
            if result is None:
                return FailedResult(
                    ray_id=ray_id,
                    client_message=f"OAuth client with ID {id} not found",
                    error_code="NOT_FOUND"
                )
            
            client = OAuthClient(...)  # Map row to domain model
            return SuccessResult(ray_id=ray_id, client_message=client)
```

**Features**:
- Uses PyPika `Query.from_().select().where()`
- Sets `row_factory = aiosqlite.Row` for named column access
- Returns `FailedResult` with `NOT_FOUND` if not found
- Maps database row to `OAuthClient` domain model
- Wraps result in `SuccessResult`

---

#### `get_by_client_identifier()`
Similar to `get_by_id()` but queries by `client_identifier` field.

---

#### `update()`
```python
async def update(self, row: OAuthClient, ray_id: str) -> Union[SuccessResult, FailedResult]:
    query = Query.update(oauth_clients).set(...).where(...)
    
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(str(query), {...})
        await db.commit()
    
    return SuccessResult(ray_id=ray_id, client_message="...")
```

**Features**:
- Uses PyPika `Query.update().set().where()`
- Updates all mutable fields
- Does NOT update `created_at` or `created_by` (immutable audit fields)

---

#### `delete_by_id()`
```python
async def delete_by_id(self, id: str, ray_id: str) -> Union[SuccessResult, FailedResult]:
    query = Query.from_(oauth_clients).delete().where(...)
    
    async with aiosqlite.connect(self.db_path) as db:
        cursor = await db.execute(str(query), {"id": id})
        await db.commit()
        
        if cursor.rowcount == 0:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"OAuth client with ID {id} not found",
                error_code="NOT_FOUND"
            )
    
    return SuccessResult(ray_id=ray_id, client_message="...")
```

**Features**:
- Uses PyPika `Query.from_().delete().where()`
- Checks `cursor.rowcount` to detect if row was deleted
- Returns `FailedResult` with `NOT_FOUND` if no rows affected

---

## OAuthClientConfigStore Implementation

Similar structure to `OAuthClientStore` but for `OAuthClientConfig` domain model.

**Methods**:
- `insert()`: Insert client configuration
- `get_by_client_id()`: Retrieve config by client ID
- `update()`: Update client configuration
- `delete_by_client_id()`: Delete config by client ID

---

## Design Patterns

### 1. PyPika Query Builder
Generates SQL queries programmatically:
```python
query = Query.from_(oauth_clients).select(
    "id", "client_identifier", ...
).where(oauth_clients.id == Parameter(":id"))

# Generates: SELECT id, client_identifier, ... FROM oauth_clients WHERE id = :id
```

**Benefits**:
- Type-safe query construction
- Prevents SQL injection
- Readable and maintainable
- Database-agnostic (can target different SQL dialects)

### 2. Async Context Managers
All database operations use async context managers:
```python
async with aiosqlite.connect(self.db_path) as db:
    async with db.execute(query, params) as cursor:
        result = await cursor.fetchone()
```

**Benefits**:
- Automatic connection cleanup
- Exception safety
- Resource management

### 3. Result Wrapping
All operations return `SuccessResult` or `FailedResult`:
```python
# Success
return SuccessResult(ray_id=ray_id, client_message=client)

# Failure
return FailedResult(
    ray_id=ray_id,
    client_message="Client not found",
    error_code="NOT_FOUND"
)
```

### 4. Domain Model Mapping
Database rows are mapped to domain models:
```python
client = OAuthClient(
    id=result["id"],
    client_identifier=result["client_identifier"],
    client_secret=result["client_secret"],
    is_confidential=bool(result["is_confidential"]),  # Convert INTEGER to bool
    ...
)
```

---

## SQLite vs Turso

### SQLite
- **Local file-based database**
- **Synchronous replication** (not suitable for distributed systems)
- **Perfect for**: Development, testing, single-instance deployments

### Turso (libSQL)
- **Distributed SQLite** (SQLite-compatible with replication)
- **Edge deployment** (global distribution)
- **Perfect for**: Production, multi-region, serverless

**Compatibility**: The same code works with both SQLite and Turso by changing the connection string:
```python
# SQLite
store = OAuthClientStore(db_path="sqlite:///oauth2.db")

# Turso
store = OAuthClientStore(db_path="libsql://your-database.turso.io")
```

---

## Extension Guidelines

### Adding a New Store

1. **Implement Storage Template**:
   ```python
   from q_scope.implementations.store.templates import AccessTokenTable
   
   class SQLiteAccessTokenStore(AccessTokenTable):
       def __init__(self, db_path: str):
           self.db_path = db_path
       
       async def insert(self, row: AccessToken, ray_id: str) -> Result:
           query = Query.into(oauth_access_tokens).columns(...).insert(...)
           # ... implementation
       
       async def get_by_id(self, id: str, ray_id: str) -> Result:
           # ... implementation
       
       async def get_by_token(self, token: str, ray_id: str) -> Result:
           # ... implementation
   ```

2. **Add to `pypika_imp/__init__.py`**:
   ```python
   oauth_access_tokens = Table("oauth_access_tokens")
   ```

3. **Export from Module**:
   ```python
   from .stores import OAuthClientStore, SQLiteAccessTokenStore
   
   __all__ = ["OAuthClientStore", "SQLiteAccessTokenStore"]
   ```

---

## Dependencies

### Internal
- **store/templates**: Abstract storage contracts
- **datastrutures**: Domain models, Result types

### External
- **PyPika**: SQL query builder
- **aiosqlite**: Async SQLite driver
- **libsql** (future): Turso/libSQL driver

---

## Testing Strategy

### Schema Tests
- Test schema creation
- Test foreign key constraints
- Test check constraints
- Test indexes

### Store Tests
- Test all CRUD operations
- Test error cases (not found, duplicate, etc.)
- Test domain model mapping
- Test transaction handling

### Integration Tests
- Test with real SQLite database
- Test with Turso (if available)
- Test concurrent operations

---

## Related Documentation

- **Storage Layer**: [../imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/imp.md)
- **Storage Templates**: [../templates/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/templates/imp.md)
- **Data Structures**: [../../datastrutures/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/datastrutures/imp.md)

---

**Summary**: The SQLite/Turso storage implementation provides a production-ready reference backend using PyPika for query generation and aiosqlite for async operations. It includes comprehensive schema definitions, implements storage contracts with Result wrapping, and supports both local SQLite and distributed Turso deployments.
