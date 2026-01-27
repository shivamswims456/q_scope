import time
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from q_scope.implementations.oauth2.asgi.endpoints.refresh_token.controller import RefreshTokenController
from q_scope.implementations.oauth2.asgi.endpoints.refresh_token.view import RefreshTokenView
from q_scope.implementations.oauth2.oauth_flows.refresh_token_flow import RefreshTokenFlow


async def token_endpoint(request: Request) -> JSONResponse:
    # Resolve dependencies from app state
    flow: RefreshTokenFlow = request.app.state.refresh_token_flow
    
    # Initialize MVC components
    view = RefreshTokenView()
    controller = RefreshTokenController(flow, view)
    
    ray_id = request.headers.get("X-Request-ID", str(time.time()))
    return await controller.handle_token_request(request, ray_id)


routes = [
    Route("/token", token_endpoint, methods=["POST"]),
]
