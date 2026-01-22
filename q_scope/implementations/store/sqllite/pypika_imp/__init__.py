from pypika import Table, Schema

schema = Schema("main")

# =====================================================
# Clients
# =====================================================

oauth_clients = Table(
    "oauth_clients",
    schema=schema
)

# Columns (reference)
# id
# client_identifier
# client_secret
# is_confidential
# redirect_uris
# grant_types
# scopes
# is_enabled
# created_at
# created_by
# updated_at
# updated_by


# =====================================================
# Client Configurations
# =====================================================

oauth_client_configs = Table(
    "oauth_client_configs",
    schema=schema
)

# Columns (reference)
# client_id (FK to oauth_clients.id)
# response_types
# require_pkce
# pkce_methods
# access_token_ttl
# refresh_token_ttl
# authorization_code_ttl
# max_active_access_tokens
# max_active_refresh_tokens
# device_code_ttl
# device_poll_interval
# metadata
# created_at
# created_by
# updated_at
# updated_by



# =====================================================
# Users (reference only)
# =====================================================

oauth_users = Table(
    "oauth_users",
    schema=schema
)

# Columns
# id
# external_id
# is_active
# created_at
# created_by
# updated_at
# updated_by


# =====================================================
# Authorization Codes
# =====================================================

oauth_authorization_codes = Table(
    "oauth_authorization_codes",
    schema=schema
)

# Columns
# id
# code
# client_id
# user_id
# redirect_uri
# scopes
# code_challenge
# code_challenge_method
# expires_at
# consumed_at
# created_at
# created_by
# updated_at
# updated_by


# =====================================================
# Access Tokens
# =====================================================

oauth_access_tokens = Table(
    "oauth_access_tokens",
    schema=schema
)

# Columns
# id
# token
# client_id
# user_id
# scopes
# expires_at
# revoked_at
# created_at
# created_by
# updated_at
# updated_by


# =====================================================
# Refresh Tokens
# =====================================================

oauth_refresh_tokens = Table(
    "oauth_refresh_tokens",
    schema=schema
)

# Columns
# id
# token
# client_id
# user_id
# scopes
# revoked_at
# created_at
# created_by
# updated_at
# updated_by


# =====================================================
# Device Authorization Codes
# =====================================================

oauth_device_codes = Table(
    "oauth_device_codes",
    schema=schema
)

# Columns
# id
# device_code
# user_code
# client_id
# user_id
# scopes
# expires_at
# interval
# state
# created_at
# created_by
# updated_at
# updated_by


# =====================================================
# Audit Log (append-only)
# =====================================================

oauth_audit_log = Table(
    "oauth_audit_log",
    schema=schema
)

# Columns
# id
# event_type
# subject
# client_id
# user_id
# metadata
# created_at
# created_by
# updated_at
# updated_by

