import time
import json
import base64
from typing import Any, Mapping

from starlette.requests import Request
from starlette.responses import JSONResponse

from q_scope.implementations.oauth2.asgi.endpoints.refresh_token.view import RefreshTokenView
from q_scope.implementations.oauth2.oauth_flows.refresh_token_flow import RefreshTokenFlow


class RefreshTokenController:
    def __init__(self, flow: RefreshTokenFlow, view: RefreshTokenView):
        self._flow = flow
        self._view = view

    async def handle_token_request(self, request: Request, ray_id: str) -> JSONResponse:
        # 1. Parse Request
        try:
            if request.headers.get("content-type") == "application/json":
                body = await request.json()
            else:
                return self._view.invalid_request("Content-Type must be application/json")
        except json.JSONDecodeError:
            return self._view.invalid_request("Invalid JSON body")

        grant_type = body.get("grant_type")
        
        # 2. Basic Validation
        if grant_type != "refresh_token":
            return self._view.unsupported_grant_type()

        # 3. Extract Credentials
        client_id = body.get("client_id")
        client_secret = body.get("client_secret")
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Basic "):
            try:
                encoded = auth_header[6:]
                decoded = base64.b64decode(encoded).decode("utf-8")
                if ":" in decoded:
                    client_id, client_secret = decoded.split(":", 1)
            except Exception:
                return self._view.unauthorized_client("Invalid Basic Auth header")

        # 4. Build Context
        context = {
            "refresh_token": body.get("refresh_token"),
            "scope": body.get("scope"),
            "client_id": client_id,
            "client_secret": client_secret,
        }

        # 5. Execute Flow
        try:
            result = await self._flow.execute(context=context, ray_id=ray_id)
            return self._view.success(result)
        except Exception as e:
            return self._view.error(e)
