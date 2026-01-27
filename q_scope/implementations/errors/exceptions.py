from typing import Any, Optional

class OAuthException(Exception):
    """
    Base exception for OAuth2 flow errors.
    """
    def __init__(self, error_code: str, message: str, client_message: Optional[Any] = None):
        self.error_code = error_code
        self.message = message
        self.client_message = client_message
        super().__init__(message)
