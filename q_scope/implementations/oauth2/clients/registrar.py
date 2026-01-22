import time
import uuid
import json
from typing import Union

from q_scope.implementations.datastrutures import (
    OAuthClient,
    OAuthClientConfig,
    Client,
    RegistrationRequest,
    SuccessResult,
    FailedResult
)
from q_scope.implementations.store.sqllite.pypika_imp.stores import (
    OAuthClientStore,
    OAuthClientConfigStore
)
from q_scope.implementations.oauth2.templates.base import (
    ClientSecretGenerator,
    ClientSecretHasher
)


class ClientRegistrar:
    """
    Service for registering OAuth clients.
    
    Responsibilities:
    - Validate registration requests
    - Generate client IDs and secrets
    - Hash secrets for secure storage
    - Persist clients and configurations to storage
    - Return registration results with wrapped Success/Failed results
    
    This service is used across all OAuth flows that require client registration.
    """

    def __init__(
        self,
        *,
        client_store: OAuthClientStore,
        config_store: OAuthClientConfigStore,
        secret_generator: ClientSecretGenerator,
        secret_hasher: ClientSecretHasher,
    ):
        """
        Initialize the ClientRegistrar with required dependencies.
        
        Args:
            client_store: Storage abstraction for persisting OAuth clients
            config_store: Storage abstraction for persisting client configurations
            secret_generator: Generator for creating client secrets
            secret_hasher: Hasher for securing client secrets
        """
        self._client_store = client_store
        self._config_store = config_store
        self._secret_generator = secret_generator
        self._secret_hasher = secret_hasher

    async def register_client(
        self,
        *,
        request: RegistrationRequest,
        ray_id: str
    ) -> Union[SuccessResult, FailedResult]:
        """
        Register a new OAuth client.
        
        This method:
        1. Validates the registration request
        2. Generates a unique client ID
        3. Generates and hashes the client secret (for confidential clients)
        4. Creates the OAuthClient record
        5. Creates the OAuthClientConfig record
        6. Persists both to storage
        7. Returns a Client object with the plaintext secret (one-time only)
        
        Args:
            request: RegistrationRequest containing client configuration
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult with Client object (including plaintext secret) on success
            FailedResult with error details on failure
        """
        
        # Validate the registration request
        validation_result = self._validate_request(request, ray_id)
        if not validation_result.status:
            return validation_result
        
        # Check if client identifier already exists
        existing_check = await self._check_duplicate_identifier(
            request.client_identifier, ray_id
        )
        if not existing_check.status:
            return existing_check
        
        # Generate unique client ID
        client_id = self._generate_client_id()
        
        # Generate and hash client secret for confidential clients
        plaintext_secret = None
        hashed_secret = None
        
        if request.is_confidential:
            plaintext_secret = self._secret_generator.generate_secret(
                user_id=request.user_id
            )
            hashed_secret = self._secret_hasher.hash(
                plaintext_secret,
                user_id=request.user_id,
                client_id=client_id
            )
        
        # Get current timestamp
        current_time = int(time.time())
        
        # Create OAuthClient for storage (identity)
        oauth_client = OAuthClient(
            id=client_id,
            client_identifier=request.client_identifier,
            client_secret=hashed_secret,  # Store hashed secret
            is_confidential=request.is_confidential,
            redirect_uris=self._serialize_list(request.redirect_uris),
            grant_types=self._serialize_list(request.grant_types),
            scopes=self._serialize_list(request.scopes) if request.scopes else None,
            is_enabled=True,  # New clients are enabled by default
            created_at=current_time,
            created_by=request.user_id,
            updated_at=current_time,
            updated_by=request.user_id
        )
        
        # Create OAuthClientConfig for storage (configuration)
        oauth_config = OAuthClientConfig(
            client_id=client_id,
            response_types=self._serialize_list(request.response_types),
            require_pkce=request.require_pkce,
            pkce_methods=self._serialize_list(request.pkce_methods) if request.pkce_methods else None,
            access_token_ttl=request.access_token_ttl,
            refresh_token_ttl=request.refresh_token_ttl,
            authorization_code_ttl=request.authorization_code_ttl,
            max_active_access_tokens=request.max_active_access_tokens,
            max_active_refresh_tokens=request.max_active_refresh_tokens,
            device_code_ttl=request.device_code_ttl,
            device_poll_interval=request.device_poll_interval,
            metadata=json.dumps(request.metadata) if request.metadata else None,
            created_at=current_time,
            created_by=request.user_id,
            updated_at=current_time,
            updated_by=request.user_id
        )
        
        # Persist client identity to storage
        insert_result = await self._client_store.insert(oauth_client, ray_id)
        
        if not insert_result.status:
            return insert_result  # Return the FailedResult from storage
        
        # Persist client configuration to storage
        config_insert_result = await self._config_store.insert(oauth_config, ray_id)
        
        if not config_insert_result.status:
            # Rollback: delete the client we just inserted
            await self._client_store.delete_by_id(client_id, ray_id)
            return config_insert_result  # Return the FailedResult from config storage
        
        # Create Client object for response (includes plaintext secret)
        client = Client(
            id=client_id,
            client_identifier=request.client_identifier,
            user_id=request.user_id,
            is_confidential=request.is_confidential,
            client_secret=plaintext_secret,  # Return plaintext secret (one-time only)
            redirect_uris=request.redirect_uris,
            grant_types=request.grant_types,
            response_types=request.response_types,
            scopes=request.scopes,
            require_pkce=request.require_pkce,
            pkce_methods=request.pkce_methods,
            access_token_ttl=request.access_token_ttl,
            refresh_token_ttl=request.refresh_token_ttl,
            authorization_code_ttl=request.authorization_code_ttl,
            max_active_access_tokens=request.max_active_access_tokens,
            max_active_refresh_tokens=request.max_active_refresh_tokens,
            device_code_ttl=request.device_code_ttl,
            device_poll_interval=request.device_poll_interval,
            is_enabled=True,
            created_at=current_time,
            created_by=request.user_id
        )
        
        return SuccessResult(
            ray_id=ray_id,
            client_message=client
        )

    async def get_client_by_id(
        self,
        *,
        client_id: str,
        ray_id: str
    ) -> Union[SuccessResult, FailedResult]:
        """
        Retrieve a client by its ID.
        
        Args:
            client_id: Internal client ID
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult with OAuthClient if found, FailedResult otherwise
        """
        return await self._client_store.get_by_id(client_id, ray_id)

    async def get_client_by_identifier(
        self,
        *,
        client_identifier: str,
        ray_id: str
    ) -> Union[SuccessResult, FailedResult]:
        """
        Retrieve a client by its public identifier.
        
        Args:
            client_identifier: Public client identifier
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult with OAuthClient if found, FailedResult otherwise
        """
        return await self._client_store.get_by_client_identifier(
            client_identifier, ray_id
        )

    def _validate_request(
        self, request: RegistrationRequest, ray_id: str
    ) -> Union[SuccessResult, FailedResult]:
        """
        Validate the registration request for required fields and constraints.
        
        Args:
            request: RegistrationRequest to validate
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult if validation passes, FailedResult otherwise
        """
        # Validate user_id
        if not request.user_id or not request.user_id.strip():
            return FailedResult(
                ray_id=ray_id,
                client_message="user_id is required",
                error_code="INVALID_REQUEST"
            )
        
        # Validate client_identifier
        if not request.client_identifier or not request.client_identifier.strip():
            return FailedResult(
                ray_id=ray_id,
                client_message="client_identifier is required",
                error_code="INVALID_REQUEST"
            )
        
        # Validate redirect_uris
        if not request.redirect_uris or len(request.redirect_uris) == 0:
            return FailedResult(
                ray_id=ray_id,
                client_message="At least one redirect_uri is required",
                error_code="INVALID_REQUEST"
            )
        
        # Validate grant_types
        if not request.grant_types or len(request.grant_types) == 0:
            return FailedResult(
                ray_id=ray_id,
                client_message="At least one grant_type is required",
                error_code="INVALID_REQUEST"
            )
        
        # Validate TTL values are positive
        if request.access_token_ttl <= 0:
            return FailedResult(
                ray_id=ray_id,
                client_message="access_token_ttl must be positive",
                error_code="INVALID_REQUEST"
            )
        
        if request.authorization_code_ttl <= 0:
            return FailedResult(
                ray_id=ray_id,
                client_message="authorization_code_ttl must be positive",
                error_code="INVALID_REQUEST"
            )
        
        return SuccessResult(
            ray_id=ray_id,
            client_message="Validation successful"
        )

    async def _check_duplicate_identifier(
        self, client_identifier: str, ray_id: str
    ) -> Union[SuccessResult, FailedResult]:
        """
        Check if a client identifier already exists.
        
        Args:
            client_identifier: Client identifier to check
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult if identifier is available, FailedResult if duplicate
        """
        result = await self._client_store.get_by_client_identifier(
            client_identifier, ray_id
        )
        
        # If we got a success result, the identifier already exists
        if result.status:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Client identifier '{client_identifier}' already exists",
                error_code="DUPLICATE_CLIENT_IDENTIFIER"
            )
        
        # If we got a NOT_FOUND error, the identifier is available
        if isinstance(result, FailedResult) and result.error_code == "NOT_FOUND":
            return SuccessResult(
                ray_id=ray_id,
                client_message="Identifier available"
            )
        
        # Any other error is a real failure
        return result

    def _generate_client_id(self) -> str:
        """
        Generate a unique client ID.
        
        For now uses UUID4. In production, this could be replaced with
        a distributed ID generator like Sonyflake.
        
        Returns:
            A unique client ID string
        """
        return str(uuid.uuid4())

    def _serialize_list(self, items: list[str]) -> str:
        """
        Serialize a list of strings into a space-separated string for storage.
        
        Args:
            items: List of strings to serialize
            
        Returns:
            Space-separated string
        """
        return " ".join(items)
