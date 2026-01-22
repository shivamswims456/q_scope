┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│                           OAUTH2 DATABASE SCHEMA                                │
│                        (SQLite/Turso Implementation)                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────┐
│        oauth2_clients                │
├──────────────────────────────────────┤
│ PK  client_id             TEXT       │◄───────────┐
│     client_secret_hash    TEXT       │            │
│     client_name           TEXT       │            │
│     redirect_uris         TEXT       │            │ One-to-Many
│     grant_types           TEXT       │            │
│     response_types        TEXT       │            │
│     scope                 TEXT       │            │
│     token_endpoint_       TEXT       │            │
│       auth_method                    │            │
│     is_confidential       INTEGER    │            │
│     require_pkce          INTEGER    │            │
│     created_at            TEXT       │            │
│     updated_at            TEXT       │            │
└──────────────────────────────────────┘            │
                                                    │
                                                    │
┌──────────────────────────────────────┐            │
│     oauth2_refresh_tokens            │            │
├──────────────────────────────────────┤            │
│ PK  id                    INTEGER    │            │
│ UK  token_id              TEXT       │◄───────────┼────────┐
│ UK  refresh_token         TEXT       │            │        │
│ FK  client_id             TEXT       │────────────┘        │
│ FK  user_id               TEXT       │────────────┐        │ One-to-Many
│     scope                 TEXT       │            │        │
│     ray_id                TEXT       │            │        │
│     created_at            TEXT       │            │        │
│     last_used_at          TEXT       │            │        │
│     revoked               INTEGER    │            │        │
│     revoked_at            TEXT       │            │        │
│     revoked_by            TEXT       │            │        │
│     revocation_reason     TEXT       │            │        │
└──────────────────────────────────────┘            │        │
                                                    │        │
                                                    │        │
┌──────────────────────────────────────┐            │        │
│      oauth2_access_tokens            │            │        │
├──────────────────────────────────────┤            │        │
│ PK  id                    INTEGER    │            │        │
│ UK  token_id              TEXT       │            │        │
│ UK  access_token          TEXT       │            │        │
│     token_type            TEXT       │            │        │
│     scope                 TEXT       │            │        │
│ FK  client_id             TEXT       │────────────┘        │
│ FK  user_id               TEXT       │────────────┐        │
│ FK  refresh_token_id      TEXT       │────────────┼────────┘
│     ray_id                TEXT       │            │
│     created_at            TEXT       │            │
│     expires_at            TEXT       │            │
│     last_used_at          TEXT       │            │
│     revoked               INTEGER    │            │
│     revoked_at            TEXT       │            │
│     revoked_by            TEXT       │            │
└──────────────────────────────────────┘            │
                                                    │
                                                    │
┌──────────────────────────────────────┐            │
│   oauth2_authorization_codes         │            │
├──────────────────────────────────────┤            │
│ PK  id                    INTEGER    │            │
│ UK  code                  TEXT       │            │
│ FK  client_id             TEXT       │────────────┼────────┐
│ FK  user_id               TEXT       │────────────┤        │
│     redirect_uri          TEXT       │            │        │
│     scope                 TEXT       │            │        │
│     code_challenge        TEXT       │            │        │
│     code_challenge_       TEXT       │            │        │
│       method                         │            │        │
│     expires_at            TEXT       │            │        │
│     used                  INTEGER    │            │        │
│     created_at            TEXT       │            │        │
└──────────────────────────────────────┘            │        │
                                                    │        │
                                                    │        │
┌──────────────────────────────────────┐            │        │
│  oauth2_authorization_requests       │            │        │
├──────────────────────────────────────┤            │        │
│ PK  id                    INTEGER    │            │        │
│ UK  request_id            TEXT       │            │        │
│ UK  consent_token         TEXT       │            │        │
│ FK  client_id             TEXT       │────────────┼────────┘
│ FK  user_id               TEXT       │────────────┤
│     scope                 TEXT       │            │
│     state                 TEXT       │            │
│     redirect_uri          TEXT       │            │
│     code_challenge        TEXT       │            │
│     code_challenge_       TEXT       │            │
│       method                         │            │
│     response_type         TEXT       │            │
│     status                TEXT       │            │
│     nonce                 TEXT       │            │
│     created_at            TEXT       │            │
│     expires_at            TEXT       │            │
└──────────────────────────────────────┘            │
                                                    │
                                                    │
┌──────────────────────────────────────┐            │
│      oauth2_device_codes             │            │
├──────────────────────────────────────┤            │
│ PK  id                    INTEGER    │            │
│ UK  device_code           TEXT       │            │
│ UK  user_code             TEXT       │            │
│ FK  client_id             TEXT       │────────────┼────────┐
│ FK  user_id               TEXT       │────────────┤        │
│     scope                 TEXT       │            │        │
│     expires_at            TEXT       │            │        │
│     interval              INTEGER    │            │        │
│     status                TEXT       │            │        │
│     created_at            TEXT       │            │        │
│     authorized_at         TEXT       │            │        │
└──────────────────────────────────────┘            │        │
                                                    │        │
                                                    │        │
