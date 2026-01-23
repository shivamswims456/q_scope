# Secret Management Implementation

## Purpose

The `secrets/` directory will provide concrete implementations of secret generation and hashing for OAuth2 client secrets. This directory currently has placeholder files but will contain production-ready secret handling implementations.

## Architecture Context

```
ClientRegistrar
       ↓
┌──────────────────────────────────────┐
│     SECRET MANAGEMENT LAYER          │
│  ┌────────────────────────────────┐  │
│  │ ClientSecretGenerator (impl)   │  │
│  │  - Generate high-entropy       │  │
│  │    secrets                     │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ ClientSecretHasher (impl)      │  │
│  │  - Hash secrets (bcrypt/argon2)│  │
│  │  - Verify secrets              │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

## Planned Implementations

### 1. DefaultSecretGenerator
**Purpose**: Generate cryptographically secure client secrets using Python's `secrets` module.

**Planned Implementation**:
```python
import secrets
from q_scope.implementations.oauth2.templates.base import ClientSecretGenerator

class DefaultSecretGenerator(ClientSecretGenerator):
    """
    Default secret generator using Python's secrets module.
    Generates URL-safe, high-entropy secrets.
    """
    
    def __init__(self, *, secret_length: int = 32):
        """
        Args:
            secret_length: Length of the secret in bytes (default: 32)
        """
        self._secret_length = secret_length
    
    def generate_secret(self, *, user_id: str) -> str:
        """
        Generate a URL-safe secret.
        
        Args:
            user_id: Owner context (not used for entropy)
        
        Returns:
            URL-safe base64-encoded secret
        """
        return secrets.token_urlsafe(self._secret_length)
```

**Security Properties**:
- Uses `secrets.token_urlsafe()` which is cryptographically secure
- Default 32 bytes = 256 bits of entropy
- URL-safe encoding (base64 with `-` and `_` instead of `+` and `/`)
- No predictable patterns based on `user_id`

---

### 2. BcryptSecretHasher
**Purpose**: Hash and verify client secrets using bcrypt.

**Planned Implementation**:
```python
import bcrypt
from q_scope.implementations.oauth2.templates.base import ClientSecretHasher

