from typing import Any, Mapping

from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

from q_scope.implementations.errors.exceptions import OAuthException


class RefreshTokenView:
    def success(self, data: Mapping[str, Any]) -> JSONResponse:
        return JSONResponse(data)

    def error(self, exception: Exception) -> JSONResponse:
        if isinstance(exception, OAuthException):
            # Map internal error codes to RFC 6749 error codes
            # e.g. "oauth.invalid_client" -> "invalid_client"
            rfc_error = exception.error_code.replace("oauth.", "")
            
            status_code = HTTP_400_BAD_REQUEST
            if rfc_error == "invalid_client":
                status_code = HTTP_401_UNAUTHORIZED
            
            return JSONResponse(
                {
                    "error": rfc_error,
                    "error_description": exception.client_message or exception.message
                },
                status_code=status_code
            )
        
        # Unexpected server error
        print(f"Server Error: {exception}")
        return JSONResponse(
            {"error": "server_error", "error_description": "Internal server error"},
            status_code=HTTP_500_INTERNAL_SERVER_ERROR
        )

    def invalid_request(self, message: str) -> JSONResponse:
        return JSONResponse(
            {"error": "invalid_request", "error_description": message},
            status_code=HTTP_400_BAD_REQUEST
        )

    def unauthorized_client(self, message: str) -> JSONResponse:
        return JSONResponse(
            {"error": "invalid_client", "error_description": message},
            status_code=HTTP_401_UNAUTHORIZED
        )

    def unsupported_grant_type(self) -> JSONResponse:
        return JSONResponse(
            {"error": "unsupported_grant_type", "error_description": "Only refresh_token grant is supported"},
            status_code=HTTP_400_BAD_REQUEST
        )
