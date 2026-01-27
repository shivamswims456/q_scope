from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Mount

from q_scope.implementations.oauth2.asgi.dependencies import Dependencies
from q_scope.implementations.oauth2.oauth_flows.refresh_token_flow import RefreshTokenFlow

# Import Routers
from q_scope.implementations.oauth2.asgi.endpoints.refresh_token.router import routes as refresh_token_routes


@asynccontextmanager
async def lifespan(app: Starlette):
    # Initialize shared dependencies
    deps = Dependencies.get_instance()

    # Initialize Flows
    # We store flows in app.state for easy access in routers/controllers
    app.state.refresh_token_flow = RefreshTokenFlow(
        storage=deps.storage,
        clock=deps.clock,
        config=deps.config,
        logger=deps.logger,
        secret_hasher=deps.hasher
    )
    
    yield
    # Cleanup if needed


# Mount modular routes
routes = [
    Mount("/", routes=refresh_token_routes),
]

app = Starlette(
    debug=True,
    routes=routes,
    lifespan=lifespan,
)
