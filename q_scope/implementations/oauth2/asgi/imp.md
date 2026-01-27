# ASGI Application Implementation

## Purpose

The `asgi/` directory contains the Starlette-based ASGI application that exposes the OAuth2 Refresh Token service. This layer handles HTTP requests, input validation, and invokes the core OAuth2 flows.

## Architecture Context

```
External Client
       ↓
    (HTTP)
       ↓
┌──────────────────────────────────────┐
│          ASGI LAYER (app.py)         │
│  - Parse JSON Request                │
│  - Validate Headers                  │
│  - Handle Lifespan                   │
└──────────────────────────────────────┘
       ↓
    (Context)
       ↓
┌──────────────────────────────────────┐
│      OAUTH2 FLOW (RefreshToken)      │
└──────────────────────────────────────┘
```

## Key Components

### `app.py`
The main entry point for the Starlette application.

**Responsibilities**:
- **Lifespan Management**: Initializes storage, clock, hasher, and flow instances.
- **Routing**: Defines the `/token` endpoint.
- **Request Parsing**: Extracts parameters from JSON body.
- **Error Handling**: Converts `OAuthException` to RFC-compliant JSON responses.

### Dependencies
- **Starlette**: Web framework.
- **Uvicorn**: ASGI server.
- **OAuth Flows**: `RefreshTokenFlow`.
- **Storage**: `SQLiteStore` (or other implementation).

## Usage

### Running the Server
```bash
uvicorn q_scope.implementations.oauth2.asgi.app:app --reload
```

### Token Request Example
```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "refresh_token",
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret"
  }'
```
