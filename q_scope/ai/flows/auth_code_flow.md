┌─────────┐                                    ┌──────────────────┐
│  User   │                                    │  OAuth2 Server   │
│ Browser │                                    │                  │
└────┬────┘                                    └────────┬─────────┘
     │                                                  │
     │  1. GET /oauth/authorize                         │
     │     ?client_id=X&redirect_uri=Y                  │
     │     &scope=read&code_challenge=ABC               │
     ├─────────────────────────────────────────────────>
     │                                                  │
     │                    ┌──────────────────────────┐  │
     │                    │  Ray ID Generated        │  │
     │                    │  (Sonyflake)             │  │
     │                    └──────────────────────────┘  │
     │                                                  │
     │                    ┌──────────────────────────┐  │
     │  2. Check Auth     │ Implementor Middleware   │  │
     │    <──────────────>│ UserContext?             │  │
     │                    └──────────────────────────┘  │
     │                                                  │
     │  ┌─ If Not Authenticated ─────────────────────┐  │
     │  │ 3. Redirect to /login?next=/oauth/authorize│  │
     │  <───────────────────────────────────────────────┤
     │  │ 4. User logs in                             │ │
     │  ├─────────────────────────────────────────────> │
     │  │ 5. Redirect back with session               │ │
     │  <──────────────────────────────────────────────┤
     │  └──────────────────────────────────────────────┘│
     │                                                  │
     │                    ┌──────────────────────────┐  │
     │  6. Validate       │ • Check client_id        │  │
     │     Request        │ • Check redirect_uri     │  │
     │                    │ • Validate scope         │  │
     │                    │ • Verify PKCE challenge  │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │  Store to Database:      │  │
     │                    │  oauth2_authorization_   │  │
     │                    │  requests                │  │
     │                    │  - request_id            │  │
     │                    │  - consent_token         │  │
     │                    │  - client_id, user_id    │  │
     │                    │  - scope, code_challenge │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │  Audit Log:              │  │
     │                    │  "authorization.         │  │
     │                    │   initiated"             │  │
     │                    └──────────────────────────┘  │
     │                                                  │
     │  7. Redirect to /oauth/consent                   │
     │     ?token={consent_token}                       │
     <──────────────────────────────────────────────────┤
     │                                                  │
     │  8. GET /oauth/consent?token=XYZ                 │
     ├─────────────────────────────────────────────────>
     │                                                  │
     │                    ┌──────────────────────────┐  │
     │  9. Render         │ ConsentRenderer callback │  │
     │     Consent UI     │ or default template      │  │
     │                    │ Shows: client name,      │  │
     │                    │        scopes requested  │  │
     │                    └──────────────────────────┘  │
     │                                                  │
     │  10. HTML Consent Page                           │
     │      [Approve] [Deny]                            │
     <──────────────────────────────────────────────────┤
     │                                                  │
     │  11. POST /oauth/consent/callback                │
     │      {consent_token: XYZ, approved: true}        │
     ├─────────────────────────────────────────────────>
     │                                                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Generate authorization   │  │
     │                    │ code                     │  │
     │                    │                          │  │
     │                    │ Store to Database:       │  │
     │                    │ oauth2_authorization_    │  │
     │                    │ codes                    │  │
     │                    │ - code                   │  │
     │                    │ - client_id, user_id     │  │
     │                    │ - redirect_uri, scope    │  │
     │                    │ - code_challenge         │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Audit Log:               │  │
     │                    │ "authorization.granted"  │  │
     │                    └──────────────────────────┘  │
     │                                                  │
     │  12. Redirect to {redirect_uri}                  │
     │      ?code=AUTH_CODE&state=CLIENT_STATE          │
     <──────────────────────────────────────────────────┤
     │                                                  │
┌────┴────┐                                    ┌────────┴─────────┐
│ Client  │                                    │  OAuth2 Server   │
│  App    │                                    │                  │
└────┬────┘                                    └────────┬─────────┘
     │                                                  │
     │  13. POST /oauth/token                           │
     │      grant_type=authorization_code               │
     │      code=AUTH_CODE                              │
     │      code_verifier=VERIFIER (PKCE)               │
     │      client_id=X                                 │
     │      client_secret=SECRET                        │
     ├──────────────────────────────────────────────────>
     │                                                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Authenticate Client:     │  │
     │                    │ - Verify client_secret   │  │
     │                    │   (bcrypt compare)       │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Validate Code:           │  │
     │                    │ - Check not expired      │  │
     │                    │ - Check not used         │  │
     │                    │ - Verify PKCE            │  │
     │                    │   (code_challenge ==     │  │
     │                    │    hash(code_verifier))  │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Generate Tokens:         │  │
     │                    │ - access_token (JWT)     │  │
     │                    │   {sub, jti, ray_id}     │  │
     │                    │ - refresh_token (random) │  │
     │                    │ - token_id (unique)      │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Check Token Limits:      │  │
     │                    │ • Refresh tokens for     │  │
     │                    │   user+client >= N?      │  │
     │                    │   → Revoke oldest (FIFO) │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Store to Database:       │  │
     │                    │                          │  │
     │                    │ oauth2_access_tokens:    │  │
     │                    │ - token_id, access_token │  │
     │                    │ - client_id, user_id     │  │
     │                    │ - scope, expires_at      │  │
     │                    │ - refresh_token_id       │  │
     │                    │                          │  │
     │                    │ oauth2_refresh_tokens:   │  │
     │                    │ - token_id, refresh_token│  │
     │                    │ - client_id, user_id     │  │
     │                    │ - scope                  │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Mark code as used        │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Audit Log:               │  │
     │                    │ "token.issued"           │  │
     │                    └──────────────────────────┘  │
     │                                                  │
     │  14. Response: 200 OK                            │
     │      {                                           │
     │        "access_token": "eyJhbG...",              │
     │        "token_type": "Bearer",                   │
     │        "expires_in": 3600,                       │
     │        "refresh_token": "def502...",             │
     │        "scope": "app.users.profile.read"         │
     │      }                                           │
     <──────────────────────────────────────────────────┤                                                  
