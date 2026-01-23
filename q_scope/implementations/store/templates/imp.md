# Storage Templates Implementation

## Purpose

The `templates/` directory defines abstract storage contracts for the q_scope framework. These interfaces establish the contract that all storage backends must implement, ensuring consistent behavior across different database implementations.

## Architecture Context

```
OAuth2 Flows & Services
         ↓
┌──────────────────────────────────────┐
│    STORAGE TEMPLATES (Contracts)     │
│  ┌────────────────────────────────┐  │
│  │ BaseTable[T]                   │  │
│  │  - Generic CRUD interface      │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ Specialized Tables:            │  │
│  │  - ClientTable                 │  │
│  │  - AuthorizationCodeTable      │  │
│  │  - AccessTokenTable            │  │
│  │  - RefreshTokenTable           │  │
│  │  - DeviceCodeTable             │  │
│  │  - AuditLogTable               │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
         ↓
   Concrete Implementations
   (SQLite, PostgreSQL, etc.)
```

## Key Files & Logic

### `__init__.py` (121 lines)
Single file containing all abstract storage interfaces using Python's `ABC` (Abstract Base Class) and `Generic` types.

## Storage Contracts

### 1. BaseTable[T] (Generic CRUD)

Generic base class for all table operations:

```python
class BaseTable(Generic[T], ABC):
    @abstractmethod
    async def insert(self, row: T, ray_id: str) -> None:
        """Insert a new row."""
        ...
    
    @abstractmethod
    async def get_by_id(self, id: str, ray_id: str) -> Optional[T]:
        """Retrieve a row by ID."""
        ...
    
    @abstractmethod
    async def update(self, row: T, ray_id: str) -> None:
        """Update an existing row."""
        ...
    
    @abstractmethod
    async def delete_by_id(self, id: str, ray_id: str) -> None:
        """Delete a row by ID."""
        ...
```

**Type Parameter `T`**: Domain model type (e.g., `OAuthClient`, `AccessToken`)

**Design**: Standard CRUD operations that all tables must support.

---

### 2. ClientTable

Extends `BaseTable[OAuthClient]` with client-specific operations:

```python
class ClientTable(BaseTable[OAuthClient], ABC):
    @abstractmethod
    async def get_by_client_identifier(
        self,
        client_identifier: str,
        ray_id: str
    ) -> Optional[OAuthClient]:
        """Retrieve a client by its public identifier."""
        ...
```

**Additional Methods**:
- `get_by_client_identifier()`: Query by OAuth2 `client_id`

---

### 3. AuthorizationCodeTable

Extends `BaseTable[AuthorizationCode]`:

```python
class AuthorizationCodeTable(BaseTable[AuthorizationCode], ABC):
    @abstractmethod
    async def get_by_code(
        self,
        code: str,
        ray_id: str
    ) -> Optional[AuthorizationCode]:
        """Retrieve an authorization code by the code string."""
        ...
    
    @abstractmethod
    async def delete_by_code(
        self,
        code: str,
        ray_id: str
    ) -> None:
        """Delete an authorization code by the code string."""
        ...
```

**Additional Methods**:
- `get_by_code()`: Query by authorization code string
- `delete_by_code()`: Delete by code (after consumption)

---

### 4. AccessTokenTable

Extends `BaseTable[AccessToken]`:

```python
class AccessTokenTable(BaseTable[AccessToken], ABC):
    @abstractmethod
    async def get_by_token(
        self,
        token: str,
        ray_id: str
    ) -> Optional[AccessToken]:
        """Retrieve an access token by the token string."""
        ...
    
    async def delete_by_token(self, token: str, ray_id: str) -> None:
        """
        Optional convenience method.
        Default implementation delegates to get_by_token + delete_by_id.
        """
        row = await self.get_by_token(token, ray_id=ray_id)
        if row is not None:
            await self.delete_by_id(row.id, ray_id=ray_id)
```

**Additional Methods**:
- `get_by_token()`: Query by access token string
- `delete_by_token()`: Convenience method (has default implementation)

---

### 5. RefreshTokenTable

Extends `BaseTable[RefreshToken]`:

```python
class RefreshTokenTable(BaseTable[RefreshToken], ABC):
    @abstractmethod
    async def get_by_token(
        self,
        token: str,
        ray_id: str
    ) -> Optional[RefreshToken]:
        """Retrieve a refresh token by the token string."""
        ...
```

**Additional Methods**:
- `get_by_token()`: Query by refresh token string

---

### 6. DeviceCodeTable

Extends `BaseTable[DeviceCode]`:

```python
class DeviceCodeTable(BaseTable[DeviceCode], ABC):
    @abstractmethod
    async def get_by_device_code(
        self,
        device_code: str,
        ray_id: str
    ) -> Optional[DeviceCode]:
        """Retrieve by device code string."""
        ...
    
    @abstractmethod
    async def get_by_user_code(
        self,
        user_code: str,
        ray_id: str
    ) -> Optional[DeviceCode]:
        """Retrieve by user-friendly code."""
        ...
```

**Additional Methods**:
- `get_by_device_code()`: Query by device code (for polling)
- `get_by_user_code()`: Query by user code (for verification UI)

