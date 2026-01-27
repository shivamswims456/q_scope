* * *

Project Context: Modular OAuth2 Framework (Python)
--------------------------------------------------

### **High-level Goal**

Build a **production-grade OAuth2 authorization server framework in Python** that is:

*   **RFC-compliant** (via `oauthlib`)
*   **Storage-agnostic** (pluggable backends)
*   **ASGI-first** (Starlette as the canonical implementation)
*   **Lightweight** (no heavy ORMs)
*   **Testable end-to-end** out of the box
*   **Extensible** without forking core code

This is a **framework**, not an app.

* * *

**Core Architectural Decisions**
--------------------------------

### 1\. OAuth2 Compliance

*   Use **`oauthlib` as the source of truth** for OAuth2 RFC behavior
*   Custom logic only wraps / adapts oauthlib
*   Explicitly **not** inventing OAuth semantics

* * *

### 2\. Supported OAuth2 Flows (v1.0 – confirmed)

**Included**

*   Authorization Code + **PKCE**
*   Client Credentials
*   Refresh Token
*   Resource Owner Password Credentials (**deprecated, but supported with warnings**)
*   **Device Authorization Flow (RFC 8628)**

**Excluded**

*   ❌ Implicit Flow (intentionally dropped)

* * *

### 3\. Storage Strategy (Important Design Choice)

You explicitly rejected ORMs.

**Final decision:**

*   ✅ **Raw SQL schema file** (`.sql`) for SQLite / Turso
*   ✅ Queries generated using **PyPika**
*   ✅ Execution via async drivers (`aiosqlite`, `libsql`)
*   ❌ No SQLAlchemy
*   ❌ No migration framework in v1

**Why this matters**

*   Storage is transparent and inspectable
*   Easier for users to re-implement storage
*   Works cleanly with Turso / libSQL
*   No hidden ORM behavior affecting OAuth semantics

SQLite/Turso is the **reference implementation**, not a hard dependency.

* * *

### 4\. Storage Abstraction Model

The framework exposes **abstract contracts only**:

*   Client store
*   Token store
*   Authorization grant store
*   Device code store
*   User authentication store

The default SQL implementation exists mainly for:

*   E2E tests
*   Reference behavior
*   Local/dev usage

Users are expected to **override storage**, not fork core.

* * *

### 5\. ASGI Strategy

*   One **Starlette-based ASGI app**
*   No framework-specific adapters (FastAPI, Quart, etc.)
*   ASGI interoperability is assumed and relied upon
*   OAuth server can be:
    *   mounted
    *   wrapped
    *   run standalone

No UI assumptions are baked in.

* * *

### 6\. User Authentication & Consent

*   Framework **does not own user login**
*   Authentication is done via **callbacks / hooks**
*   Consent UI is **integrator-provided**
*   Framework only enforces:
    *   redirect validation
    *   scope approval
    *   PKCE rules

This keeps the framework backend-only.

* * *

### 7\. Token Strategy

*   Default: **opaque tokens**
*   Token introspection supported (RFC 7662)
*   Token revocation supported (RFC 7009)
*   JWT is **explicitly deferred** (future extension)

* * *

### 8\. Schema-first Design

The SQL schema defines:

*   OAuth clients
*   Tokens (access + refresh)
*   Authorization codes
*   Device codes
*   Users (reference only)
*   Optional consent records

This schema is treated as **public API**, not an internal detail.

* * *

### 9\. Testing Philosophy

SQLite is not “just an example” — it enables:

*   Full OAuth2 E2E flows
*   RFC-level behavior testing
*   Storage contract tests
*   Deterministic CI runs

Anything that passes SQLite tests is expected to work on Turso.

* * *

### 10\. Explicit Non-Goals (v1)

*   ❌ OIDC
*   ❌ Admin UI
*   ❌ Client management UI
*   ❌ ORM-based models
*   ❌ OAuth1
*   ❌ Framework-specific plugins

* * *

One-line Summary
----------------

> **You’re building a storage-agnostic, ASGI-native, schema-first OAuth2 server framework in Python, using oauthlib for correctness, PyPika for SQL portability, and SQLite/Turso as the canonical reference backend.**

If you want, next we can:

*   Freeze **public APIs** (storage + server contracts)
*   Define **exact oauthlib integration boundaries**
*   Write a **non-code “architecture spec”** suitable for README / RFC-style docs
*   Or sanity-check this design against existing OAuth servers (Hydra, Authlib, Keycloak)