class BcryptSecretHasher(ClientSecretHasher):
    """
    Secret hasher using bcrypt.
    Provides strong password hashing with configurable work factor.
    """
    
    def __init__(self, *, rounds: int = 12):
        """
        Args:
            rounds: bcrypt work factor (default: 12)
                    Higher = more secure but slower
        """
        self._rounds = rounds
    
    def hash(
        self,
        secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> str:
        """
        Hash a secret using bcrypt.
        
        Args:
            secret: Raw client secret
            user_id: Owner context (not used for salting)
            client_id: Client context (not used for salting)
        
        Returns:
            bcrypt hash string (self-contained with salt)
        """
        salt = bcrypt.gensalt(rounds=self._rounds)
        hashed = bcrypt.hashpw(secret.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify(
        self,
        secret: str,
        hashed_secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> bool:
        """
        Verify a secret against a bcrypt hash.
        
        Args:
            secret: Raw client secret
            hashed_secret: Previously stored hash
            user_id: Owner context (not used)
            client_id: Client context (not used)
        
        Returns:
            True if secret matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                secret.encode('utf-8'),
                hashed_secret.encode('utf-8')
            )
        except Exception:
            return False
```

**Security Properties**:
- bcrypt is designed for password hashing
- Configurable work factor (default: 12 rounds)
- Built-in salt generation
- Constant-time comparison
- Resistant to timing attacks

---

### 3. Argon2SecretHasher (Alternative)
**Purpose**: Hash and verify client secrets using Argon2 (winner of Password Hashing Competition).

**Planned Implementation**:
```python
from argon2 import PasswordHasher
from q_scope.implementations.oauth2.templates.base import ClientSecretHasher

class Argon2SecretHasher(ClientSecretHasher):
    """
    Secret hasher using Argon2id.
    Provides state-of-the-art password hashing.
    """
    
    def __init__(self):
        # Use default parameters (recommended by argon2-cffi)
        self._hasher = PasswordHasher()
    
    def hash(
        self,
        secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> str:
        """Hash a secret using Argon2id."""
        return self._hasher.hash(secret)
    
    def verify(
        self,
        secret: str,
        hashed_secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> bool:
        """Verify a secret against an Argon2 hash."""
        try:
            self._hasher.verify(hashed_secret, secret)
            return True
        except Exception:
            return False
```

**Security Properties**:
- Argon2id (hybrid mode) resistant to side-channel attacks
- Memory-hard algorithm (resistant to GPU/ASIC attacks)
- Recommended by OWASP
- Automatic parameter tuning

---

## Design Patterns

### 1. Strategy Pattern
Different secret generation and hashing strategies can be swapped via dependency injection:
```python
# Use bcrypt
registrar = ClientRegistrar(
    client_store=client_store,
    config_store=config_store,
    secret_generator=DefaultSecretGenerator(),
    secret_hasher=BcryptSecretHasher(rounds=12)
)

# Or use Argon2
registrar = ClientRegistrar(
    client_store=client_store,
    config_store=config_store,
    secret_generator=DefaultSecretGenerator(),
    secret_hasher=Argon2SecretHasher()
)
```

### 2. Separation of Concerns
- **Generation**: `ClientSecretGenerator` only generates secrets
- **Hashing**: `ClientSecretHasher` only hashes/verifies secrets
- **Storage**: Service layer handles persistence
- **Policy**: Config layer defines requirements

---

## Security Considerations

### Secret Generation
1. **Entropy**: Use cryptographically secure random number generator (CSPRNG)
2. **Length**: Minimum 32 bytes (256 bits) for adequate security
3. **Encoding**: URL-safe encoding for easy transmission
4. **Uniqueness**: Each secret must be unique

### Secret Hashing
1. **Algorithm**: Use bcrypt or Argon2 (not SHA-256 or MD5)
2. **Work Factor**: Configurable to adapt to hardware improvements
3. **Salt**: Automatically generated and stored with hash
4. **Timing**: Constant-time comparison to prevent timing attacks

### Secret Storage
1. **Never store plaintext**: Only store hashed secrets
2. **Never log secrets**: Avoid logging plaintext secrets
3. **One-time transmission**: Return plaintext secret only once during registration
4. **Secure transmission**: Use HTTPS for secret transmission

### Secret Verification
1. **Constant-time comparison**: Prevent timing attacks
2. **Exception handling**: Return `False` on any error (don't leak information)
3. **Rate limiting**: Prevent brute-force attacks (implemented at API layer)

---

## Extension Guidelines

### Implementing a Custom Secret Generator

1. **Extend ClientSecretGenerator**:
   ```python
   from q_scope.implementations.oauth2.templates.base import ClientSecretGenerator
   
   class HSMSecretGenerator(ClientSecretGenerator):
       """Generate secrets using Hardware Security Module."""
       
       def __init__(self, hsm_client):
           self._hsm = hsm_client
       
       def generate_secret(self, *, user_id: str) -> str:
           # Generate secret using HSM
           random_bytes = self._hsm.generate_random(32)
           return base64.urlsafe_b64encode(random_bytes).decode('utf-8')
   ```

2. **Inject into Service**:
   ```python
   registrar = ClientRegistrar(
       client_store=client_store,
       config_store=config_store,
       secret_generator=HSMSecretGenerator(hsm_client),
       secret_hasher=BcryptSecretHasher()
   )
   ```

### Implementing a Custom Secret Hasher

1. **Extend ClientSecretHasher**:
   ```python
   from q_scope.implementations.oauth2.templates.base import ClientSecretHasher
   
   class PBKDF2SecretHasher(ClientSecretHasher):
       """Hash secrets using PBKDF2."""
       
       def hash(self, secret, *, user_id, client_id) -> str:
           import hashlib
           salt = os.urandom(32)
           key = hashlib.pbkdf2_hmac('sha256', secret.encode(), salt, 100000)
           return base64.b64encode(salt + key).decode('utf-8')
       
       def verify(self, secret, hashed_secret, *, user_id, client_id) -> bool:
           import hashlib
           decoded = base64.b64decode(hashed_secret.encode('utf-8'))
           salt = decoded[:32]
           stored_key = decoded[32:]
           new_key = hashlib.pbkdf2_hmac('sha256', secret.encode(), salt, 100000)
           return secrets.compare_digest(stored_key, new_key)
   ```

---

## Dependencies

### Internal
- **templates/base**: `ClientSecretGenerator`, `ClientSecretHasher`

### External (Planned)
- **secrets**: Python standard library (CSPRNG)
- **bcrypt**: bcrypt hashing library
- **argon2-cffi**: Argon2 hashing library (optional)

---

## Testing Strategy

### Secret Generation Tests
- Test entropy (statistical randomness)
- Test uniqueness (no collisions in large sample)
- Test length (meets minimum requirements)
- Test encoding (URL-safe characters only)

### Secret Hashing Tests
- Test hash generation
- Test verification (correct secret returns True)
- Test verification (incorrect secret returns False)
- Test constant-time comparison (timing attack resistance)
- Test exception handling (malformed hash returns False)

### Integration Tests
- Test generation + hashing workflow
- Test secret lifecycle (generate → hash → verify)

---

## Related Documentation

- **OAuth2 Layer**: [../imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/imp.md)
- **Templates**: [../templates/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/templates/imp.md)
- **Client Management**: [../clients/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/clients/imp.md)

---

**Summary**: The secret management layer will provide production-ready implementations of `ClientSecretGenerator` and `ClientSecretHasher` using industry-standard algorithms (bcrypt, Argon2). It follows security best practices including high entropy, proper hashing, constant-time comparison, and separation of concerns.
