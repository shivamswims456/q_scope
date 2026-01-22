oauth2-framework/
├── README.md
├── LICENSE
├── pyproject.toml
├── setup.py
│
├── oauth2_framework/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── server.py                      # OAuth2Server - main orchestrator
│   │   │
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                    # BaseEndpoint abstract class
│   │   │   ├── authorize.py               # AuthorizeEndpoint
│   │   │   ├── token.py                   # TokenEndpoint
│   │   │   ├── revoke.py                  # RevokeEndpoint
│   │   │   ├── introspect.py              # IntrospectEndpoint
│   │   │   ├── consent.py                 # ConsentEndpoint, ConsentCallbackEndpoint
│   │   │   ├── device.py                  # DeviceAuthorizationEndpoint, DeviceVerifyEndpoint
│   │   │   ├── register.py                # ClientRegistrationEndpoint
│   │   │   └── discovery.py               # OAuth2DiscoveryEndpoint (RFC 8414)
│   │   │
│   │   ├── grant_handlers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                    # BaseGrantHandler abstract
│   │   │   ├── authorization_code.py      # AuthorizationCodeHandler
│   │   │   ├── client_credentials.py      # ClientCredentialsHandler
│   │   │   ├── refresh_token.py           # RefreshTokenHandler
│   │   │   ├── password.py                # PasswordGrantHandler (deprecated)
│   │   │   └── device.py                  # DeviceCodeHandler
│   │   │
│   │   ├── validators/
│   │   │   ├── __init__.py
│   │   │   ├── request_validator.py       # oauthlib RequestValidator implementation
│   │   │   ├── pkce.py                    # PKCEValidator
│   │   │   └── scope.py                   # ScopeValidator, ScopeManager
│   │   │
│   │   ├── token/
│   │   │   ├── __init__.py
│   │   │   ├── generator.py               # TokenGenerator abstract, JWTTokenGenerator
│   │   │   ├── verifier.py                # TokenVerifier
│   │   │   └── limits.py                  # TokenLimitEnforcer
│   │   │
│   │   ├── client/
│   │   │   ├── __init__.py
│   │   │   ├── registrar.py               # ClientRegistrar
│   │   │   └── authenticator.py           # ClientAuthenticator
│   │   │
│   │   └── exceptions.py                  # All OAuth2 error classes
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py                        # Abstract storage interfaces
│   │   │                                  # - BaseClientStore
│   │   │                                  # - BaseAccessTokenStore
│   │   │                                  # - BaseRefreshTokenStore
│   │   │                                  # - BaseGrantStore
│   │   │                                  # - BaseDeviceStore
│   │   │                                  # - BaseUserStore
│   │   │                                  # - BaseStorage (composition)
│   │   │
│   │   └── sql/
│   │       ├── __init__.py
│   │       ├── storage.py                 # SQLiteStorage - main class
│   │       ├── client_store.py            # SQLClientStore
│   │       ├── access_token_store.py      # SQLAccessTokenStore
│   │       ├── refresh_token_store.py     # SQLRefreshTokenStore
│   │       ├── grant_store.py             # SQLGrantStore
│   │       ├── device_store.py            # SQLDeviceStore
│   │       ├── user_store.py              # SQLUserStore
│   │       │
│   │       └── schema/
│   │           └── sqlite.sql             # Complete database schema
│   │
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── logger.py                      # AuditLogger abstract class
│   │   ├── sql_logger.py                  # SQLiteAuditLogger
│   │   │
│   │   └── schema/
│   │       └── sqlite.sql                 # Audit log schema
│   │
│   ├── asgi/
│   │   ├── __init__.py
│   │   ├── app.py                         # OAuth2ASGIApp - main ASGI application
│   │   ├── middleware.py                  # RayIDMiddleware, AuditMiddleware
│   │   ├── context.py                     # RequestContext class
│   │   └── renderers.py                   # ConsentRenderer, DeviceVerificationRenderer
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── client.py                      # Client dataclass
│   │   ├── token.py                       # AccessToken, RefreshToken dataclasses
│   │   ├── grant.py                       # AuthorizationGrant dataclass
│   │   ├── device.py                      # DeviceCode dataclass
│   │   ├── user.py                        # User protocol/interface
│   │   └── authorization_request.py       # AuthorizationRequest dataclass
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── id_generator.py                # IDGenerator abstract, SonyflakeIDGenerator
│   │   ├── scope_manager.py               # ScopeManager (wildcard matching)
│   │   ├── security.py                    # SecretHasher, constant-time comparison
│   │   └── constants.py                   # Grant types, response types, etc.
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                    # OAuth2Settings dataclass
│   │
│   └── interfaces/
│       ├── __init__.py
│       ├── registration_auth.py           # RegistrationAuthenticator abstract
│       └── consent.py                     # Consent callback interfaces
│
├── examples/
│   ├── quickstart/
│   │   ├── app.py                         # Minimal working example
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   ├── fastapi_integration/
│   │   ├── app.py                         # FastAPI with OAuth2
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   ├── device_flow/
│   │   ├── app.py                         # Device flow example
│   │   ├── templates/
│   │   │   └── device_verify.html
│   │   └── README.md
│   │
│   ├── password_flow/
│   │   ├── app.py                         # Password credentials example
│   │   └── README.md
│   │
│   ├── custom_storage/
│   │   ├── postgres_storage.py            # PostgreSQL implementation example
│   │   ├── redis_storage.py               # Redis implementation example
│   │   ├── app.py
│   │   └── README.md
│   │
│   └── turso/
│       ├── app.py                         # Turso deployment example
│       ├── .env.example
│       └── README.md
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                        # Pytest fixtures
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_token_generator.py
│   │   ├── test_scope_manager.py
│   │   ├── test_pkce_validator.py
│   │   ├── test_id_generator.py
│   │   └── test_security.py
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── test_sql_storage.py
│   │   ├── test_client_store.py
│   │   ├── test_token_store.py
│   │   └── test_storage_contract.py       # Abstract storage compliance tests
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_authorization_code_flow.py
│   │   ├── test_client_credentials_flow.py
│   │   ├── test_refresh_token_flow.py
│   │   ├── test_password_flow.py
│   │   ├── test_device_flow.py
│   │   ├── test_token_revocation.py
│   │   ├── test_token_introspection.py
│   │   └── test_client_registration.py
│   │
│   ├── security/
│   │   ├── __init__.py
│   │   ├── test_timing_attacks.py
│   │   ├── test_token_entropy.py
│   │   └── test_pkce_compliance.py
│   │
│   ├── rfc_compliance/
│   │   ├── __init__.py
│   │   ├── test_rfc6749.py                # OAuth2 core spec
│   │   ├── test_rfc7636.py                # PKCE
│   │   ├── test_rfc8628.py                # Device flow
│   │   ├── test_rfc7009.py                # Token revocation
│   │   ├── test_rfc7662.py                # Token introspection
│   │   └── test_rfc7591.py                # Dynamic registration
│   │
│   └── e2e/
│       ├── __init__.py
│       └── test_complete_flows.py
│
├── docs/
│   ├── index.md
│   ├── quickstart.md
│   ├── installation.md
│   │
│   ├── guides/
│   │   ├── storage_implementation.md      # How to implement custom storage
│   │   ├── deployment.md                  # Production deployment
│   │   ├── turso_deployment.md            # Turso-specific guide
│   │   ├── security_best_practices.md
│   │   └── customization.md               # Customizing renderers, callbacks
│   │
│   ├── api/
│   │   ├── server.md                      # OAuth2Server API
│   │   ├── storage.md                     # Storage interfaces
│   │   ├── endpoints.md                   # Endpoint classes
│   │   ├── grant_handlers.md
│   │   ├── models.md
│   │   └── configuration.md               # OAuth2Settings
│   │
│   ├── flows/
│   │   ├── authorization_code.md
│   │   ├── client_credentials.md
│   │   ├── refresh_token.md
│   │   ├── password.md
│   │   └── device.md
│   │
│   └── examples/
│       ├── basic_usage.md
│       ├── fastapi_integration.md
│       ├── custom_storage.md
│       └── device_flow.md
│
└── scripts/
    ├── generate_secret.py                 # Generate JWT secret keys
    ├── create_client.py                   # CLI tool to create clients
    └── migrate_schema.py                  # Database migration helper
