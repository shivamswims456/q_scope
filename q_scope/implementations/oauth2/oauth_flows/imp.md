# OAuth2 Flows Implementation

## Purpose

The `oauth_flows/` directory contains implementations of OAuth2 grant type flows. Each flow orchestrates the complete lifecycle of an OAuth2 authorization request, from validation through token issuance, using the Template Method and Condition patterns.

## Architecture Context

```
ASGI Endpoints (future)
       ↓
┌──────────────────────────────────────┐
│        OAUTH2 FLOWS LAYER            │
│  ┌────────────────────────────────┐  │
│  │ RefreshTokenFlow (in progress) │  │
│  │  - Preconditions (Conditions)  │  │
│  │  - Run (core logic)            │  │
│  │  - Postconditions (persist)    │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ Future Flows:                  │  │
│  │  - AuthorizationCodeFlow       │  │
│  │  - ClientCredentialsFlow       │  │
│  │  - DeviceAuthorizationFlow     │  │
│  │  - ResourceOwnerPasswordFlow   │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
       ↓
Storage Layer + Condition Chain
```

## Current Implementation Status

### ✅ In Progress
- **Refresh Token Flow** (`refresh_token_flow.py`): RFC 6749 refresh token grant

### 📋 Planned
- **Authorization Code Flow**: RFC 6749 + RFC 7636 (PKCE)
- **Client Credentials Flow**: RFC 6749 client credentials grant
- **Device Authorization Flow**: RFC 8628 device flow
- **Resource Owner Password Flow**: RFC 6749 password grant (deprecated)

## Key Files & Logic

### `refresh_token_flow.py`
Currently empty (in progress). Will implement:

**RFC**: RFC 6749 Section 6 (Refreshing an Access Token)

**Flow Diagram**: [../../ai/flows/refresh_token_flow.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/flows/refresh_token_flow.md)

**Lifecycle**:
1. **Preconditions**:
   - Validate refresh token presence
   - Authenticate client
   - Validate refresh token (not revoked, belongs to client)
   - Check access token limit (FIFO revocation if needed)

2. **Run**:
   - Generate new access token
   - Optionally rotate refresh token
   - Apply token limits

3. **Postconditions**:
   - Store new access token
   - Update refresh token `last_used_at`
   - Audit log: `token.issued`, `refresh_token.used`

**Interview Answers**: [interview_ansers.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/oauth_flows/interview_ansers.md) (currently empty, but referenced in conversation history)

---


## Design Patterns

### 1. Template Method Pattern
All flows extend `OAuth2Authorization` base class:

```python
class RefreshTokenFlow(OAuth2Authorization):
    async def _preconditions(self, context, ray_id):
        """Validate refresh token and client."""
        chain = ConditionChain([
            ValidateRefreshTokenPresenceCondition(),
            AuthenticateClientCondition(),
            ValidateRefreshTokenCondition(),
            CheckAccessTokenLimitCondition()
        ])
        result = await chain.execute(context=context, ray_id=ray_id)
        if not result.status:
            raise OAuthError(result.error_code, result.client_message)
    
    async def _run(self, context, ray_id):
        """Generate new access token."""
        access_token = await self._generate_access_token(context)
        return {"access_token": access_token, ...}
    
    async def _postconditions(self, context, result, ray_id):
        """Persist tokens and audit logs."""
        await self._storage.access_tokens.insert(result["access_token"], ray_id)
        await self._audit_log(event="token.issued", ray_id=ray_id)
```

### 2. Condition Pattern
Validation logic is encapsulated in reusable `Condition` objects:

```python
class ValidateRefreshTokenCondition(Condition):
    async def validate(self, context, ray_id) -> Result:
        refresh_token = context.get("refresh_token")
        
        # Query from storage
        result = await storage.refresh_tokens.get_by_token(refresh_token, ray_id)
        
        if not result.status:
            return FailedResult(
                ray_id=ray_id,
                client_message="Invalid refresh token",
                error_code=OAuthErrors.INVALID_GRANT
            )
        
        token = result.client_message
        
        # Check not revoked
        if token.revoked_at is not None:
            return FailedResult(
                ray_id=ray_id,
                client_message="Refresh token has been revoked",
                error_code=OAuthErrors.INVALID_GRANT
            )
        
        # Check client_id match
        if token.client_id != context.get("client_id"):
            return FailedResult(
                ray_id=ray_id,
                client_message="Refresh token does not belong to client",
                error_code=OAuthErrors.INVALID_GRANT
            )
        
        # Store in context for later use
        context["refresh_token_obj"] = token
        
        return SuccessResult(ray_id=ray_id, client_message=None)
```

### 3. Unit of Work Pattern
Each flow execution is a unit of work:
- **Begin**: Start flow execution
- **Validate**: Run preconditions
- **Execute**: Run core logic
- **Commit**: Persist state in postconditions
- **Rollback**: Handle errors (future)

### 4. FIFO Token Limits
Token limits are enforced with First-In-First-Out revocation:

