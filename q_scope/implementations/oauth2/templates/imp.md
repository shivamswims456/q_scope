# OAuth2 Templates Implementation

## Purpose

The `templates/` directory defines core abstractions and base classes for the OAuth2 implementation layer. These templates establish patterns for flow orchestration, validation logic, and secret management that are used throughout the framework.

## Architecture Context

```
┌──────────────────────────────────────┐
│       OAUTH2 TEMPLATES LAYER         │
│  ┌────────────────────────────────┐  │
│  │ OAuth2Authorization            │  │
│  │  - Template Method for flows   │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ Condition                      │  │
│  │  - Validation pattern          │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ ClientSecretGenerator          │  │
│  │ ClientSecretHasher             │  │
│  │  - Secret management           │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
       ↓
   Concrete Implementations
   (Flows, Conditions, Secret Handlers)
```

## Key Files & Logic

### `base.py` (230 lines)
Single file containing all template abstractions.

---

## Core Abstractions

### 1. OAuth2Authorization (Base Class for Flows)

**Purpose**: Template method pattern for OAuth2 flow lifecycle.

**Structure**:
```python
class OAuth2Authorization(ABC):
    def __init__(self, *, storage, clock, config, logger):
        self._storage = storage
        self._clock = clock
        self._config = config
        self._logger = logger
    
    async def execute(self, *, context, ray_id) -> Mapping[str, Any]:
        """Execute the authorization flow. MUST NOT be overridden."""
        self._log_start(context)
        await self._preconditions(context, ray_id)
        result = await self._run(context, ray_id)
        await self._postconditions(context, result, ray_id)
        self._log_success(context, result, ray_id)
        return result
    
    @abstractmethod
    async def _preconditions(self, context, ray_id) -> None:
        """Validate flow-specific preconditions. MUST raise OAuth errors on failure."""
        ...
    
    @abstractmethod
    async def _run(self, context, ray_id) -> Mapping[str, Any]:
        """Execute the core flow logic. MUST return a serializable result."""
        ...
    
    @abstractmethod
    async def _postconditions(self, context, result, ray_id) -> None:
        """Persist state, audit logs, etc."""
        ...
```

**Lifecycle**:
1. **Log Start**: Record flow initiation
2. **Preconditions**: Validate input and state (raises on failure)
3. **Run**: Execute core flow logic
4. **Postconditions**: Persist tokens, audit logs
5. **Log Success**: Record flow completion

**Design Philosophy**:
- **Template Method**: `execute()` defines the algorithm, subclasses fill in the steps
- **Dependency Injection**: All dependencies injected via constructor
- **Immutable**: `execute()` is final and cannot be overridden
- **Logging**: Built-in logging hooks

**Example Usage**:
```python
class RefreshTokenFlow(OAuth2Authorization):
    async def _preconditions(self, context, ray_id):
        # Validate refresh token
        chain = ConditionChain([...])
        result = await chain.execute(context=context, ray_id=ray_id)
        if not result.status:
            raise OAuthError(result.error_code)
    
    async def _run(self, context, ray_id):
        # Generate new access token
        return {"access_token": ..., "token_type": "Bearer", ...}
    
    async def _postconditions(self, context, result, ray_id):
        # Persist token
        await self._storage.access_tokens.insert(result["access_token"], ray_id)
```

---

### 2. Condition (Validation Pattern)

**Purpose**: Composable validation logic for OAuth flows.

**Structure**:
```python
class Condition(ABC):
    @abstractmethod
    async def validate(
        self,
        *,
        context: Mapping[str, Any],
        ray_id: str,
    ) -> Result:
        """
        Validate a single condition.
        
        MUST:
        - return SuccessResult to continue
        - return FailedResult to stop execution
        
        MUST NOT:
        - raise business exceptions
        - mutate config
        """
        ...
```

**Design Philosophy**:
- **Composable**: Chain multiple conditions together
- **Reusable**: Share conditions across flows
- **Testable**: Test conditions in isolation
- **Explicit**: Return `Result` instead of raising exceptions
- **Immutable**: Cannot mutate config

