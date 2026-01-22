CREATE TABLE oauth_audit_log (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    subject TEXT,
    client_id TEXT,
    user_id TEXT,
    metadata TEXT,

    created_at INTEGER NOT NULL,
    created_by TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE INDEX idx_audit_log_created ON oauth_audit_log (created_at);
CREATE INDEX idx_audit_log_event ON oauth_audit_log (event_type);