---

### 7. AuditLogTable

Extends `BaseTable[AuditLog]` with append-only semantics:

```python
class AuditLogTable(BaseTable[AuditLog], ABC):
    async def update(self, row: AuditLog, ray_id: str) -> None:
        """Audit log is append-only."""
        raise NotImplementedError("audit_log is append-only")
    
    async def delete_by_id(self, id: str, ray_id: str) -> None:
        """Audit log is append-only."""
        raise NotImplementedError("audit_log is append-only")
```

**Restrictions**:
- **No updates**: Audit logs are immutable
- **No deletes**: Audit logs are permanent
- **Insert only**: Only `insert()` and `get_by_id()` are allowed

---

## Design Patterns

### 1. Generic Base Class
Uses Python's `Generic[T]` for type safety:
```python
class BaseTable(Generic[T], ABC):
    async def insert(self, row: T, ray_id: str) -> None:
        ...
```

Benefits:
- Type hints for domain models
- IDE autocomplete
- Static type checking

### 2. Abstract Base Class (ABC)
All methods are `@abstractmethod`, forcing implementations to provide concrete behavior.

### 3. Optional Return Types
Query methods return `Optional[T]`:
- `None`: Entity not found
- `T`: Entity found

This is a **storage-level** contract. The **service layer** wraps these in `SuccessResult`/`FailedResult`.

### 4. Async-First
All methods are `async`, enabling:
- Non-blocking I/O
- Connection pooling
- Concurrent operations

### 5. Ray ID Tracing
All methods accept `ray_id: str` for distributed tracing and debugging.

## Contract Guarantees

### Atomicity
Each method call is atomic. Multi-step operations (e.g., insert client + config) must handle rollback manually.

### Consistency
Implementations must enforce:
- Foreign key constraints
- Unique constraints
- Check constraints (e.g., boolean values)

### Return Semantics
- **Insert**: No return value (or exception on failure)
- **Get**: `Optional[T]` (None if not found)
- **Update**: No return value (or exception on failure)
- **Delete**: No return value (or exception on failure)

**Note**: The SQLite implementation wraps these in `Result` types at the **store implementation** level, not the template level.

## Extension Guidelines

### Implementing a Storage Backend

1. **Inherit from Template**:
   ```python
   from q_scope.implementations.store.templates import ClientTable
   from q_scope.implementations.datastrutures import OAuthClient
   
   class PostgresClientTable(ClientTable):
       async def insert(self, row: OAuthClient, ray_id: str) -> None:
           # PostgreSQL-specific implementation
           ...
   ```

2. **Implement All Abstract Methods**:
   - `insert()`, `get_by_id()`, `update()`, `delete_by_id()`
   - Plus any specialized methods (e.g., `get_by_client_identifier()`)

3. **Handle Async Operations**:
   - Use appropriate async driver (asyncpg, motor, etc.)
   - Manage connections properly
   - Handle exceptions

4. **Return Correct Types**:
   - `Optional[T]` for queries
   - `None` for mutations
   - Raise exceptions for infrastructure failures

### Adding a New Table Template

1. **Define Interface**:
   ```python
   class NewTable(BaseTable[NewModel], ABC):
       @abstractmethod
       async def custom_query(self, param: str, ray_id: str) -> Optional[NewModel]:
           """Custom query specific to this table."""
           ...
   ```

2. **Document Contract**: Explain what the custom methods do and when to use them.

3. **Update Implementations**: All storage backends must implement the new interface.

## Testing Strategy

### Contract Tests
Write tests that verify **any** implementation of a template behaves correctly:

```python
async def test_client_table_contract(client_table: ClientTable):
    """Test that any ClientTable implementation follows the contract."""
    
    # Test insert
    client = OAuthClient(...)
    await client_table.insert(client, ray_id="test")
    
    # Test get_by_id
    result = await client_table.get_by_id(client.id, ray_id="test")
    assert result is not None
    assert result.id == client.id
    
    # Test get_by_client_identifier
    result = await client_table.get_by_client_identifier(
        client.client_identifier, ray_id="test"
    )
    assert result is not None
    
    # Test update
    client.is_enabled = False
    await client_table.update(client, ray_id="test")
    
    # Test delete
    await client_table.delete_by_id(client.id, ray_id="test")
    result = await client_table.get_by_id(client.id, ray_id="test")
    assert result is None
```

Run these tests against **all** storage implementations to ensure consistency.

## Dependencies

### Internal
- **datastrutures**: Domain models (`OAuthClient`, `AccessToken`, etc.)

### External
- **typing**: `Generic`, `Optional`, `ABC`
- **abc**: `abstractmethod`

## Related Documentation

- **Storage Layer**: [../imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/imp.md)
- **SQLite Implementation**: [../sqllite/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/store/sqllite/imp.md)
- **Data Structures**: [../../datastrutures/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/datastrutures/imp.md)

---

**Summary**: Storage templates define abstract contracts for all storage operations using Python's ABC and Generic types. They establish a consistent interface for CRUD operations plus domain-specific queries, enabling pluggable storage backends while maintaining type safety and clear contracts.
