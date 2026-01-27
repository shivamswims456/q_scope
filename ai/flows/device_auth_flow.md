┌─────────┐         ┌─────────┐              ┌──────────────────┐
│ Device  │         │  User   │              │  OAuth2 Server   │
│  (TV)   │         │ Browser │              │                  │
└────┬────┘         └────┬────┘              └────────┬─────────┘
     │                   │                            │
     │  1. POST /oauth/device_authorization           │
     │     client_id=TV_APP                           │
     │     scope=app.video.play                       │
     ├───────────────────────────────────────────────>
     │                                                │
     │                   ┌──────────────────────────┐ │
     │                   │ Generate:                │ │
     │                   │ - device_code (random)   │ │
     │                   │ - user_code (8 chars)    │ │
     │                   │ - verification_uri       │ │
     │                   └──────────┬───────────────┘ │
     │                              │                 │
     │                              v                 │
     │                   ┌──────────────────────────┐ │
     │                   │ Store to Database:       │ │
     │                   │ oauth2_device_codes      │ │
     │                   │ - device_code            │ │
     │                   │ - user_code (uppercase)  │ │
     │                   │ - client_id              │ │
     │                   │ - scope                  │ │
     │                   │ - status: pending        │ │
     │                   │ - interval: 5            │ │
     │                   └──────────┬───────────────┘ │
     │                              │                 │
     │                              v                 │
     │                   ┌──────────────────────────┐ │
     │                   │ Audit Log:               │ │
     │                   │ "device.code.created"    │ │
     │                   └──────────────────────────┘ │
     │                                                │
     │  2. Response: 200 OK                           │
     │     {                                          │
     │       "device_code": "abc123...",              │
     │       "user_code": "ABCDEFGH",                 │
     │       "verification_uri":                      │
     │         "https://example.com/device",          │
     │       "expires_in": 1800,                      │
     │       "interval": 5                            │
     │     }                                          │
     <────────────────────────────────────────────────┤
     │                                                │
     │  3. Display to User:                           │
     │     "Go to https://example.com/device"         │
     │     "Enter code: ABCDEFGH"                     │
     │                                                │
     │                   │                            │
     │                   │  4. User visits            │
     │                   │     verification_uri       │
     │                   ├────────────────────────────>
     │                   │                            │
     │                   │5. GET /oauth/device/verify │
     │                   ├────────────────────────────>
     │                   │                            │
     │                   │         ┌─────────────────┐│
     │                   │         │ Render UI:      ││
     │                   │         │ "Enter code"    ││
     │                   │         └─────────┬───────┘│
     │                   │                   │        │
     │                   │  6. HTML Form     │        │
     │                   <────────────────────────────┤
     │                   │                            │
     │                   │  7. User enters: ABCDEFGH  │
     │                   │                            │
     │                   │8. POST /device/verify-code │
     │                   │     {user_code: "ABCDEFGH"}│
     │                   ├────────────────────────────>
     │                   │                            │
     │                   │         ┌─────────────────┐│
     │                   │         │ Check Auth      ││
     │                   │         │ (User logged in?)│
     │                   │<───────>│ If not,         ││
     │                   │         │ redirect login  ││
     │                   │         └─────────┬───────┘│
     │                   │                   │        │
     │                   │         ┌─────────────────┐│
     │                   │         │ Validate code:  ││
     │                   │         │ - Find in DB    ││
     │                   │         │ - Check valid   ││
     │                   │         │ - Check pending ││
     │                   │         └─────────┬───────┘│
     │                   │                   │        │
     │                   │  9. Show consent page      │
     │                   │     "Allow TV_APP access?" │
     │                   <────────────────────────────┤
     │                   │                            │
     │                   │  10. User clicks "Approve" │
     │                   │                            │
     │                   │11. POST /device/authorize  │
     │                   │  {user_code: "ABCDEFGH",   │
     │                   │       approved: true}      │
     │                   ├────────────────────────────>
     │                   │                             │
     │                   │         ┌─────────────────┐ │
     │                   │         │ Update Database:│ │
     │                   │         │ - status:       │ │
     │                   │         │   authorized    │ │
     │                   │         │ - user_id: XXX  │ │
     │                   │         │ - authorized_at │ │
     │                   │         └─────────┬───────┘ │
     │                   │                   │         │
     │                   │         ┌─────────────────┐ │
     │                   │         │ Audit Log:      │ │
     │                   │         │ "device.        │ │
     │                   │         │  authorized"    │ │
     │                   │         └─────────────────┘ │
     │                   │                             │
     │                   │  12. "Success! Return to    │
     │                   │       your device"          │
     │                   <─────────────────────────────┤
     │                   │                             │
     │                                                 │
     │  [Meanwhile, device is polling...]              │
     │                                                 │
     │  13. POST /oauth/token (poll #1)                │
     │      grant_type=                                │
     │        urn:ietf:params:oauth:grant-type:        │
     │        device_code                              │
     │      device_code=abc123...                      │
     │      client_id=TV_APP                           │
     ├────────────────────────────────────────────────>
     │                                                 │
     │                   ┌──────────────────────────┐  │
     │                   │ Check status in DB:      │  │
     │                   │ status = pending         │  │
     │                   └──────────┬───────────────┘  │
     │                              │                  │
     │  14. Response: 400                              │
     │      {error: "authorization_pending"}           │
     <─────────────────────────────────────────────────┤
     │                                                 │
     │  [Wait 5 seconds (interval)...]                 │
     │                                                 │
     │  15. POST /oauth/token (poll #2)                │
     │      [same as poll #1]                          │
     ├─────────────────────────────────────────────────>
     │                                                 │
     │                   ┌──────────────────────────┐  │
     │                   │ Check status in DB:      │  │
     │                   │ status = authorized ✓    │  │
     │                   └──────────┬───────────────┘  │
     │                              │                  │
     │                              v                  │
     │                   ┌──────────────────────────┐  │
     │                   │ Generate Tokens:         │  │
     │                   │ - access_token (JWT)     │  │
     │                   │ - refresh_token          │  │
     │                   └──────────┬───────────────┘  │
     │                              │                  │
     │                              v                  │
     │                   ┌──────────────────────────┐  │
     │                   │ Store tokens to DB       │  │
     │                   │ Mark device_code used    │  │
     │                   └──────────┬───────────────┘  │
     │                              │                  │
     │                              v                  │
     │                   ┌──────────────────────────┐  │
     │                   │ Audit Log:               │  │
     │                   │ "token.issued"           │  │
     │                   │ "device.code.consumed"   │  │
     │                   └──────────────────────────┘  │
     │                                                 │
     │  16. Response: 200 OK                           │
     │      {                                          │
     │        "access_token": "eyJhbG...",             │
     │        "token_type": "Bearer",                  │
     │        "expires_in": 3600,                      │
     │        "refresh_token": "def502...",            │
     │        "scope": "app.video.play"                │
     │      }                                          │
     <─────────────────────────────────────────────────┤
     │                                                 │
     │  Device is now authenticated!                   │
     │                                                 │
