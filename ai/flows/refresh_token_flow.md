┌─────────┐                                    ┌──────────────────┐
│ Client  │                                    │  OAuth2 Server   │
│  App    │                                    │                  │
└────┬────┘                                    └────────┬─────────┘
     │                                                  │
     │  1. POST /oauth/token                            │
     │     grant_type=refresh_token                     │
     │     refresh_token=def502...                      │
     │     client_id=X                                  │
     │     client_secret=SECRET                         │
     ├─────────────────────────────────────────────────>
     │                                                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Ray ID Generated         │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Authenticate Client      │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Validate Refresh Token:  │  │
     │                    │ • Query from DB          │  │
     │                    │ • Check not revoked      │  │
     │                    │ • Verify client_id match │  │
     │                    │ • Update last_used_at    │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Check Access Token Limit:│  │
     │                    │ • Count tokens for this  │  │
     │                    │   refresh_token_id       │  │
     │                    │ • If >= M tokens:        │  │
     │                    │   → Revoke oldest access │  │
     │                    │      token (FIFO)        │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Generate New Access      │  │
     │                    │ Token (JWT)              │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Store to Database:       │  │
     │                    │ oauth2_access_tokens     │  │
     │                    │ - new token_id           │  │
     │                    │ - access_token (JWT)     │  │
     │                    │ - refresh_token_id: XYZ  │  │
     │                    │   (parent relationship)  │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Audit Log:               │  │
     │                    │ "token.issued"           │  │
     │                    │ "refresh_token.used"     │  │
     │                    └──────────────────────────┘  │
     │                                                  │
     │  2. Response: 200 OK                             │
     │     {                                            │
     │       "access_token": "eyJhbG...",               │
     │       "token_type": "Bearer",                    │
     │       "expires_in": 3600,                        │
     │       "refresh_token": "def502...",              │
     │       "scope": "app.users.profile.read"          │
     │     }                                            │
     <──────────────────────────────────────────────────┤
                                                        
