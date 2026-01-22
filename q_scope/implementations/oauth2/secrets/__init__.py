import secrets
import base64
import hashlib

from argon2 import PasswordHasher, exceptions as argon2_exceptions
from q_scope.implementations.oauth2.templates.base import (
    ClientSecretGenerator,
    ClientSecretHasher
)


class DefaultClientSecretGenerator(ClientSecretGenerator):
    """
    Default secure client secret generator.

    Properties:
    - Cryptographically secure randomness
    - URL-safe output
    - Fixed minimum entropy
    - Stateless
    """

    def __init__(self, *, byte_length: int = 32):
        """
        Args:
            byte_length:
                Number of random bytes before encoding.
                32 bytes ≈ 256 bits of entropy (strong for long-lived secrets).
        """
        if byte_length < 32:
            raise ValueError("byte_length must be at least 32 bytes")

        self._byte_length = byte_length

    def generate_secret(self, *, user_id: str) -> str:
        # NOTE:
        # user_id is intentionally NOT embedded directly.
        # We only use it for optional entropy mixing.

        random_bytes = secrets.token_bytes(self._byte_length)

        # Optional entropy mixing (does NOT reduce entropy)
        # This prevents subtle weaknesses if RNG is ever compromised.
        mix = hashlib.sha256(user_id.encode("utf-8")).digest()

        combined = bytes(a ^ b for a, b in zip(random_bytes, mix))

        # URL-safe, copy/paste friendly
        secret = base64.urlsafe_b64encode(combined).decode("ascii").rstrip("=")

        return secret



class Argon2ClientSecretHasher(ClientSecretHasher):
    """
    Default Argon2-based hasher for OAuth client secrets.

    Uses Argon2id with strong defaults.
    Hashes are self-describing and safe to persist verbatim.
    """

    def __init__(
        self,
        *,
        time_cost: int = 3,
        memory_cost: int = 64 * 1024,  # 64 MB
        parallelism: int = 1,
        hash_len: int = 32,
        salt_len: int = 16,
    ):
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    # -------- public API --------

    def hash(
        self,
        secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> str:
        if not secret:
            raise ValueError("secret must not be empty")

        contextual_secret = self._contextualize_secret(
            secret, user_id, client_id
        )

        return self._hasher.hash(contextual_secret)

    def verify(
        self,
        secret: str,
        hashed_secret: str,
        *,
        user_id: str,
        client_id: str,
    ) -> bool:
        contextual_secret = self._contextualize_secret(
            secret, user_id, client_id
        )

        try:
            return self._hasher.verify(
                hashed_secret, contextual_secret
            )
        except argon2_exceptions.VerifyMismatchError:
            return False
        except argon2_exceptions.InvalidHash:
            return False


    def _contextualize_secret(
        self,
        secret: str,
        user_id: str,
        client_id: str,
    ) -> str:
        """
        Bind user_id and client_id to the secret without reducing entropy.

        This prevents:
        - cross-client hash reuse
        - secret transplant attacks

        This does NOT:
        - make secrets predictable
        - encode identity in plaintext
        """
        context = f"{user_id}:{client_id}".encode("utf-8")
        context_hash = hashlib.sha256(context).hexdigest()

        return f"{secret}:{context_hash}"