```python
class CheckAccessTokenLimitCondition(Condition):
    async def validate(self, context, ray_id) -> Result:
        refresh_token = context["refresh_token_obj"]
        client_config = context["client_config"]
        
        max_tokens = client_config.max_active_access_tokens
        if max_tokens is None:
            return SuccessResult(ray_id=ray_id, client_message=None)
        
        # Count active access tokens for this refresh token
        active_tokens = await storage.access_tokens.count_by_refresh_token(
            refresh_token.id, ray_id
        )
        
        if active_tokens >= max_tokens:
            # Revoke oldest access token (FIFO)
            oldest = await storage.access_tokens.get_oldest_by_refresh_token(
                refresh_token.id, ray_id
            )
            await storage.access_tokens.revoke(oldest.id, ray_id)
        
        return SuccessResult(ray_id=ray_id, client_message=None)
```

## RFC Compliance

### Refresh Token Flow (RFC 6749 Section 6)

**Request**:
```http
POST /oauth/token HTTP/1.1
Host: server.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=tGzv3JOkF0XG5Qx2TlKWIA
&client_id=s6BhdRkqt3
&client_secret=7Fjfp0ZBr1KtDRbnfVdmIw
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
  "scope": "read write"
}
```

**Error Response**:
```json
{
  "error": "invalid_grant",
  "error_description": "The refresh token is invalid or expired"
}
```

## Flow Diagrams

Visual representations of each flow are available in `ai/flows/`:

- **Refresh Token Flow**: [../../ai/flows/refresh_token_flow.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/flows/refresh_token_flow.md)
- **Authorization Code Flow**: [../../ai/flows/auth_code_flow.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/flows/auth_code_flow.md)
- **Client Credentials Flow**: [../../ai/flows/client_creds_flow.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/flows/client_creds_flow.md)
- **Device Authorization Flow**: [../../ai/flows/device_auth_flow.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/flows/device_auth_flow.md)
- **Resource Owner Password Flow**: [../../ai/flows/resource_owner_credential_flow.md](file:///home/shivam/Desktop/q_scope/q_scope/ai/flows/resource_owner_credential_flow.md)

## Extension Guidelines

### Implementing a New Flow

1. **Create Flow Class**:
   ```python
   from q_scope.implementations.oauth2.templates.base import OAuth2Authorization
   
   class NewFlow(OAuth2Authorization):
       def __init__(self, storage, clock, config, logger):
           super().__init__(storage=storage, clock=clock, config=config, logger=logger)
   ```

2. **Implement Preconditions**:
   ```python
   async def _preconditions(self, context, ray_id):
       chain = ConditionChain([
           ValidateInputCondition(),
           AuthenticateClientCondition(),
           # ... other conditions
       ])
       result = await chain.execute(context=context, ray_id=ray_id)
       if not result.status:
           raise OAuthError(result.error_code, result.client_message)
   ```

3. **Implement Core Logic**:
   ```python
   async def _run(self, context, ray_id):
       # Generate tokens
       access_token = await self._generate_access_token(context)
       refresh_token = await self._generate_refresh_token(context)
       
       return {
           "access_token": access_token,
           "refresh_token": refresh_token,
           "token_type": "Bearer",
           "expires_in": self._config.access_token_ttl
       }
   ```

4. **Implement Postconditions**:
   ```python
   async def _postconditions(self, context, result, ray_id):
       # Persist tokens
       await self._storage.access_tokens.insert(result["access_token"], ray_id)
       await self._storage.refresh_tokens.insert(result["refresh_token"], ray_id)
       
       # Audit log
       await self._audit_log(event="token.issued", ray_id=ray_id)
   ```

5. **Create Flow Diagram**: Add visual representation to `ai/flows/`

6. **Write Tests**: E2E tests with SQLite backend

7. **Document**: Update this file with flow details

## Dependencies

### Internal
- **templates/base**: `OAuth2Authorization`, `Condition`
- **helpers**: `ConditionChain`
- **datastrutures**: Domain models, Result types
- **store**: Storage layer
- **errors**: Error codes

### External
- **oauthlib** (future): RFC-compliant OAuth2 logic

## Testing Strategy

### Unit Tests
- Test individual conditions
- Test token generation
- Test token limit enforcement

### Integration Tests
- Test flow with mocked storage
- Test condition chains
- Test error handling

### E2E Tests
- Full flow with SQLite backend
- RFC compliance tests
- Token lifecycle tests

## Related Documentation

- **OAuth2 Layer**: [../imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/imp.md)
- **Templates**: [../templates/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/templates/imp.md)
- **Helpers**: [../helpers/imp.md](file:///home/shivam/Desktop/q_scope/q_scope/implementations/oauth2/helpers/imp.md)
- **Flow Diagrams**: [../../ai/flows/](file:///home/shivam/Desktop/q_scope/q_scope/ai/flows/)
- **Chat History**: [../../ai/chats/](file:///home/shivam/Desktop/q_scope/q_scope/ai/chats/) - OAuth2 Refresh Token 
---

**Summary**: The OAuth flows layer implements OAuth2 grant types using the Template Method and Condition patterns. Each flow validates input, executes core logic, and persists state following RFC specifications. The Refresh Token Flow is currently in progress, with other flows planned for future implementation.
