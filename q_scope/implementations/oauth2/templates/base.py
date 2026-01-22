from abc import ABC, abstractmethod
from typing import Optional, Mapping, Any

from q_scope.implementations.datastrutures import Result



class OAuth2Authorization(ABC):
    """
    Base class for all OAuth2 authorization flows.

    This class defines the *lifecycle* of a flow.
    Concrete subclasses implement grant-specific logic.
    """

    def __init__(
        self,
        *,
        storage,
        clock,
        config,
        logger,
    ):
        """
        Dependencies are injected, not imported.

        - storage: composite database interface (CRUD-only)
        - clock: monotonic / wall-clock abstraction
        - config: immutable OAuth configuration
        - logger: structured logger
        """
        self._storage = storage
        self._clock = clock
        self._config = config
        self._logger = logger

    
    async def _run(self, context: Mapping[str, Any], ray_id:str) -> Mapping[str, Any]:
        """
        Execute the core flow logic.

        MUST return a serializable result.
        """
        ...


    @abstractmethod
    async def _preconditions(self, context: Mapping[str, Any], ray_id:str) -> None:
        """
        Validate flow-specific preconditions.

        MUST raise OAuth errors on failure.
        """
        ...


    @abstractmethod
    async def _postconditions(
        self,
        context: Mapping[str, Any],
        result: Mapping[str, Any],
        ray_id:str
    ) -> None:
        """
        Persist state, audit logs, etc.
        """
        ...

    def _log_start(self, context: Mapping[str, Any]) -> None:
        self._logger.info(
            "oauth.flow.start",
            flow=self.__class__.__name__,
        )

    

    def _log_success(
        self,
        context: Mapping[str, Any],
        result: Mapping[str, Any],
        ray_id: str
    ) -> None:
        self._logger.info(
            "oauth.flow.success",
            flow=self.__class__.__name__,
        )

    async def execute(self, *, context: Mapping[str, Any], ray_id:str) -> Mapping[str, Any]:
        """
        Execute the authorization flow.

        This method MUST NOT be overridden.
        """
        self._log_start(context)

        await self._preconditions(context, ray_id=ray_id)

        result = await self._run(context, ray_id=ray_id)

        await self._postconditions(context, result, ray_id=ray_id)

        self._log_success(context, result, ray_id=ray_id)

        return result

class Condition(ABC):
    """
    Base class for all OAuth flow conditions (pre or post).

    Conditions are executed in order.
    They must return a Result.
    """

    @abstractmethod
    async def validate(
        self,
        *,
        context: Mapping[str, Any],
        ray_id: str,
    ) -> Result:
        """
        Validate a single condition.

        MUST:
        - return SuccessResult to continue
        - return FailedResult to stop execution

        MUST NOT:
        - raise business exceptions
        - mutate config
        """
        ...

class ClientSecretGenerator(ABC):
    """
    Base abstraction for generating OAuth client secrets.

    This abstraction is responsible ONLY for generating a raw secret.
    It must NOT:
    - hash the secret
    - persist the secret
    - encode policy
    - encode identity into the secret

    The returned secret is expected to be:
    - high entropy
    - cryptographically secure
    - returned only once
    """

    @abstractmethod
    def generate_secret(self, *, user_id: str) -> str:
        """
        Generate a new raw client secret.

        Args:
            user_id: Owner of the client. Provided as contextual input
                     (for entropy mixing, audit, or HSM routing).
                     Must NOT reduce entropy or make output predictable.

        Returns:
            A raw client secret as a string.

        Raises:
            RuntimeError or lower-level exceptions on entropy failure.
        """
        ...

class ClientSecretHasher(ABC):
    """
    Base abstraction for hashing and verifying OAuth client secrets.

    Responsibilities:
    - Hash raw client secrets for storage
    - Verify raw client secrets against stored hashes

    This abstraction must NOT:
    - generate secrets
    - persist secrets
    - enforce policy
    - return Result objects

    Failures here are infrastructure-level and may raise exceptions.
    """

    @abstractmethod
    def hash(
        self,
        secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> str:
        """
        Hash a raw client secret for storage.

        Args:
            secret: Raw client secret
            user_id: Owner context (namespacing / salting / routing only)
            client_id: Client context (namespacing / salting / routing only)

        Returns:
            An opaque, self-contained hash string suitable for persistence.
        """
        ...

    @abstractmethod
    def verify(
        self,
        secret: str,
        hashed_secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> bool:
        """
        Verify a raw client secret against a stored hash.

        Args:
            secret: Raw client secret
            hashed_secret: Previously stored hash
            user_id: Owner context
            client_id: Client context

        Returns:
            True if the secret matches, False otherwise.
        """
        ...

