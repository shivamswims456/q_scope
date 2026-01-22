┌─────────┐              ┌──────────────┐         ┌──────────────────┐
│ Client  │              │  Resource    │         │  OAuth2 Server   │
│  App    │              │  Server/API  │         │   (Database)     │
└────┬────┘              └──────┬───────┘         └────────┬─────────┘
     │                          │                           │
     │  1. GET /api/user/profile                           │
     │     Authorization: Bearer eyJhbGciOiJIUzI1Ni...     │
     ├──────────────────────────>                          │
     │                          │                           │
     │                          │  ┌─────────────────────┐ │
     │                          │  │ Extract JWT from    │ │
     │                          │  │ Authorization header│ │
     │                          │  └──────────┬──────────┘ │
     │                          │             │            │
     │                          │             v            │
     │                          │  ┌─────────────────────┐ │
     │                          │  │ Decode JWT payload  │ │
     │                          │  │ (NO verification yet)│ │
     │                          │  │                     │ │
     │                          │  │ Extracted:          │ │
     │                          │  │ {                   │ │
     │                          │  │   "sub": "user_123",│ │
     │                          │  │   "jti": "tok_456", │ │
     │                          │  │   "ray_id": "789",  │ │
     │                          │  │   "exp": 1735000000,│ │
     │                          │  │   "iat": 1734996400 │ │
     │                          │  │ }                   │ │
     │                          │  └──────────┬──────────┘ │
     │                          │             │            │
     │                          │             v            │
     │                          │  ┌─────────────────────┐ │
     │                          │  │ Query Database      │ │
     │                          │  │ (No Cache in v1.0)  │ │
     │                          │  └──────────┬──────────┘ │
     │                          │             │            │
     │                          │  SELECT * FROM           │
     │                          │  oauth2_access_tokens    │
     │                          │  WHERE token_id='tok_456'│
     │                          │  AND revoked = 0         │
     │                          ├─────────────────────────>│
     │                          │                          │
     │                          │         ┌──────────────┐ │
     │                          │         │ Database     │ │
     │                          │         │ returns:     │ │
     │                          │         │ - client_id  │ │
     │                          │         │ - user_id    │ │
     │                          │         │ - scope      │ │
     │                          │         │ - expires_at │ │
     │                          │         │ - revoked: 0 │ │
     │                          │         └──────┬───────┘ │
     │                          │                │         │
     │                          │  Token metadata          │
     │                          <─────────────────────────┤
     │                          │                          │
     │                          │  ┌─────────────────────┐│
     │                          │  │ IF NOT FOUND:       ││
     │                          │  │ → 401 Unauthorized  ││
     │                          │  │ (token invalid/     ││
     │                          │  │  revoked)           ││
     │                          │  └─────────────────────┘│
     │                          │                          │
     │                          │  ┌─────────────────────┐│
     │                          │  │ Get JWT Secret Key  ││
     │                          │  │ (Global key from env││
     │                          │  │  in v1.0)           ││
     │                          │  └──────────┬──────────┘│
     │                          │             │           │
     │                          │             v           │
     │                          │  ┌─────────────────────┐│
     │                          │  │ Verify JWT Signature││
     │                          │  │ using secret key    ││
     │                          │  │                     ││
     │                          │  │ jwt.verify(         ││
     │                          │  │   token,            ││
     │                          │  │   secret_key,       ││
     │                          │  │   algorithm='HS256' ││
     │                          │  │ )                   ││
     │                          │  └──────────┬──────────┘│
     │                          │             │           │
     │                          │  ┌──────────v──────────┐│
     │                          │  │ IF INVALID:         ││
     │                          │  │ → 401 Unauthorized  ││
     │                          │  │ (tampered token)    ││
     │                          │  └─────────────────────┘│
     │                          │                          │
     │                          │  ┌─────────────────────┐│
     │                          │  │ Check JWT Expiration││
     │                          │  │                     ││
     │                          │  │ if exp < now():     ││
     │                          │  │   → 401 Token       ││
     │                          │  │      Expired        ││
     │                          │  └──────────┬──────────┘│
     │                          │             │           │
     │                          │             v           │
     │                          │  ┌─────────────────────┐│
     │                          │  │ Validate Scopes     ││
     │                          │  │                     ││
     │                          │  │ Required by API:    ││
     │                          │  │   app.users.        ││
     │                          │  │   profile.read      ││
     │                          │  │                     ││
     │                          │  │ Granted (from DB):  ││
     │                          │  │   app.users.ALL.read││
     │                          │  │                     ││
     │                          │  │ ScopeManager.match():││
     │                          │  │   app.users.ALL.read││
     │                          │  │   matches           ││
     │                          │  │   app.users.        ││
     │                          │  │   profile.read ✓    ││
     │                          │  └──────────┬──────────┘│
     │                          │             │           │
     │                          │  ┌──────────v──────────┐│
     │                          │  │ IF SCOPE MISMATCH:  ││
     │                          │  │ → 403 Forbidden     ││
     │                          │  │ "Insufficient scope"││
     │                          │  └─────────────────────┘│
     │                          │                          │
     │                          │  ┌─────────────────────┐│
     │                          │  │ Update last_used_at ││
     │                          │  │ (optional tracking) ││
     │                          │  │                     ││
     │                          │  │ UPDATE              ││
     │                          │  │ oauth2_access_tokens││
     │                          │  │ SET last_used_at =  ││
     │                          │  │   now()             ││
     │                          │  │ WHERE token_id =    ││
     │                          │  │   'tok_456'         ││
     │                          │  └──────────┬──────────┘│
     │                          │             │           │
     │                          ├─────────────────────────>│
     │                          │                          │
     │                          │  ┌─────────────────────┐│
     │                          │  │ Audit Log (async):  ││
     │                          │  │ "token.validated"   ││
     │                          │  │ {                   ││
     │                          │  │   ray_id: "789",    ││
     │                          │  │   token_id: "tok_456││
     │                          │  │   user_id: "user_123││
     │                          │  │   endpoint: "/api/  ││
     │                          │  │     user/profile",  ││
     │                          │  │   result: "success" ││
     │                          │  │ }                   ││
     │                          │  └─────────────────────┘│
     │                          │                          │
     │                          │  ┌─────────────────────┐│
     │                          │  │ Token Valid! ✓      ││
     │                          │  │ Attach user context:││
     │                          │  │ - user_id           ││
     │                          │  │ - client_id         ││
     │                          │  │ - scopes            ││
     │                          │  │ to request          ││
     │                          │  └──────────┬──────────┘│
     │                          │             │           │
     │                          │  Process API request    │
     │                          │  with authenticated     │
     │                          │  user context           │
     │                          │                          │
     │  2. 200 OK                                         │
     │     {                                              │
     │       "user_id": "user_123",                       │
     │       "name": "John Doe",                          │
     │       "email": "john@example.com",                 │
     │       "profile_picture": "..."                     │
     │     }                                              │
     <──────────────────────────┤                          │
     │                          │                          │
     │                                                     │
     
     