**Example Usage**:
```python
class ValidateRefreshTokenCondition(Condition):
    async def validate(self, *, context, ray_id) -> Result:
        refresh_token = context.get("refresh_token")
        
        if not refresh_token:
            return FailedResult(
                ray_id=ray_id,
                client_message="refresh_token is required",
                error_code=OAuthErrors.INVALID_REQUEST
            )
        
        # Query from storage
        result = await storage.refresh_tokens.get_by_token(refresh_token, ray_id)
        
        if not result.status:
            return FailedResult(
                ray_id=ray_id,
                client_message="Invalid refresh token",
                error_code=OAuthErrors.INVALID_GRANT
            )
        
        # Store in context for later use
        context["refresh_token_obj"] = result.client_message
        
        return SuccessResult(ray_id=ray_id, client_message=None)
```

**Chaining Conditions**:
```python
from q_scope.implementations.oauth2.helpers import ConditionChain

chain = ConditionChain([
    ValidateRefreshTokenPresenceCondition(),
    AuthenticateClientCondition(),
    ValidateRefreshTokenCondition(),
    CheckTokenLimitCondition()
])

result = await chain.execute(context=context, ray_id=ray_id)
# Stops at first FailedResult
```

---

### 3. ClientSecretGenerator

**Purpose**: Abstract interface for generating OAuth client secrets.

**Structure**:
```python
class ClientSecretGenerator(ABC):
    @abstractmethod
    def generate_secret(self, *, user_id: str) -> str:
        """
        Generate a new raw client secret.
        
        Args:
            user_id: Owner of the client (for entropy mixing, audit, or HSM routing).
                     Must NOT reduce entropy or make output predictable.
        
        Returns:
            A raw client secret as a string.
        
        Raises:
            RuntimeError or lower-level exceptions on entropy failure.
        """
        ...
```

**Responsibilities**:
- ✅ Generate high-entropy, cryptographically secure secrets
- ✅ Return raw secret as string
- ❌ NOT hash the secret (that's `ClientSecretHasher`'s job)
- ❌ NOT persist the secret (that's the service layer's job)
- ❌ NOT encode policy (that's the config's job)

**Example Implementation**:
```python
import secrets

class DefaultSecretGenerator(ClientSecretGenerator):
    def generate_secret(self, *, user_id: str) -> str:
        # Generate 32-byte URL-safe secret
        return secrets.token_urlsafe(32)
```

---

### 4. ClientSecretHasher

**Purpose**: Abstract interface for hashing and verifying OAuth client secrets.

**Structure**:
```python
class ClientSecretHasher(ABC):
    @abstractmethod
    def hash(
        self,
        secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> str:
        """
        Hash a raw client secret for storage.
        
        Args:
            secret: Raw client secret
            user_id: Owner context (namespacing / salting / routing only)
            client_id: Client context (namespacing / salting / routing only)
        
        Returns:
            An opaque, self-contained hash string suitable for persistence.
        """
        ...
    
    @abstractmethod
    def verify(
        self,
        secret: str,
        hashed_secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> bool:
        """
        Verify a raw client secret against a stored hash.
        
        Args:
            secret: Raw client secret
            hashed_secret: Previously stored hash
            user_id: Owner context
            client_id: Client context
        
        Returns:
            True if the secret matches, False otherwise.
        """
        ...
```

**Responsibilities**:
- ✅ Hash raw client secrets for storage
- ✅ Verify raw secrets against stored hashes
- ❌ NOT generate secrets (that's `ClientSecretGenerator`'s job)
- ❌ NOT persist secrets (that's the service layer's job)
- ❌ NOT enforce policy (that's the config's job)
- ❌ NOT return Result objects (raise exceptions for infrastructure failures)

**Example Implementation**:
```python
import bcrypt

class BcryptSecretHasher(ClientSecretHasher):
    def hash(self, secret, *, user_id, client_id) -> str:
        # Hash with bcrypt (12 rounds)
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(secret.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify(self, secret, hashed_secret, *, user_id, client_id) -> bool:
        # Verify with bcrypt (constant-time comparison)
        return bcrypt.checkpw(
            secret.encode('utf-8'),
            hashed_secret.encode('utf-8')
        )
```