Just tell me where you want to go next.

## Prompt:
Write a non-code “architecture spec” suitable for README / RFC-style docs

## Response:
Below is a **non-code architecture specification** written in an **RFC / design-doc style**, suitable to live verbatim in a `README.md` or `/docs/architecture.md`.  
It deliberately avoids implementation details and code, and focuses on **contracts, responsibilities, and invariants**.

* * *

OAuth2 Framework — Architecture Specification
=============================================

**Status:** Draft  
**Target Release:** v1.0  
**Audience:** Framework users, contributors, auditors  
**Scope:** OAuth 2.0 Authorization Server (not OIDC)

* * *

1\. Purpose
-----------

This document specifies the architecture of a modular, storage-agnostic OAuth 2.0 authorization server framework written in Python.

The framework aims to provide:

*   RFC-compliant OAuth2 behavior
*   Clear separation of concerns
*   Extensibility without forking core logic
*   Predictable operational characteristics

This document is **normative** unless stated otherwise.

* * *

2\. Design Principles
---------------------

### 2.1 RFC Fidelity First

All OAuth2 semantics MUST follow the relevant RFCs.  
Custom logic MUST defer to RFC-defined behavior where applicable.

Primary references:

*   RFC 6749 (OAuth 2.0)
*   RFC 7636 (PKCE)
*   RFC 7009 (Token Revocation)
*   RFC 7662 (Token Introspection)
*   RFC 8628 (Device Authorization Grant)
*   RFC 8414 (Authorization Server Metadata)

* * *

### 2.2 Storage Agnosticism

The framework MUST NOT assume:

*   Any specific database
*   Any ORM
*   Any migration system

Storage is accessed exclusively through abstract contracts.

A SQLite / Turso implementation is provided as:

*   A reference implementation
*   A testing backend
*   A documentation aid

* * *

### 2.3 ASGI Native

The framework is ASGI-first and framework-agnostic.

A Starlette-based ASGI application is provided as the canonical runtime, relying on ASGI interoperability for integration with:

*   Starlette
*   FastAPI
*   Quart (ASGI mode)
*   Other ASGI servers

* * *

### 2.4 No Opinionated UI

The framework does not render:

*   Login pages
*   Consent screens
*   Admin dashboards

All user interaction is delegated to the integrator via callbacks.

* * *

### 2.5 Explicit Extensibility

All extensibility points are:

*   Documented
*   Contract-driven
*   Stable across minor versions

* * *

3\. High-Level Architecture
---------------------------

```
+----------------------+
|  ASGI Application    |
|  (Starlette-based)   |
+----------+-----------+
           |
           v
+----------------------+
|  OAuth2 Core Server  |
|  (oauthlib wrapper) |
+----------+-----------+
           |
           v
+----------------------+
|  Storage Interfaces  |
|  (Abstract)          |
+----------+-----------+
           |
           v
+----------------------+
|  Storage Backend     |
|  (SQLite/Turso/etc.) |
+----------------------+
```

* * *

4\. Core Components
-------------------

### 4.1 OAuth2 Core Server

The OAuth2 Core Server:

*   Wraps `oauthlib`
*   Owns protocol enforcement
*   Coordinates flows across storage and ASGI layers

**Responsibilities**

*   Grant type orchestration
*   Token issuance and revocation
*   PKCE validation
*   Device flow state transitions
*   Error normalization

**Non-responsibilities**

*   User authentication
*   UI rendering
*   Database-specific behavior

* * *

### 4.2 ASGI Application Layer

The ASGI layer:

*   Translates HTTP requests into OAuth2 requests
*   Translates OAuth2 responses into HTTP responses
*   Exposes standard OAuth2 endpoints

**Required Endpoints**

*   `/authorize`
*   `/token`
*   `/revoke`
*   `/introspect`
*   `/device_authorization`
*   `/.well-known/oauth-authorization-server`

**Constraints**

*   MUST support form-encoded requests
*   MUST return RFC-compliant error responses
*   MUST NOT enforce CORS policies

* * *

### 4.3 Storage Layer

The storage layer is defined entirely by abstract contracts.

**Required Logical Stores**

*   Client Store
*   Token Store
*   Authorization Grant Store
*   Device Code Store
*   User Store (authentication only)

**Storage Guarantees**

*   Atomicity per operation
*   Consistency across grant flows
*   FIFO revocation semantics (see §8)

* * *

### 4.4 Logging & Audit Layer

