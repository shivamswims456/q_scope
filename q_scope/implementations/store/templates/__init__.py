from typing import Generic, TypeVar, Optional, Iterable
from abc import ABC, abstractmethod

from q_scope.implementations.datastrutures import AccessToken, AuditLog, AuthorizationCode, DeviceCode, OAuthClient, RefreshToken

T = TypeVar("T")


class BaseTable(Generic[T], ABC):
    """
    Base class for a single database table.

    Implements standard CRUD shape.
    Concrete implementations decide *how* rows are persisted.
    """

    @abstractmethod
    async def insert(self, row: T, ray_id:str) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, id: str, ray_id:str) -> Optional[T]:
        ...

    @abstractmethod
    async def update(self, row: T, ray_id:str) -> None:
        ...

    @abstractmethod
    async def delete_by_id(self, id: str, ray_id:str) -> None:
        ...




class ClientTable(BaseTable[OAuthClient], ABC):
    @abstractmethod
    async def get_by_client_identifier(
        self,
        client_identifier: str,
        ray_id:str
    ) -> Optional[OAuthClient]:
        ...



class AuthorizationCodeTable(BaseTable[AuthorizationCode], ABC):
    @abstractmethod
    async def get_by_code(
        self,
        code: str,
        ray_id:str
    ) -> Optional[AuthorizationCode]:
        ...

    @abstractmethod
    async def delete_by_code(
        self,
        code: str,
        ray_id:str
    ) -> None:
        ...


class AccessTokenTable(BaseTable[AccessToken], ABC):
    @abstractmethod
    async def get_by_token(
        self,
        token: str,
        ray_id:str
    ) -> Optional[AccessToken]:
        ...

    async def delete_by_token(self, token: str, ray_id:str) -> None:
        """
        Optional convenience.
        Default implementation delegates to get_by_token + delete_by_id.
        """
        row = await self.get_by_token(token, ray_id=ray_id)
        if row is not None:
            await self.delete_by_id(row.id, ray_id=ray_id)

    @abstractmethod
    async def count_by_refresh_token(
        self,
        refresh_token_id: str,
        ray_id: str
    ) -> int:
        """
        Count active access tokens associated with a refresh token.
        Required for token limit enforcement.
        """
        ...

    @abstractmethod
    async def get_oldest_by_refresh_token(
        self,
        refresh_token_id: str,
        ray_id: str
    ) -> Optional[AccessToken]:
        """
        Get the oldest active access token associated with a refresh token.
        Required for FIFO revocation.
        """
        ...



class RefreshTokenTable(BaseTable[RefreshToken], ABC):
    @abstractmethod
    async def get_by_token(
        self,
        token: str,
        ray_id:str
    ) -> Optional[RefreshToken]:
        ...


class DeviceCodeTable(BaseTable[DeviceCode], ABC):
    @abstractmethod
    async def get_by_device_code(
        self,
        device_code: str,
        ray_id:str
    ) -> Optional[DeviceCode]:
        ...

    @abstractmethod
    async def get_by_user_code(
        self,
        user_code: str,
        ray_id:str
    ) -> Optional[DeviceCode]:
        ...



class AuditLogTable(BaseTable[AuditLog], ABC):
    async def update(self, row: AuditLog, ray_id:str) -> None:
        raise NotImplementedError("audit_log is append-only")

    async def delete_by_id(self, id: str, ray_id:str) -> None:
        raise NotImplementedError("audit_log is append-only")