---

## Design Patterns

### 1. Template Method Pattern
`OAuth2Authorization` defines the flow algorithm, subclasses implement the steps.

### 2. Strategy Pattern
`Condition` objects encapsulate validation strategies that can be composed and reused.

### 3. Abstract Factory Pattern
`ClientSecretGenerator` and `ClientSecretHasher` are abstract factories for secret handling.

### 4. Dependency Injection
All dependencies are injected, enabling testability and flexibility.

### 5. Separation of Concerns
Each abstraction has a single, well-defined responsibility:
- **OAuth2Authorization**: Flow orchestration
- **Condition**: Validation logic
- **ClientSecretGenerator**: Secret generation
- **ClientSecretHasher**: Secret hashing/verification

---

## Extension Guidelines

### Creating a New Flow

1. **Extend OAuth2Authorization**:
   ```python
   class NewFlow(OAuth2Authorization):
       async def _preconditions(self, context, ray_id):
           # Validate using Condition pattern
           ...
       
       async def _run(self, context, ray_id):
           # Core flow logic
           ...
       
       async def _postconditions(self, context, result, ray_id):
           # Persist state
           ...
   ```

2. **Inject Dependencies**:
   ```python
   flow = NewFlow(
       storage=storage,
       clock=clock,
       config=config,
       logger=logger
   )
   ```

3. **Execute Flow**:
   ```python
   result = await flow.execute(context=context, ray_id=ray_id)
   ```

### Creating a New Condition

1. **Implement Condition Interface**:
   ```python
   class ValidateNewThingCondition(Condition):
       async def validate(self, *, context, ray_id) -> Result:
           if context.get("new_thing") is None:
               return FailedResult(
                   ray_id=ray_id,
                   client_message="new_thing is required",
                   error_code="INVALID_REQUEST"
               )
           return SuccessResult(ray_id=ray_id, client_message=None)
   ```

2. **Use in Flow**:
   ```python
   chain = ConditionChain([
       ValidateNewThingCondition(),
       # ... other conditions
   ])
   ```

### Implementing Custom Secret Handling

1. **Implement Generator**:
   ```python
   class HSMSecretGenerator(ClientSecretGenerator):
       def generate_secret(self, *, user_id) -> str:
           # Generate secret using HSM
           return hsm.generate_random(32)
   ```

2. **Implement Hasher**:
   ```python
   class Argon2SecretHasher(ClientSecretHasher):
       def hash(self, secret, *, user_id, client_id) -> str:
           return argon2.hash(secret)
       
       def verify(self, secret, hashed_secret, *, user_id, client_id) -> bool:
           return argon2.verify(hashed_secret, secret)
   ```

3. **Inject into Service**:
   ```python
   registrar = ClientRegistrar(
       client_store=client_store,
       config_store=config_store,
       secret_generator=HSMSecretGenerator(),
       secret_hasher=Argon2SecretHasher()
   )
   ```

---

## Dependencies

### Internal
- **datastrutures**: `Result`, `SuccessResult`, `FailedResult`

### External
- **abc**: `ABC`, `abstractmethod`
- **typing**: `Mapping`, `Any`, `Optional`

---

## Testing Strategy

### Unit Tests
- Test template method lifecycle
- Test condition validation logic
- Test secret generation/hashing

### Integration Tests
- Test flow execution with real conditions
- Test condition chaining
- Test secret handling integration

---

## Related Documentation

- **OAuth2 Layer**: [../imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/imp.md)
- **OAuth Flows**: [../oauth_flows/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/oauth_flows/imp.md)
- **Helpers**: [../helpers/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/helpers/imp.md)
- **Client Management**: [../clients/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/clients/imp.md)

---

**Summary**: The OAuth2 templates layer provides core abstractions for flow orchestration (`OAuth2Authorization`), validation logic (`Condition`), and secret management (`ClientSecretGenerator`, `ClientSecretHasher`). These templates establish consistent patterns used throughout the OAuth2 implementation, enabling extensibility, testability, and clear separation of concerns.