Logging is a first-class concern.

**Characteristics**

*   Based on Python logging
*   Structured logging via `structlog`
*   Separate audit-log abstraction

**Audit Log Requirements**

*   MUST be storage-backed
*   MUST be append-only
*   MUST be isolated from OAuth operational data
*   MUST support streaming and persistence

* * *

5\. Supported OAuth2 Grant Types
--------------------------------

### 5.1 Included (v1.0)

| Grant Type | Status |
| --- | --- |
| Authorization Code + PKCE | Required |
| Client Credentials | Required |
| Refresh Token | Required |
| Device Authorization | Required |
| Resource Owner Password | Optional (deprecated) |

### 5.2 Explicitly Excluded

*   Implicit Grant

* * *

6\. User Authentication Model
-----------------------------

The framework does not authenticate users.

**Authentication Model**

*   Integrator authenticates user externally
*   User context is injected into OAuth flow
*   Framework validates presence, not method

**Rationale**

*   Avoid coupling OAuth2 with identity systems
*   Support custom auth (SSO, LDAP, MFA, etc.)

* * *

7\. Consent Model
-----------------

The framework does not render consent screens.

**Consent Handling**

*   Framework provides consent metadata
*   Integrator renders UI
*   Integrator returns allow/deny decision

**Consent Metadata Includes**

*   Client identity
*   Requested scopes
*   User identity
*   Redirect URI

* * *

8\. Token Model & Revocation Semantics
--------------------------------------

### 8.1 Token Types

*   Access Tokens: short-lived, opaque
*   Refresh Tokens: long-lived, non-expiring unless revoked

### 8.2 Token Limits (FIFO)

**Client-level limit**

*   A client MAY have at most **N refresh tokens**
*   Oldest refresh tokens are revoked first

**Refresh-token-level limit**

*   A refresh token MAY issue at most **M access tokens**
*   Oldest access tokens are revoked first

**No Grace Period**

*   Rotation is strict
*   Old tokens are invalid immediately

* * *

9\. Device Authorization Flow
-----------------------------

**Characteristics**

*   User codes are:
    *   Case-insensitive
    *   Dashless
*   Polling interval:
    *   Client-configurable
    *   Enforced minimum by server

**UI**

*   Verification UI is integrator-provided
*   QR codes deferred to v1.1

* * *

10\. Password Grant (Deprecated)
--------------------------------

*   Disabled by default
*   Requires explicit opt-in
*   Emits warnings in:
    *   Logs
    *   Documentation

**No additional security restrictions enforced by framework**

* * *

11\. Scope Model
----------------

Scopes are:

*   Space-separated strings
*   Validated syntactically only

Semantic meaning is integrator-defined.

* * *

12\. Client Registration
------------------------

**v1.0 Policy**

*   Manual client registration only
*   No dynamic registration (RFC 7591 deferred)

Clients are expected to be provisioned via:

*   Admin tooling
*   SQL scripts
*   External systems

* * *

13\. Configuration Model
------------------------

Configuration is explicit and immutable at runtime.

**Configurable Domains**

*   Enabled grant types
*   Token lifetimes
*   Token limits
*   Logging behavior
*   Password grant opt-in
*   Device flow parameters

* * *

14\. Error Handling
-------------------

Errors:

*   MUST follow RFC error formats
*   MUST avoid leaking secrets
*   MAY be enriched in logs, not responses

* * *

15\. Testing Guarantees
-----------------------

The framework MUST:

*   Support full OAuth2 E2E testing via SQLite
*   Provide storage contract tests
*   Be deterministic in CI environments

* * *

16\. Versioning & Compatibility
-------------------------------

*   Semantic Versioning is enforced
*   Storage contracts are stable within a major version
*   Schema changes require migration guidance

* * *

17\. Explicit Non-Goals
-----------------------

This framework does not aim to:

*   Implement OIDC
*   Provide UI components
*   Manage users
*   Replace identity providers
*   Enforce deployment topology

* * *

18\. Summary
------------

This framework is:

*   Protocol-first
*   Storage-agnostic
*   ASGI-native
*   UI-neutral
*   Extensible by design

It is intended to be embedded, not operated standalone.

* * *

If you want, next we can:

*   Extract **“MUST / SHOULD / MAY” rules into a compliance checklist**
*   Write a **Threat Model & Security Assumptions doc**
*   Define **public API stability rules**
*   Produce a **storage contract spec** as a separate RFC-style document



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)
