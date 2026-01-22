PRAGMA foreign_keys = ON;

-- =====================================================
-- Clients
-- =====================================================



CREATE TABLE oauth_clients (
    id TEXT PRIMARY KEY,

    -- OAuth2 client identity
    client_identifier TEXT NOT NULL UNIQUE,   -- OAuth2 client_id
    client_secret TEXT,
    is_confidential INTEGER NOT NULL CHECK (is_confidential IN (0,1)),

    -- OAuth2 capabilities
    redirect_uris TEXT NOT NULL,
    grant_types TEXT NOT NULL,                 -- defines allowed flows
    scopes TEXT,

    is_enabled INTEGER NOT NULL CHECK (is_enabled IN (0,1)),

    -- audit (Claude-locked)
    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE INDEX idx_clients_enabled
    ON oauth_clients (is_enabled);

-- =====================================================
-- Users (reference only)
-- =====================================================

CREATE TABLE oauth_users (
    id TEXT PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL CHECK (is_active IN (0,1)),

    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    updated_by TEXT NOT NULL
);

-- =====================================================
-- Authorization Codes
-- =====================================================

CREATE TABLE oauth_authorization_codes (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    client_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    scopes TEXT,
    code_challenge TEXT,
    code_challenge_method TEXT,
    expires_at INTEGER NOT NULL,
    consumed_at INTEGER,

    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    updated_by TEXT NOT NULL,

    FOREIGN KEY (client_id) REFERENCES oauth_clients(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES oauth_users(id) ON DELETE CASCADE
);

CREATE INDEX idx_auth_codes_client ON oauth_authorization_codes (client_id);
CREATE INDEX idx_auth_codes_expires ON oauth_authorization_codes (expires_at);

-- =====================================================
-- Access Tokens
-- =====================================================

CREATE TABLE oauth_access_tokens (
    id TEXT PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    client_id TEXT NOT NULL,
    user_id TEXT,
    scopes TEXT,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER,

    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    updated_by TEXT NOT NULL,

    FOREIGN KEY (client_id) REFERENCES oauth_clients(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES oauth_users(id) ON DELETE CASCADE
);

CREATE INDEX idx_access_tokens_client ON oauth_access_tokens (client_id);
CREATE INDEX idx_access_tokens_user ON oauth_access_tokens (user_id);
CREATE INDEX idx_access_tokens_expires ON oauth_access_tokens (expires_at);
CREATE INDEX idx_access_tokens_created ON oauth_access_tokens (created_at);

-- =====================================================
-- Refresh Tokens
-- =====================================================

CREATE TABLE oauth_refresh_tokens (
    id TEXT PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    client_id TEXT NOT NULL,
    user_id TEXT,
    scopes TEXT,
    revoked_at INTEGER,

    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    updated_by TEXT NOT NULL,

    FOREIGN KEY (client_id) REFERENCES oauth_clients(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES oauth_users(id) ON DELETE CASCADE
);

CREATE INDEX idx_refresh_tokens_client ON oauth_refresh_tokens (client_id);
CREATE INDEX idx_refresh_tokens_user ON oauth_refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_created ON oauth_refresh_tokens (created_at);

-- =====================================================
-- Device Authorization Codes
-- =====================================================

CREATE TABLE oauth_device_codes (
    id TEXT PRIMARY KEY,
    device_code TEXT NOT NULL UNIQUE,
    user_code TEXT NOT NULL UNIQUE,
    client_id TEXT NOT NULL,
    user_id TEXT,
    scopes TEXT,
    expires_at INTEGER NOT NULL,
    interval INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (
        state IN ('pending', 'approved', 'denied', 'consumed', 'expired')
    ),

    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    updated_by TEXT NOT NULL,

    FOREIGN KEY (client_id) REFERENCES oauth_clients(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES oauth_users(id) ON DELETE SET NULL
);

CREATE INDEX idx_device_codes_state ON oauth_device_codes (state);
CREATE INDEX idx_device_codes_expires ON oauth_device_codes (expires_at);

-- =====================================================
-- Audit Log (append-only)
-- =====================================================


