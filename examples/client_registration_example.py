"""
Example: How to use the ClientRegistrar to register OAuth clients.

This demonstrates the complete client registration flow.
"""

import asyncio
from q_scope.implementations.datastrutures import RegistrationRequest
from q_scope.implementations.oauth2.clients import (
    ClientRegistrar,
    OAuthClientStore,
    DefaultClientSecretGenerator,
    Argon2ClientSecretHasher
)


async def main():
    # Initialize dependencies
    db_path = "/tmp/oauth_test.db"  # In production, use actual database path
    
    client_store = OAuthClientStore(db_path=db_path)
    secret_generator = DefaultClientSecretGenerator(byte_length=32)
    secret_hasher = Argon2ClientSecretHasher()
    
    # Create the registrar service
    registrar = ClientRegistrar(
        client_store=client_store,
        secret_generator=secret_generator,
        secret_hasher=secret_hasher
    )
    
    # Example 1: Register a confidential client (web application)
    print("=" * 60)
    print("Example 1: Registering a confidential client")
    print("=" * 60)
    
    confidential_request = RegistrationRequest(
        user_id="user_123",
        client_identifier="my-web-app",
        is_confidential=True,
        redirect_uris=["https://myapp.com/callback", "https://myapp.com/oauth/callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scopes=["read", "write", "profile"],
        require_pkce=True,
        pkce_methods=["S256"],
        access_token_ttl=3600,  # 1 hour
        refresh_token_ttl=2592000,  # 30 days
        authorization_code_ttl=600,  # 10 minutes
        max_active_access_tokens=5,
        max_active_refresh_tokens=3,
        device_code_ttl=None,
        device_poll_interval=None,
        metadata={"app_name": "My Web Application"}
    )
    
    result = await registrar.register_client(
        request=confidential_request,
        ray_id="ray_001"
    )
    
    if result.status:
        client = result.client_message
        print(f"✅ Client registered successfully!")
        print(f"   Client ID: {client.id}")
        print(f"   Client Identifier: {client.client_identifier}")
        print(f"   Client Secret: {client.client_secret}")  # ⚠️ Store this securely!
        print(f"   Is Confidential: {client.is_confidential}")
        print(f"   Redirect URIs: {client.redirect_uris}")
        print(f"   Grant Types: {client.grant_types}")
    else:
        print(f"❌ Registration failed: {result.client_message}")
        print(f"   Error Code: {result.error_code}")
    
    print()
    
    # Example 2: Register a public client (mobile app / SPA)
    print("=" * 60)
    print("Example 2: Registering a public client")
    print("=" * 60)
    
    public_request = RegistrationRequest(
        user_id="user_456",
        client_identifier="my-mobile-app",
        is_confidential=False,  # Public client (no secret)
        redirect_uris=["myapp://oauth/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scopes=["read", "profile"],
        require_pkce=True,  # PKCE is mandatory for public clients
        pkce_methods=["S256"],
        access_token_ttl=1800,  # 30 minutes
        refresh_token_ttl=None,  # No refresh tokens for public clients
        authorization_code_ttl=300,  # 5 minutes
        max_active_access_tokens=10,
        max_active_refresh_tokens=None,
        device_code_ttl=None,
        device_poll_interval=None,
        metadata={"app_name": "My Mobile App", "platform": "iOS"}
    )
    
    result = await registrar.register_client(
        request=public_request,
        ray_id="ray_002"
    )
    
    if result.status:
        client = result.client_message
        print(f"✅ Client registered successfully!")
        print(f"   Client ID: {client.id}")
        print(f"   Client Identifier: {client.client_identifier}")
        print(f"   Client Secret: {client.client_secret}")  # Will be None for public clients
        print(f"   Is Confidential: {client.is_confidential}")
        print(f"   PKCE Required: {client.require_pkce}")
    else:
        print(f"❌ Registration failed: {result.client_message}")
        print(f"   Error Code: {result.error_code}")
    
    print()
    
    # Example 3: Try to register a duplicate client identifier
    print("=" * 60)
    print("Example 3: Attempting duplicate registration")
    print("=" * 60)
    
    duplicate_request = RegistrationRequest(
        user_id="user_789",
        client_identifier="my-web-app",  # Same as Example 1
        is_confidential=True,
        redirect_uris=["https://other.com/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scopes=["read"],
        require_pkce=False,
        pkce_methods=None,
        access_token_ttl=3600,
        refresh_token_ttl=None,
        authorization_code_ttl=600,
        max_active_access_tokens=None,
        max_active_refresh_tokens=None,
        device_code_ttl=None,
        device_poll_interval=None,
        metadata=None
    )
    
    result = await registrar.register_client(
        request=duplicate_request,
        ray_id="ray_003"
    )
    
    if result.status:
        print(f"✅ Client registered (unexpected)")
    else:
        print(f"❌ Registration failed (expected): {result.client_message}")
        print(f"   Error Code: {result.error_code}")
    
    print()
    
    # Example 4: Retrieve a client by identifier
    print("=" * 60)
    print("Example 4: Retrieving client by identifier")
    print("=" * 60)
    
    result = await registrar.get_client_by_identifier(
        client_identifier="my-web-app",
        ray_id="ray_004"
    )
    
    if result.status:
        oauth_client = result.client_message
        print(f"✅ Client found!")
        print(f"   Client ID: {oauth_client.id}")
        print(f"   Client Identifier: {oauth_client.client_identifier}")
        print(f"   Is Enabled: {oauth_client.is_enabled}")
        # Note: client_secret is hashed in the database
    else:
        print(f"❌ Client not found: {result.client_message}")
    
    print()
    print("=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
