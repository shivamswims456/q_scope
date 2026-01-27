import os
import time
from typing import Optional

from q_scope.implementations.store.sqllite.pypika_imp.stores import (
    OAuthClientStore,
    OAuthClientConfigStore,
    AccessTokenStore,
    RefreshTokenStore,
    AuditLogStore,
)
from q_scope.implementations.oauth2.secrets import Argon2ClientSecretHasher


class SystemClock:
    def now(self) -> int:
        return int(time.time())


class CompositeStore:
    def __init__(self, db_path: str):
        self.clients = OAuthClientStore(db_path)
        self.client_configs = OAuthClientConfigStore(db_path)
        self.access_tokens = AccessTokenStore(db_path)
        self.refresh_tokens = RefreshTokenStore(db_path)
        self.audit_logs = AuditLogStore(db_path)


class OAuth2Config:
    # minimal config wrapper for the flow
    def __init__(self):
        self.rotate_refresh_tokens = True  # Default policy


class Logger:
    # Simple logger stub
    def info(self, event: str, **kwargs):
        print(f"INFO: {event} {kwargs}")

    def error(self, event: str, **kwargs):
        print(f"ERROR: {event} {kwargs}")


class Dependencies:
    _instance = None
    
    def __init__(self):
        db_path = os.getenv("OAUTH2_DB_PATH", "oauth2_db.sqlite")
        self.storage = CompositeStore(db_path)
        self.clock = SystemClock()
        self.hasher = Argon2ClientSecretHasher()
        self.config = OAuth2Config()
        self.logger = Logger()
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
