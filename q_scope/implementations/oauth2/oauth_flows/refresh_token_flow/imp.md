# OAuth2 Refresh Token Flow Implementation

## Purpose

The `RefreshTokenFlow` implements the OAuth2 Refresh Token Grant as defined in [RFC 6749 Section 6](https://datatracker.ietf.org/doc/html/rfc6749#section-6). It allows clients to exchange a valid refresh token for a new access token (and optionally a new refresh token).

## Architecture & Implementation

The flow follows the **Template Method** and **Condition Chain** patterns used throughout this framework.

### Class Location
`q_scope.implementations.oauth2.oauth_flows.refresh_token_flow.RefreshTokenFlow`

> [!NOTE]
> The implementation resides in `__init__.py` of the `refresh_token_flow` package to avoid naming conflicts with the directory.

### Public Interface

The main entry point is the `execute` method inherited from `OAuth2Authorization`.

```python
async def execute(self, context: Mapping[str, Any], ray_id: str) -> Mapping[str, Any]:
    """
    Executes the Refresh Token Flow.
    
    Args:
        context: A dictionary containing request parameters:
            - refresh_token (str): The refresh token credential.
            - client_id (str): The client identifier.
            - client_secret (str, optional): The client secret (if confidential).
            - scope (str, optional): Requested scope (must be subset of original).
        ray_id: Unique request identifier for tracing.
        
    Returns:
        dict: The token response containing:
            - access_token
            - token_type
            - expires_in
            - refresh_token (if rotated)
            - scope
            
    Raises:
        OAuthException: If validation fails (invalid_grant, invalid_client, etc.)
    """
```

## Logic Flow

The execution is divided into three stages:

### 1. Preconditions (Validation)
Methods: `_preconditions`

A `ConditionChain` executes the following validators in order:
1.  **ValidateRefreshTokenPresenceCondition**: Ensures `refresh_token` is in the request.
2.  **AuthenticateClientCondition**:
    -   Validates `client_id` exists.
    -   Authenticates `client_secret` if the client is confidential.
    -   Loads `client_obj` and `client_config` into context.
3.  **ValidateRefreshTokenCondition**:
    -   Check if token exists in storage.
    -   Check if token is revoked.
    -   Check if token belongs to the authenticated client.
4.  **CheckAccessTokenLimitCondition**:
    -   Enforces `max_active_access_tokens` policy (FIFO revocation) if configured.

### 2. Run (Execution)
Method: `_run`

1.  **Scope Validation**:
    -   If `scope` is requested, verify it is a subset of the original refresh token's scopes.
    -   Rejects superset requests with `invalid_scope`.
2.  **Token Generation**:
    -   Generates a new `access_token` (UUID).
    -   Determines `expires_in` from client config.
3.  **Rotation Logic**:
    -   If `config.rotate_refresh_tokens` is True, generates a new `refresh_token`.
    -   Otherwise, reuses the existing one.

### 3. Postconditions (Persistence)
Method: `_postconditions`

1.  **Persist Access Token**: Saves the new token to `AccessTokenStore`.
2.  **Handle Refresh Token**:
    -   **If Rotated**: Revokes the old refresh token and persists the new one.
    -   **If Reused**: Updates the `updated_at` timestamp of the existing token.
3.  **Audit Logging**:
    -   Records `token.issued` event with metadata about rotation.

## Storage Dependencies

The flow relies on `self._storage` implementing the following repositories:
-   `clients`: `ClientStore` (get by identifier)
-   `client_configs`: `ClientConfigStore` (get by client id)
-   `refresh_tokens`: `RefreshTokenStore` (get, insert, update)
-   `access_tokens`: `AccessTokenStore` (insert, count/get_oldest for limits)
-   `audit_logs`: `AuditLogStore` (insert)

## Error Handling

All validation errors are raised as `OAuthException` with standard OAuth2 error codes:
-   `invalid_request`: Missing parameters.
-   `invalid_client`: Authentication failed.
-   `invalid_grant`: Token invalid, revoked, or ownership mismatch.
-   `invalid_scope`: Requested scope exceeds original scope.
-   `server_error`: Configuration issues.

## Compliance
-   **RFC 6749 Section 6**: Fully implemented.
-   **Security**:
    -   Rotated refresh tokens (optional).
    -   Scope downsizing supported.
    -   Revoked token detection.
    -   FIFO access token limits to prevent abuse.
