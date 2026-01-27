┌─────────┐                                    ┌──────────────────┐
│ Client  │                                    │  OAuth2 Server   │
│  App    │                                    │                  │
│(Service)│                                    │                  │
└────┬────┘                                    └────────┬─────────┘
     │                                                  │
     │  1. POST /oauth/token                            │
     │     grant_type=client_credentials                │
     │     scope=app.service.resource.read              │
     │     client_id=SERVICE_X                          │
     │     client_secret=SECRET                         │
     ├──────────────────────────────────────────────────>
     │                                                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Ray ID Generated         │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Authenticate Client:     │  │
     │                    │ • Fetch from DB          │  │
     │                    │ • Verify secret (bcrypt) │  │
     │                    │ • Check grant_type       │  │
     │                    │   allowed for client     │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Validate Scope:          │  │
     │                    │ • Check length <= 100    │  │
     │                    │ • Check client allowed   │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Generate Access Token:   │  │
     │                    │ JWT {                    │  │
     │                    │   sub: client_id,        │  │
     │                    │   jti: token_id,         │  │
     │                    │   ray_id: xxx            │  │
     │                    │ }                        │  │
     │                    │ Signed with JWT secret   │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Store to Database:       │  │
     │                    │ oauth2_access_tokens     │  │
     │                    │ - token_id               │  │
     │                    │ - access_token (JWT)     │  │
     │                    │ - client_id              │  │
     │                    │ - user_id: NULL          │  │
     │                    │ - scope                  │  │
     │                    │ - refresh_token_id: NULL │  │
     │                    └──────────┬───────────────┘  │
     │                               │                  │
     │                               v                  │
     │                    ┌──────────────────────────┐  │
     │                    │ Audit Log:               │  │
     │                    │ "token.issued"           │  │
     │                    │ grant_type:              │  │
     │                    │   client_credentials     │  │
     │                    └──────────────────────────┘  │
     │                                                  │
     │  2. Response: 200 OK                             │
     │     {                                            │
     │       "access_token": "eyJhbG...",               │
     │       "token_type": "Bearer",                    │
     │       "expires_in": 3600,                        │
     │       "scope": "app.service.resource.read"       │
     │     }                                            │
     │     (No refresh_token for client_credentials)    │
     <───────────────────────────────────────────────────┤
