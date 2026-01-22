┌─────────┐                                    ┌──────────────────┐
│ Client  │                                    │  OAuth2 Server   │
│  App    │                                    │                  │
└────┬────┘                                    └────────┬─────────┘
     │                                                   │
     │  ⚠️  DEPRECATED FLOW - SECURITY WARNING ⚠️       │
     │  Only enabled if allow_password_grant = True     │
     │                                                   │
     │  ┌────────────────────────────────────────────┐  │
     │  │ User enters credentials directly in client │  │
     │  │ app (NOT on OAuth server's page)           │  │
     │  │                                            │  │
     │  │ Username: john@example.com                 │  │
     │  │ Password: ••••••••                         │  │
     │  │                                            │  │
     │  │ [Login Button]                             │  │
     │  └────────────────────────────────────────────┘  │
     │                                                   │
     │  1. POST /oauth/token                            │
     │     grant_type=password                          │
     │     username=john@example.com                    │
     │     password=secretpassword123                   │
     │     scope=app.users.profile.read                 │
     │     client_id=MOBILE_APP                         │
     │     client_secret=SECRET                         │
     ├──────────────────────────────────────────────────>
     │                                                   │
     │                    ┌──────────────────────────┐  │
     │                    │ Ray ID Generated         │  │
     │                    │ (Sonyflake)              │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ ⚠️  Log Warning:         │  │
     │                    │ "password_grant.used"    │  │
     │                    │ level: WARNING           │  │
     │                    │ message: "Deprecated     │  │
     │                    │  password grant type     │  │
     │                    │  used. Consider migrating│  │
     │                    │  to authorization_code   │  │
     │                    │  flow."                  │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Check Grant Enabled:     │  │
     │                    │                          │  │
     │                    │ if not settings.         │  │
     │                    │   allow_password_grant:  │  │
     │                    │   → 400 Bad Request      │  │
     │                    │   "unsupported_grant_    │  │
     │                    │    type"                 │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Authenticate Client:     │  │
     │                    │ • Fetch client from DB   │  │
     │                    │ • Verify client_secret   │  │
     │                    │   (bcrypt compare)       │  │
     │                    │ • Check 'password' in    │  │
     │                    │   client.grant_types     │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                    ┌──────────v───────────────┐  │
     │                    │ IF CLIENT AUTH FAILS:    │  │
     │                    │ → 401 Unauthorized       │  │
     │                    │   "invalid_client"       │  │
     │                    │                          │  │
     │                    │ Audit Log:               │  │
     │                    │ "client.auth.failed"     │  │
     │                    └──────────────────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Authenticate User:       │  │
     │                    │ (Call implementor's      │  │
     │                    │  UserStore)              │  │
     │                    │                          │  │
     │                    │ user = await storage.    │  │
     │                    │   users.authenticate_user│  │
     │                    │     (username, password) │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Query Database:          │  │
     │                    │                          │  │
     │                    │ SELECT * FROM            │  │
     │                    │ oauth2_users             │  │
     │                    │ WHERE username = ?       │  │
     │                    │   AND is_active = 1      │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Verify Password:         │  │
     │                    │                          │  │
     │                    │ bcrypt.verify(           │  │
     │                    │   password,              │  │
     │                    │   user.password_hash     │  │
     │                    │ )                        │  │
     │                    │                          │  │
     │                    │ Uses constant-time       │  │
     │                    │ comparison for security  │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                    ┌──────────v───────────────┐  │
     │                    │ IF USER AUTH FAILS:      │  │
     │                    │ → 400 Bad Request        │  │
     │                    │   "invalid_grant"        │  │
     │                    │   "Invalid username or   │  │
     │                    │    password"             │  │
     │                    │                          │  │
     │                    │ Audit Log (WARNING):     │  │
     │                    │ "user.auth.failed"       │  │
     │                    │ username: "john@..."     │  │
     │                    │ ip_address: "1.2.3.4"    │  │
     │                    │ (potential brute force)  │  │
     │                    └──────────────────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ ✓ User Authenticated     │  │
     │                    │                          │  │
     │                    │ User: {                  │  │
     │                    │   user_id: "user_123",   │  │
     │                    │   username: "john@...",  │  │
     │                    │   email: "..."           │  │
     │                    │ }                        │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Validate Scope:          │  │
     │                    │ • Check length <= 100    │  │
     │                    │ • Check user has access  │  │
     │                    │   to requested scopes    │  │
     │                    │   (implementor's logic)  │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                    ┌──────────v───────────────┐  │
     │                    │ IF SCOPE INVALID:        │  │
     │                    │ → 400 Bad Request        │  │
     │                    │   "invalid_scope"        │  │
     │                    └──────────────────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Generate Tokens:         │  │
     │                    │                          │  │
     │                    │ access_token = JWT {     │  │
     │                    │   sub: "user_123",       │  │
     │                    │   jti: "tok_abc123",     │  │
     │                    │   ray_id: "ray_xyz",     │  │
     │                    │   exp: now + 3600,       │  │
     │                    │   iat: now               │  │
     │                    │ }                        │  │
     │                    │ Signed with JWT secret   │  │
     │                    │                          │  │
     │                    │ refresh_token = random   │  │
     │                    │   secure string          │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Check Refresh Token      │  │
     │                    │ Limits:                  │  │
     │                    │                          │  │
     │                    │ Count refresh tokens for │  │
     │                    │ (user_id + client_id)    │  │
     │                    │                          │  │
     │                    │ SELECT COUNT(*) FROM     │  │
     │                    │ oauth2_refresh_tokens    │  │
     │                    │ WHERE user_id = ?        │  │
     │                    │   AND client_id = ?      │  │
     │                    │   AND revoked = 0        │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ IF count >= N (e.g., 5): │  │
     │                    │                          │  │
     │                    │ Revoke Oldest (FIFO):    │  │
     │                    │ • Get oldest by          │  │
     │                    │   created_at             │  │
     │                    │ • UPDATE revoked = 1     │  │
     │                    │ • revocation_reason =    │  │
     │                    │   'fifo_limit'           │  │
     │                    │ • CASCADE revoke all     │  │
     │                    │   child access tokens    │  │
     │                    │                          │  │
     │                    │ Audit Log:               │  │
     │                    │ "refresh_token.          │  │
     │                    │  auto_revoked"           │  │
     │                    │ reason: "fifo_limit"     │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Store Tokens to Database:│  │
     │                    │                          │  │
     │                    │ INSERT INTO              │  │
     │                    │ oauth2_refresh_tokens:   │  │
     │                    │ - token_id               │  │
     │                    │ - refresh_token          │  │
     │                    │ - client_id, user_id     │  │
     │                    │ - scope                  │  │
     │                    │ - ray_id                 │  │
     │                    │ - created_at             │  │
     │                    │                          │  │
     │                    │ INSERT INTO              │  │
     │                    │ oauth2_access_tokens:    │  │
     │                    │ - token_id               │  │
     │                    │ - access_token (JWT)     │  │
     │                    │ - client_id, user_id     │  │
     │                    │ - scope                  │  │
     │                    │ - refresh_token_id       │  │
     │                    │ - ray_id                 │  │
     │                    │ - expires_at             │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Audit Log:               │  │
     │                    │ "token.issued"           │  │
     │                    │ {                        │  │
     │                    │   grant_type: "password",│  │
     │                    │   user_id: "user_123",   │  │
     │                    │   client_id: "MOBILE_APP"│  │
     │                    │   scope: "app.users.     │  │
     │                    │     profile.read",       │  │
     │                    │   ray_id: "ray_xyz",     │  │
     │                    │   warning: "deprecated_  │  │
     │                    │     grant_type"          │  │
     │                    │ }                        │  │
     │                    └──────────────────────────┘  │
     │                                                   │
     │  2. Response: 200 OK                             │
     │     {                                            │
     │       "access_token": "eyJhbGciOiJIUzI1Ni...",   │
     │       "token_type": "Bearer",                    │
     │       "expires_in": 3600,                        │
     │       "refresh_token": "def50200abc...",         │
     │       "scope": "app.users.profile.read"          │
     │     }                                            │
     <───────────────────────────────────────────────────┤
     │                                                   │
     │  Client stores tokens and can now make API calls │
     │                                                   │


═══════════════════════════════════════════════════════════════════
                    ERROR SCENARIOS
═══════════════════════════════════════════════════════════════════

Scenario A: Grant Type Not Enabled
┌────────────────────────────────────────┐
│ OAuth2Settings:                        │
│   allow_password_grant = False         │
└──────────────┬─────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Response: 400 Bad Request              │
│ {                                      │
│   "error": "unsupported_grant_type",   │
│   "error_description":                 │
│     "Password grant type is disabled.  │
│      This grant type is deprecated.    │
│      Please use authorization_code     │
│      flow instead."                    │
│ }                                      │
└────────────────────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Audit Log (WARNING):                   │
│ "password_grant.rejected"              │
│ reason: "grant_type_disabled"          │
│ client_id: "MOBILE_APP"                │
└────────────────────────────────────────┘


Scenario B: Invalid Client Credentials
┌────────────────────────────────────────┐
│ Client secret verification failed      │
│ (bcrypt.verify() returns False)        │
└──────────────┬─────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Response: 401 Unauthorized             │
│ {                                      │
│   "error": "invalid_client",           │
│   "error_description":                 │
│     "Client authentication failed"     │
│ }                                      │
└────────────────────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Audit Log (WARNING):                   │
│ "client.auth.failed"                   │
│ client_id: "MOBILE_APP"                │
│ auth_method: "client_secret_post"      │
│ ray_id: "ray_xyz"                      │
└────────────────────────────────────────┘


Scenario C: Invalid User Credentials
┌────────────────────────────────────────┐
│ User not found OR                      │
│ Password verification failed           │
└──────────────┬─────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Response: 400 Bad Request              │
│ {                                      │
│   "error": "invalid_grant",            │
│   "error_description":                 │
│     "The provided username or password │
│      is incorrect"                     │
│ }                                      │
│                                        │
│ Note: Generic message to prevent       │
│ username enumeration attacks           │
└────────────────────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Audit Log (WARNING):                   │
│ "user.auth.failed"                     │
│ username: "john@example.com"           │
│ client_id: "MOBILE_APP"                │
│ ip_address: "192.168.1.100"            │
│ ray_id: "ray_xyz"                      │
│ grant_type: "password"                 │
│                                        │
│ Security Note: Monitor for brute force │
└────────────────────────────────────────┘


Scenario D: Client Not Allowed Password Grant
┌────────────────────────────────────────┐
│ Client exists BUT                      │
│ 'password' NOT in client.grant_types   │
└──────────────┬─────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Response: 401 Unauthorized             │
│ {                                      │
│   "error": "unauthorized_client",      │
│   "error_description":                 │
│     "This client is not authorized to  │
│      use the password grant type"      │
│ }                                      │
└────────────────────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Audit Log (WARNING):                   │
│ "client.unauthorized_grant"            │
│ client_id: "MOBILE_APP"                │
│ attempted_grant: "password"            │
│ allowed_grants: ["authorization_code"] │
└────────────────────────────────────────┘


Scenario E: User Account Inactive
┌────────────────────────────────────────┐
│ User found BUT is_active = 0           │
└──────────────┬─────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Response: 400 Bad Request              │
│ {                                      │
│   "error": "invalid_grant",            │
│   "error_description":                 │
│     "User account is inactive"         │
│ }                                      │
└────────────────────────────────────────┘
               │
               v
┌────────────────────────────────────────┐
│ Audit Log (WARNING):                   │
│ "user.auth.blocked"                    │
│ reason: "account_inactive"             │
│ user_id: "user_123"                    │
└────────────────────────────────────────┘