┌──────────────────────────────────────┐            │        │
│         oauth2_users                 │            │        │
├──────────────────────────────────────┤            │        │
│ PK  user_id               TEXT       │◄───────────┴────────┘
│ UK  username              TEXT       │
│     password_hash         TEXT       │
│     email                 TEXT       │
│     is_active             INTEGER    │
│     created_at            TEXT       │
│     updated_at            TEXT       │
└──────────────────────────────────────┘


════════════════════════════════════════════════════════════════════
                      SEPARATE AUDIT DATABASE
════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────┐
│           audit_logs                 │
├──────────────────────────────────────┤
│ PK  id                    INTEGER    │
│     ray_id                TEXT       │  ← Correlation with main DB
│     timestamp             TEXT       │
│     level                 TEXT       │  (INFO/WARNING/ERROR)
│     event_type            TEXT       │  (e.g., "token.issued")
│     user_id               TEXT       │  (nullable)
│     client_id             TEXT       │  (nullable)
│     details               TEXT       │  (JSON blob)
│     ip_address            TEXT       │  (optional)
│     user_agent            TEXT       │  (optional)
└──────────────────────────────────────┘

Indexes:
- idx_audit_ray_id         ON ray_id
- idx_audit_timestamp      ON timestamp
- idx_audit_event_type     ON event_type
- idx_audit_user_id        ON user_id
- idx_audit_client_id      ON client_id


════════════════════════════════════════════════════════════════════
                        RELATIONSHIP SUMMARY
════════════════════════════════════════════════════════════════════

oauth2_clients (1) ──────────< (N) oauth2_refresh_tokens
    One client can have many refresh tokens

oauth2_clients (1) ──────────< (N) oauth2_access_tokens
    One client can have many access tokens

oauth2_clients (1) ──────────< (N) oauth2_authorization_codes
    One client can have many authorization codes

oauth2_clients (1) ──────────< (N) oauth2_authorization_requests
    One client can have many authorization requests

oauth2_clients (1) ──────────< (N) oauth2_device_codes
    One client can have many device codes

oauth2_users (1) ────────────< (N) oauth2_refresh_tokens
    One user can have many refresh tokens

oauth2_users (1) ────────────< (N) oauth2_access_tokens
    One user can have many access tokens

oauth2_users (1) ────────────< (N) oauth2_authorization_codes
    One user can have many authorization codes

oauth2_users (1) ────────────< (N) oauth2_authorization_requests
    One user can have many authorization requests

oauth2_users (1) ────────────< (N) oauth2_device_codes
    One user can have many device codes

oauth2_refresh_tokens (1) ───< (N) oauth2_access_tokens
    One refresh token can create many access tokens
    (Parent-child relationship for token rotation)


════════════════════════════════════════════════════════════════════
                          CONSTRAINTS
════════════════════════════════════════════════════════════════════

PRIMARY KEYS (PK):
├─ oauth2_clients.client_id
├─ oauth2_refresh_tokens.id
├─ oauth2_access_tokens.id
├─ oauth2_authorization_codes.id
├─ oauth2_authorization_requests.id
├─ oauth2_device_codes.id
├─ oauth2_users.user_id
└─ audit_logs.id

UNIQUE KEYS (UK):
├─ oauth2_refresh_tokens.token_id
├─ oauth2_refresh_tokens.refresh_token
├─ oauth2_access_tokens.token_id
├─ oauth2_access_tokens.access_token
├─ oauth2_authorization_codes.code
├─ oauth2_authorization_requests.request_id
├─ oauth2_authorization_requests.consent_token
├─ oauth2_device_codes.device_code
├─ oauth2_device_codes.user_code
└─ oauth2_users.username

FOREIGN KEYS (FK):
├─ oauth2_refresh_tokens.client_id → oauth2_clients.client_id
├─ oauth2_refresh_tokens.user_id → oauth2_users.user_id
├─ oauth2_access_tokens.client_id → oauth2_clients.client_id
├─ oauth2_access_tokens.user_id → oauth2_users.user_id
├─ oauth2_access_tokens.refresh_token_id → oauth2_refresh_tokens.token_id
├─ oauth2_authorization_codes.client_id → oauth2_clients.client_id
├─ oauth2_authorization_codes.user_id → oauth2_users.user_id
├─ oauth2_authorization_requests.client_id → oauth2_clients.client_id
├─ oauth2_authorization_requests.user_id → oauth2_users.user_id
├─ oauth2_device_codes.client_id → oauth2_clients.client_id
└─ oauth2_device_codes.user_id → oauth2_users.user_id

CASCADE BEHAVIORS:
├─ oauth2_clients DELETE → CASCADE delete all related tokens/codes
├─ oauth2_users DELETE → CASCADE delete all related tokens/codes
└─ oauth2_refresh_tokens DELETE → CASCADE delete child access tokens


════════════════════════════════════════════════════════════════════
                            INDEXES
════════════════════════════════════════════════════════════════════

