from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(kw_only=True, slots=True)
class Result:
    status:bool
    client_message:Any
    ray_id:str


@dataclass(kw_only=True, slots=True)
class SuccessResult:
    status:bool = field(default=True)
    client_message:Any = field(default=None)
    ray_id:str




@dataclass(kw_only=True, slots=True)
class FailedResult:
    status:bool = field(default=False)
    client_message:Any = field(default=None)
    ray_id:str
    error_code:str






@dataclass(kw_only=True, slots=True)
class AuditFields:
    created_at: int
    created_by: str
    updated_at: int
    updated_by: str



@dataclass(kw_only=True, slots=True)
class OAuthClient(AuditFields):
    id: str
    client_identifier: str
    client_secret: str | None
    is_confidential: bool
    redirect_uris: str
    grant_types: str
    scopes: str | None
    is_enabled: bool





@dataclass(kw_only=True, slots=True)
class OAuthUser(AuditFields):
    id: str
    external_id: str
    is_active: bool



@dataclass(kw_only=True, slots=True)
class AuthorizationCode(AuditFields):
    id: str
    code: str
    client_id: str
    user_id: str
    redirect_uri: str
    scopes: Optional[str]
    code_challenge: Optional[str]
    code_challenge_method: Optional[str]
    expires_at: int
    consumed_at: Optional[int]



@dataclass(kw_only=True, slots=True)
class AccessToken(AuditFields):
    id: str
    token: str
    client_id: str
    user_id: Optional[str]
    scopes: Optional[str]
    expires_at: int
    revoked_at: Optional[int]



@dataclass(kw_only=True, slots=True)
class RefreshToken(AuditFields):
    id: str
    token: str
    client_id: str
    user_id: Optional[str]
    scopes: Optional[str]
    revoked_at: Optional[int]

@dataclass(kw_only=True, slots=True)
class DeviceCode(AuditFields):
    id: str
    device_code: str
    user_code: str
    client_id: str
    user_id: Optional[str]
    scopes: Optional[str]
    expires_at: int
    interval: int
    state: str

@dataclass(kw_only=True, slots=True)
class AuditLog(AuditFields):
    id: str
    event_type: str
    subject: Optional[str]
    client_id: Optional[str]
    user_id: Optional[str]
    metadata: Optional[str]



@dataclass(kw_only=True, slots=True)
class RegistrationRequest:
    # ---- Ownership / binding ----
    user_id: str

    # ---- Client identity & type ----
    client_identifier: str
    is_confidential: bool

    # ---- Redirect & grant configuration ----
    redirect_uris: list[str]
    grant_types: list[str]
    response_types: list[str]

    # ---- Scope configuration ----
    scopes: list[str]

    # ---- PKCE & security posture ----
    require_pkce: bool
    pkce_methods: list[str] | None

    # ---- Token & lifecycle limits (config snapshot) ----
    access_token_ttl: int
    refresh_token_ttl: int | None
    authorization_code_ttl: int

    max_active_access_tokens: int | None
    max_active_refresh_tokens: int | None

    # ---- Device flow constraints ----
    device_code_ttl: int | None
    device_poll_interval: int | None

    # ---- Operational metadata ----
    metadata: dict[str, str] | None



@dataclass(kw_only=True, slots=True)
class Client:
    # ---- Identity ----
    id: str                     # internal unique ID
    client_identifier: str       # public identifier

    # ---- Ownership ----
    user_id: str

    # ---- Client type & security ----
    is_confidential: bool
    client_secret: str | None   # PRESENT ONLY ON CREATION

    # ---- OAuth capabilities ----
    redirect_uris: list[str]
    grant_types: list[str]
    response_types: list[str]
    scopes: list[str]

    # ---- PKCE configuration ----
    require_pkce: bool
    pkce_methods: list[str] | None

    # ---- Token & lifecycle limits (snapshot) ----
    access_token_ttl: int
    refresh_token_ttl: int | None
    authorization_code_ttl: int

    max_active_access_tokens: int | None
    max_active_refresh_tokens: int | None

    # ---- Device flow constraints ----
    device_code_ttl: int | None
    device_poll_interval: int | None

    # ---- Status ----
    is_enabled: bool

    # ---- Audit ----
    created_at: int
    created_by: str

