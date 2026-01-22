from typing import Optional, Union
import aiosqlite
from pypika import Query, Parameter

from q_scope.implementations.datastrutures import OAuthClient, SuccessResult, FailedResult
from q_scope.implementations.store.templates import ClientTable
from q_scope.implementations.store.sqllite.pypika_imp import oauth_clients


class OAuthClientStore(ClientTable):
    """
    SQLite-based implementation of ClientTable using pypika.
    Consumes OAuthClient dataclass and wraps all results in SuccessResult/FailedResult.
    """

    def __init__(self, db_path: str):
        """
        Initialize the OAuthClientStore with a database connection path.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

    async def insert(self, row: OAuthClient, ray_id: str) -> Union[SuccessResult, FailedResult]:
        """
        Insert a new OAuth client into the oauth_clients table.
        
        Args:
            row: OAuthClient dataclass instance
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult if insertion succeeds, FailedResult otherwise
        """
        try:
            query = Query.into(oauth_clients).columns(
                "id", "client_identifier", "client_secret", "is_confidential",
                "redirect_uris", "grant_types", "scopes", "is_enabled",
                "created_at", "created_by", "updated_at", "updated_by"
            ).insert(
                Parameter(":id"), Parameter(":client_identifier"), Parameter(":client_secret"), Parameter(":is_confidential"),
                Parameter(":redirect_uris"), Parameter(":grant_types"), Parameter(":scopes"), Parameter(":is_enabled"),
                Parameter(":created_at"), Parameter(":created_by"), Parameter(":updated_at"), Parameter(":updated_by")
            )

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    str(query),
                    {
                        "id": row.id,
                        "client_identifier": row.client_identifier,
                        "client_secret": row.client_secret,
                        "is_confidential": row.is_confidential,
                        "redirect_uris": row.redirect_uris,
                        "grant_types": row.grant_types,
                        "scopes": row.scopes,
                        "is_enabled": row.is_enabled,
                        "created_at": row.created_at,
                        "created_by": row.created_by,
                        "updated_at": row.updated_at,
                        "updated_by": row.updated_by
                    }
                )
                await db.commit()

            return SuccessResult(
                ray_id=ray_id,
                client_message=f"OAuth client {row.client_identifier} inserted successfully"
            )
        except Exception as e:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Failed to insert OAuth client {row.client_identifier}",
                error_code="INSERT_FAILED"
            )

    async def get_by_id(self, id: str, ray_id: str) -> Union[SuccessResult, FailedResult]:
        """
        Retrieve an OAuth client by its ID.
        
        Args:
            id: Client ID to retrieve
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult with OAuthClient in client_message if found, FailedResult otherwise
        """
        try:
            query = Query.from_(oauth_clients).select(
                "id", "client_identifier", "client_secret", "is_confidential",
                "redirect_uris", "grant_types", "scopes", "is_enabled",
                "created_at", "created_by", "updated_at", "updated_by"
            ).where(oauth_clients.id == Parameter(":id"))

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(str(query), {"id": id}) as cursor:
                    result = await cursor.fetchone()

                    if result is None:
                        return FailedResult(
                            ray_id=ray_id,
                            client_message=f"OAuth client with ID {id} not found",
                            error_code="NOT_FOUND"
                        )

                    client = OAuthClient(
                        id=result["id"],
                        client_identifier=result["client_identifier"],
                        client_secret=result["client_secret"],
                        is_confidential=bool(result["is_confidential"]),
                        redirect_uris=result["redirect_uris"],
                        grant_types=result["grant_types"],
                        scopes=result["scopes"],
                        is_enabled=bool(result["is_enabled"]),
                        created_at=result["created_at"],
                        created_by=result["created_by"],
                        updated_at=result["updated_at"],
                        updated_by=result["updated_by"]
                    )

                    return SuccessResult(
                        ray_id=ray_id,
                        client_message=client
                    )
        except Exception as e:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Failed to retrieve OAuth client: {str(e)}",
                error_code="FETCH_FAILED"
            )

    async def get_by_client_identifier(
        self, client_identifier: str, ray_id: str
    ) -> Union[SuccessResult, FailedResult]:
        """
        Retrieve an OAuth client by its client identifier.
        
        Args:
            client_identifier: Client identifier to search for
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult with OAuthClient in client_message if found, FailedResult otherwise
        """
        try:
            query = Query.from_(oauth_clients).select(
                "id", "client_identifier", "client_secret", "is_confidential",
                "redirect_uris", "grant_types", "scopes", "is_enabled",
                "created_at", "created_by", "updated_at", "updated_by"
            ).where(oauth_clients.client_identifier == Parameter(":client_identifier"))

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(str(query), {"client_identifier": client_identifier}) as cursor:
                    result = await cursor.fetchone()

                    if result is None:
                        return FailedResult(
                            ray_id=ray_id,
                            client_message=f"OAuth client with identifier {client_identifier} not found",
                            error_code="NOT_FOUND"
                        )

                    client = OAuthClient(
                        id=result["id"],
                        client_identifier=result["client_identifier"],
                        client_secret=result["client_secret"],
                        is_confidential=bool(result["is_confidential"]),
                        redirect_uris=result["redirect_uris"],
                        grant_types=result["grant_types"],
                        scopes=result["scopes"],
                        is_enabled=bool(result["is_enabled"]),
                        created_at=result["created_at"],
                        created_by=result["created_by"],
                        updated_at=result["updated_at"],
                        updated_by=result["updated_by"]
                    )

                    return SuccessResult(
                        ray_id=ray_id,
                        client_message=client
                    )
        except Exception as e:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Failed to retrieve OAuth client: {str(e)}",
                error_code="FETCH_FAILED"
            )

    async def update(self, row: OAuthClient, ray_id: str) -> Union[SuccessResult, FailedResult]:
        """
        Update an existing OAuth client.
        
        Args:
            row: OAuthClient dataclass instance with updated values
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult if update succeeds, FailedResult otherwise
        """
        try:
            query = Query.update(oauth_clients).set(
                oauth_clients.client_identifier, Parameter(":client_identifier")
            ).set(
                oauth_clients.client_secret, Parameter(":client_secret")
            ).set(
                oauth_clients.is_confidential, Parameter(":is_confidential")
            ).set(
                oauth_clients.redirect_uris, Parameter(":redirect_uris")
            ).set(
                oauth_clients.grant_types, Parameter(":grant_types")
            ).set(
                oauth_clients.scopes, Parameter(":scopes")
            ).set(
                oauth_clients.is_enabled, Parameter(":is_enabled")
            ).set(
                oauth_clients.updated_at, Parameter(":updated_at")
            ).set(
                oauth_clients.updated_by, Parameter(":updated_by")
            ).where(oauth_clients.id == Parameter(":id"))

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    str(query),
                    {
                        "client_identifier": row.client_identifier,
                        "client_secret": row.client_secret,
                        "is_confidential": row.is_confidential,
                        "redirect_uris": row.redirect_uris,
                        "grant_types": row.grant_types,
                        "scopes": row.scopes,
                        "is_enabled": row.is_enabled,
                        "updated_at": row.updated_at,
                        "updated_by": row.updated_by,
                        "id": row.id
                    }
                )
                await db.commit()

            return SuccessResult(
                ray_id=ray_id,
                client_message=f"OAuth client {row.client_identifier} updated successfully"
            )
        except Exception as e:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Failed to update OAuth client {row.client_identifier}: {str(e)}",
                error_code="UPDATE_FAILED"
            )

    async def delete_by_id(self, id: str, ray_id: str) -> Union[SuccessResult, FailedResult]:
        """
        Delete an OAuth client by its ID.
        
        Args:
            id: Client ID to delete
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult if deletion succeeds, FailedResult otherwise
        """
        try:
            query = Query.from_(oauth_clients).delete().where(
                oauth_clients.id == Parameter(":id")
            )

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(str(query), {"id": id})
                await db.commit()
                
                if cursor.rowcount == 0:
                    return FailedResult(
                        ray_id=ray_id,
                        client_message=f"OAuth client with ID {id} not found",
                        error_code="NOT_FOUND"
                    )

            return SuccessResult(
                ray_id=ray_id,
                client_message=f"OAuth client with ID {id} deleted successfully"
            )
        except Exception as e:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Failed to delete OAuth client: {str(e)}",
                error_code="DELETE_FAILED"
            )


class OAuthClientConfigStore:
    """
    SQLite-based implementation for storing OAuth client configurations.
    Handles CRUD operations for client-specific settings (PKCE, TTLs, limits, etc.).
    """

    def __init__(self, db_path: str):
        """
        Initialize the OAuthClientConfigStore with a database connection path.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

    async def insert(self, config: "OAuthClientConfig", ray_id: str) -> Union[SuccessResult, FailedResult]:
        """
        Insert a new client configuration.
        
        Args:
            config: OAuthClientConfig dataclass instance
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult if insertion succeeds, FailedResult otherwise
        """
        try:
            from q_scope.implementations.store.sqllite.pypika_imp import oauth_client_configs
            
            query = Query.into(oauth_client_configs).columns(
                "client_id", "response_types", "require_pkce", "pkce_methods",
                "access_token_ttl", "refresh_token_ttl", "authorization_code_ttl",
                "max_active_access_tokens", "max_active_refresh_tokens",
                "device_code_ttl", "device_poll_interval", "metadata",
                "created_at", "created_by", "updated_at", "updated_by"
            ).insert(
                Parameter(":client_id"), Parameter(":response_types"), Parameter(":require_pkce"), Parameter(":pkce_methods"),
                Parameter(":access_token_ttl"), Parameter(":refresh_token_ttl"), Parameter(":authorization_code_ttl"),
                Parameter(":max_active_access_tokens"), Parameter(":max_active_refresh_tokens"),
                Parameter(":device_code_ttl"), Parameter(":device_poll_interval"), Parameter(":metadata"),
                Parameter(":created_at"), Parameter(":created_by"), Parameter(":updated_at"), Parameter(":updated_by")
            )

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    str(query),
                    {
                        "client_id": config.client_id,
                        "response_types": config.response_types,
                        "require_pkce": config.require_pkce,
                        "pkce_methods": config.pkce_methods,
                        "access_token_ttl": config.access_token_ttl,
                        "refresh_token_ttl": config.refresh_token_ttl,
                        "authorization_code_ttl": config.authorization_code_ttl,
                        "max_active_access_tokens": config.max_active_access_tokens,
                        "max_active_refresh_tokens": config.max_active_refresh_tokens,
                        "device_code_ttl": config.device_code_ttl,
                        "device_poll_interval": config.device_poll_interval,
                        "metadata": config.metadata,
                        "created_at": config.created_at,
                        "created_by": config.created_by,
                        "updated_at": config.updated_at,
                        "updated_by": config.updated_by
                    }
                )
                await db.commit()

            return SuccessResult(
                ray_id=ray_id,
                client_message=f"Client config for {config.client_id} inserted successfully"
            )
        except Exception as e:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Failed to insert client config: {str(e)}",
                error_code="INSERT_FAILED"
            )

    async def get_by_client_id(self, client_id: str, ray_id: str) -> Union[SuccessResult, FailedResult]:
        """
        Retrieve client configuration by client ID.
        
        Args:
            client_id: Client ID to retrieve config for
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult with OAuthClientConfig if found, FailedResult otherwise
        """
        try:
            from q_scope.implementations.store.sqllite.pypika_imp import oauth_client_configs
            from q_scope.implementations.datastrutures import OAuthClientConfig
            
            query = Query.from_(oauth_client_configs).select(
                "client_id", "response_types", "require_pkce", "pkce_methods",
                "access_token_ttl", "refresh_token_ttl", "authorization_code_ttl",
                "max_active_access_tokens", "max_active_refresh_tokens",
                "device_code_ttl", "device_poll_interval", "metadata",
                "created_at", "created_by", "updated_at", "updated_by"
            ).where(oauth_client_configs.client_id == Parameter(":client_id"))

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(str(query), {"client_id": client_id}) as cursor:
                    result = await cursor.fetchone()

                    if result is None:
                        return FailedResult(
                            ray_id=ray_id,
                            client_message=f"Client config for {client_id} not found",
                            error_code="NOT_FOUND"
                        )

                    config = OAuthClientConfig(
                        client_id=result["client_id"],
                        response_types=result["response_types"],
                        require_pkce=bool(result["require_pkce"]),
                        pkce_methods=result["pkce_methods"],
                        access_token_ttl=result["access_token_ttl"],
                        refresh_token_ttl=result["refresh_token_ttl"],
                        authorization_code_ttl=result["authorization_code_ttl"],
                        max_active_access_tokens=result["max_active_access_tokens"],
                        max_active_refresh_tokens=result["max_active_refresh_tokens"],
                        device_code_ttl=result["device_code_ttl"],
                        device_poll_interval=result["device_poll_interval"],
                        metadata=result["metadata"],
                        created_at=result["created_at"],
                        created_by=result["created_by"],
                        updated_at=result["updated_at"],
                        updated_by=result["updated_by"]
                    )

                    return SuccessResult(
                        ray_id=ray_id,
                        client_message=config
                    )
        except Exception as e:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Failed to retrieve client config: {str(e)}",
                error_code="FETCH_FAILED"
            )

    async def update(self, config: "OAuthClientConfig", ray_id: str) -> Union[SuccessResult, FailedResult]:
        """
        Update an existing client configuration.
        
        Args:
            config: OAuthClientConfig dataclass instance with updated values
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult if update succeeds, FailedResult otherwise
        """
        try:
            from q_scope.implementations.store.sqllite.pypika_imp import oauth_client_configs
            
            query = Query.update(oauth_client_configs).set(
                oauth_client_configs.response_types, Parameter(":response_types")
            ).set(
                oauth_client_configs.require_pkce, Parameter(":require_pkce")
            ).set(
                oauth_client_configs.pkce_methods, Parameter(":pkce_methods")
            ).set(
                oauth_client_configs.access_token_ttl, Parameter(":access_token_ttl")
            ).set(
                oauth_client_configs.refresh_token_ttl, Parameter(":refresh_token_ttl")
            ).set(
                oauth_client_configs.authorization_code_ttl, Parameter(":authorization_code_ttl")
            ).set(
                oauth_client_configs.max_active_access_tokens, Parameter(":max_active_access_tokens")
            ).set(
                oauth_client_configs.max_active_refresh_tokens, Parameter(":max_active_refresh_tokens")
            ).set(
                oauth_client_configs.device_code_ttl, Parameter(":device_code_ttl")
            ).set(
                oauth_client_configs.device_poll_interval, Parameter(":device_poll_interval")
            ).set(
                oauth_client_configs.metadata, Parameter(":metadata")
            ).set(
                oauth_client_configs.updated_at, Parameter(":updated_at")
            ).set(
                oauth_client_configs.updated_by, Parameter(":updated_by")
            ).where(oauth_client_configs.client_id == Parameter(":client_id"))

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    str(query),
                    {
                        "response_types": config.response_types,
                        "require_pkce": config.require_pkce,
                        "pkce_methods": config.pkce_methods,
                        "access_token_ttl": config.access_token_ttl,
                        "refresh_token_ttl": config.refresh_token_ttl,
                        "authorization_code_ttl": config.authorization_code_ttl,
                        "max_active_access_tokens": config.max_active_access_tokens,
                        "max_active_refresh_tokens": config.max_active_refresh_tokens,
                        "device_code_ttl": config.device_code_ttl,
                        "device_poll_interval": config.device_poll_interval,
                        "metadata": config.metadata,
                        "updated_at": config.updated_at,
                        "updated_by": config.updated_by,
                        "client_id": config.client_id
                    }
                )
                await db.commit()

            return SuccessResult(
                ray_id=ray_id,
                client_message=f"Client config for {config.client_id} updated successfully"
            )
        except Exception as e:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Failed to update client config: {str(e)}",
                error_code="UPDATE_FAILED"
            )

    async def delete_by_client_id(self, client_id: str, ray_id: str) -> Union[SuccessResult, FailedResult]:
        """
        Delete a client configuration by client ID.
        
        Args:
            client_id: Client ID to delete config for
            ray_id: Request tracking identifier
            
        Returns:
            SuccessResult if deletion succeeds, FailedResult otherwise
        """
        try:
            from q_scope.implementations.store.sqllite.pypika_imp import oauth_client_configs
            
            query = Query.from_(oauth_client_configs).delete().where(
                oauth_client_configs.client_id == Parameter(":client_id")
            )

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(str(query), {"client_id": client_id})
                await db.commit()
                
                if cursor.rowcount == 0:
                    return FailedResult(
                        ray_id=ray_id,
                        client_message=f"Client config for {client_id} not found",
                        error_code="NOT_FOUND"
                    )

            return SuccessResult(
                ray_id=ray_id,
                client_message=f"Client config for {client_id} deleted successfully"
            )
        except Exception as e:
            return FailedResult(
                ray_id=ray_id,
                client_message=f"Failed to delete client config: {str(e)}",
                error_code="DELETE_FAILED"
            )