oauth2_access_tokens:
├─ idx_access_tokens_token_id          ON token_id
├─ idx_access_tokens_access_token      ON access_token
├─ idx_access_tokens_refresh_token_id  ON refresh_token_id
├─ idx_access_tokens_expires_at        ON expires_at
├─ idx_access_tokens_revoked           ON revoked
└─ idx_access_tokens_client_user       ON (client_id, user_id)

oauth2_refresh_tokens:
├─ idx_refresh_tokens_token_id         ON token_id
├─ idx_refresh_tokens_refresh_token    ON refresh_token
├─ idx_refresh_tokens_client_user      ON (client_id, user_id)
├─ idx_refresh_tokens_last_used        ON last_used_at
└─ idx_refresh_tokens_revoked          ON revoked

oauth2_authorization_codes:
├─ idx_auth_codes_code                 ON code
├─ idx_auth_codes_expires_at           ON expires_at
└─ idx_auth_codes_client_user          ON (client_id, user_id)

oauth2_authorization_requests:
├─ idx_auth_req_consent_token          ON consent_token
├─ idx_auth_req_status                 ON status
├─ idx_auth_req_expires_at             ON expires_at
└─ idx_auth_req_client_user            ON (client_id, user_id)

oauth2_device_codes:
├─ idx_device_codes_device_code        ON device_code
├─ idx_device_codes_user_code          ON user_code
├─ idx_device_codes_status             ON status
└─ idx_device_codes_expires_at         ON expires_at

oauth2_users:
└─ idx_users_username                  ON username


════════════════════════════════════════════════════════════════════
                      FIELD TYPE MAPPINGS
════════════════════════════════════════════════════════════════════

TEXT Fields:
├─ IDs (client_id, user_id, token_id): Variable length strings
├─ Tokens (access_token, refresh_token): JWT or random strings
├─ JSON Arrays (redirect_uris, grant_types): Stored as JSON text
├─ Timestamps: ISO 8601 format "YYYY-MM-DDTHH:MM:SSZ"
└─ Hashes (password_hash, client_secret_hash): bcrypt output

INTEGER Fields:
├─ Booleans: 0 = False, 1 = True
├─ Auto-increment IDs: Primary keys
└─ Intervals: Seconds (e.g., device_code interval)


════════════════════════════════════════════════════════════════════
                      DATA RETENTION NOTES
════════════════════════════════════════════════════════════════════

Expired Records:
├─ oauth2_authorization_codes: Clean after expiration (10 min)
├─ oauth2_authorization_requests: Clean after expiration (10 min)
├─ oauth2_device_codes: Clean after expiration (30 min)
├─ oauth2_access_tokens: Keep for audit (or clean after expiry + grace)
└─ oauth2_refresh_tokens: Never expire (manual revocation only)

Audit Logs:
└─ No automatic cleanup - implementor's responsibility


════════════════════════════════════════════════════════════════════
                   STORAGE SIZE ESTIMATES
════════════════════════════════════════════════════════════════════

Per Token Set (1 user, 1 client, 1 refresh + 1 access):
├─ oauth2_refresh_tokens:        ~500 bytes
├─ oauth2_access_tokens:         ~600 bytes (includes JWT)
└─ Total per token set:          ~1.1 KB

Per Authorization Flow:
├─ oauth2_authorization_requests: ~400 bytes
├─ oauth2_authorization_codes:    ~350 bytes
└─ Total per auth flow:          ~750 bytes (temporary)

Per Device Flow:
└─ oauth2_device_codes:          ~300 bytes (temporary)

Example Scale:
├─ 10,000 users × 2 clients × 3 tokens:
│   = 60,000 token records
│   = ~66 MB
│
├─ 1,000,000 audit logs:
│   = ~500 MB (assuming 500 bytes/log)
│
└─ Total: ~600 MB for 10K active users


════════════════════════════════════════════════════════════════════
                 EXAMPLE QUERIES (PERFORMANCE)
════════════════════════════════════════════════════════════════════

1. Token Validation (Most Frequent):
   SELECT * FROM oauth2_access_tokens 
   WHERE token_id = ? AND revoked = 0
   
   Performance: < 5ms (indexed on token_id)

2. Refresh Token Lookup:
   SELECT * FROM oauth2_refresh_tokens 
   WHERE refresh_token = ? AND revoked = 0
   
   Performance: < 5ms (indexed on refresh_token)

3. Count User's Refresh Tokens (FIFO check):
   SELECT COUNT(*) FROM oauth2_refresh_tokens 
   WHERE user_id = ? AND client_id = ? AND revoked = 0
   
   Performance: < 10ms (indexed on client_id, user_id)

4. Find Oldest Refresh Token (FIFO):
   SELECT * FROM oauth2_refresh_tokens 
   WHERE user_id = ? AND client_id = ? AND revoked = 0
   ORDER BY created_at ASC LIMIT 1
   
   Performance: < 10ms (indexed on client_id, user_id)

5. Cascade Revoke Access Tokens:
   UPDATE oauth2_access_tokens 
   SET revoked = 1, revoked_at = ? 
   WHERE refresh_token_id = ? AND revoked = 0
   
   Performance: < 20ms (indexed on refresh_token_id)