═══════════════════════════════════════════════════════════════════
                    VALIDATION FAILURE SCENARIOS
═══════════════════════════════════════════════════════════════════

Scenario A: Token Not Found or Revoked
┌──────────────────────────┐
│ Database returns NULL    │
│ (token doesn't exist or  │
│  revoked = 1)            │
└────────────┬─────────────┘
             │
             v
┌────────────────────────────────────┐
│ Response: 401 Unauthorized         │
│ {                                  │
│   "error": "invalid_token",        │
│   "error_description":             │
│     "Token is invalid or revoked"  │
│ }                                  │
└────────────────────────────────────┘
             │
             v
┌────────────────────────────────────┐
│ Audit Log:                         │
│ "token.validation.failed"          │
│ reason: "token_not_found"          │
└────────────────────────────────────┘


Scenario B: JWT Signature Invalid (Tampered)
┌──────────────────────────┐
│ JWT verification fails   │
│ (signature mismatch)     │
└────────────┬─────────────┘
             │
             v
┌────────────────────────────────────┐
│ Response: 401 Unauthorized         │
│ {                                  │
│   "error": "invalid_token",        │
│   "error_description":             │
│     "Token signature is invalid"   │
│ }                                  │
└────────────────────────────────────┘
             │
             v
┌────────────────────────────────────┐
│ Audit Log (WARNING):               │
│ "token.validation.failed"          │
│ reason: "signature_invalid"        │
│ potential_attack: true             │
└────────────────────────────────────┘


Scenario C: Token Expired
┌──────────────────────────┐
│ JWT exp claim < now()    │
└────────────┬─────────────┘
             │
             v
┌────────────────────────────────────┐
│ Response: 401 Unauthorized         │
│ {                                  │
│   "error": "invalid_token",        │
│   "error_description":             │
│     "Token has expired"            │
│ }                                  │
└────────────────────────────────────┘
             │
             v
┌────────────────────────────────────┐
│ Audit Log:                         │
│ "token.validation.failed"          │
│ reason: "token_expired"            │
│ expired_at: "2024-12-20T10:00:00Z" │
└────────────────────────────────────┘


Scenario D: Insufficient Scope
┌──────────────────────────────────┐
│ Required: app.users.profile.write│
│ Granted:  app.users.profile.read │
│                                  │
│ ScopeManager.match() → False     │
└────────────┬─────────────────────┘
             │
             v
┌────────────────────────────────────┐
│ Response: 403 Forbidden            │
│ {                                  │
│   "error": "insufficient_scope",   │
│   "error_description":             │
│     "Token does not have required  │
│      scope",                       │
│   "scope": "app.users.profile.write│
│ }                                  │
└────────────────────────────────────┘
             │
             v
┌────────────────────────────────────┐
│ Audit Log (WARNING):               │
│ "scope.mismatch"                   │
│ required: "app.users.profile.write"│
│ granted: "app.users.profile.read"  │
│ user_id: "user_123"                │
└────────────────────────────────────┘
