---
id: okta-sso
name: Okta Single Sign-On
updated: 2026-04-22
audience: Okta administrators, platform engineers
---

# Okta Single Sign-On

AMIE supports Okta Verify / Okta SSO through the OpenID Connect
Authorization Code + PKCE flow. The SPA authenticates directly against
Okta, receives an access token, and presents it as a bearer token on
every API call. The backend validates the token against Okta's JWKS.

No refresh token is stored in the browser; a silent re-auth is initiated
if the token expires.

## Architecture

```
  [SPA]  --1. click Sign in-->  [Okta /authorize]
    |
    |<--2. redirect with code---
    |
    |--3. POST code + PKCE--->  [Okta /token]
    |
    |<--4. access_token, id_token---
    |
    |--5. Authorization: Bearer ...--->  [AMIE backend]
                                             |
                                             |--6. fetch & cache JWKS--> [Okta /keys]
                                             |
                                             |--7. verify signature, iss, aud, exp
                                             |
                                             |--8. attach user to request context
```

1. The SPA fetches `/api/auth/config` on boot to learn whether SSO is
   enabled and which issuer and client id to use.
2. On the sign-in button it generates a PKCE verifier, stores the state
   in `sessionStorage`, and redirects to Okta `/authorize`.
3. Okta authenticates the user and redirects back to
   `/auth/callback?code=...&state=...`.
4. The SPA validates `state`, exchanges the code for tokens at Okta
   `/token`, and stores them in `sessionStorage` for the session.
5. Every subsequent API call includes `Authorization: Bearer
   <access_token>`.
6. The backend caches the Okta JWKS for one hour, validates the token,
   and attaches the user to the request context.

## Okta configuration

### 1. Create a SPA application

Okta Admin Console > Applications > Create App Integration:

- **Sign-in method:** OIDC - OpenID Connect
- **Application type:** Single-Page Application (SPA)
- **Grant type:** Authorization Code + Refresh Token
- **Sign-in redirect URIs:** `https://amie.usps.gov/auth/callback`
  (plus `http://localhost:5173/auth/callback` for dev)
- **Sign-out redirect URIs:** `https://amie.usps.gov`
  (plus `http://localhost:5173` for dev)
- **Controlled access:** choose the groups that should be allowed to
  use AMIE. Okta enforces this before a token is ever issued.

Save the **Client ID**. There is no client secret for a SPA.

### 2. Configure an Authorization Server

Admin Console > Security > API:

- Use the built-in `default` server, or create one named `amie`.
- **Audience:** `api://usps-amie` (or whatever value you set in
  `OKTA_AUDIENCE`).
- **Scopes:** `openid`, `profile`, `email`, `offline_access`.
- **Claims:** add a `groups` claim filter so the backend can read
  group membership.
- **Access policies:** assign the SPA client and the allowed groups.

Note the **Issuer URI**. It looks like
`https://dev-12345.okta.com/oauth2/default`.

### 3. Configure AMIE

Edit `.env`:

```bash
AUTH_ENABLED=true
OKTA_ENABLED=true
OKTA_ISSUER=https://dev-12345.okta.com/oauth2/default
OKTA_CLIENT_ID=0oaXXXXXXXXXXXXX
OKTA_AUDIENCE=api://usps-amie
OKTA_SCOPES=openid profile email offline_access

VITE_OKTA_ENABLED=true
VITE_OKTA_ISSUER=https://dev-12345.okta.com/oauth2/default
VITE_OKTA_CLIENT_ID=0oaXXXXXXXXXXXXX
VITE_OKTA_AUDIENCE=api://usps-amie
VITE_OKTA_REDIRECT_URI=http://localhost:5173/auth/callback
VITE_OKTA_POST_LOGOUT_URI=http://localhost:5173
```

Restart the backend. It will fetch
`https://dev-12345.okta.com/oauth2/default/v1/keys` on first verify and
cache the JWKS for one hour.

The `VITE_*` duplicates exist so the SPA can start the login flow even
before `/api/auth/config` returns, which matters during the very first
boot while Okta is still handshaking.

### 4. Verify

```bash
# Backend publishes its config
curl http://localhost:8000/api/auth/config
# {"enabled":true,"provider":"okta","issuer":"https://...","client_id":"...","audience":"api://usps-amie","scopes":["openid","profile","email","offline_access"],"redirect_path":"/auth/callback"}

# Rejects requests without a token
curl -i http://localhost:8000/api/auth/me
# HTTP/1.1 401 Unauthorized

# Accepts a valid Okta access token
TOKEN=...
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/me
```

## Group-based authorization

The backend attaches `groups` to the request context. Guard any route
or feature with a small dependency:

```python
from fastapi import Depends, HTTPException, status

def require_group(group_name: str):
    def _dep(user: dict = Depends(get_current_user)) -> dict:
        if group_name not in user.get("groups", []):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not authorized")
        return user
    return _dep

@router.get("/admin/analytics")
async def admin(_: dict = Depends(require_group("amie-admins"))):
    ...
```

## Token lifecycle

| Token | Stored where | TTL | Notes |
|---|---|---|---|
| Access token | `sessionStorage` | Okta default, typically 1 hour | Sent as `Authorization: Bearer` |
| ID token | `sessionStorage` | Same as access | Used for logout `id_token_hint` |
| Refresh token | Not stored | n/a | SPA re-auths silently when the token expires |

When an access token expires, the next API call returns `401`. The SPA
catches this in `useAuth.initialize()` on the next reload and kicks
off a fresh `/authorize` flow. For silent re-auth without reload,
implement `prompt=none` against the authorize endpoint in
`beginLogin`.

## Logout

Clicking the sign-out icon in the sidebar:

1. Clears the `sessionStorage` tokens.
2. Redirects to Okta's end-session endpoint
   `/v1/logout?id_token_hint=...&post_logout_redirect_uri=...`.
3. Okta ends the Okta session and redirects back to
   `VITE_OKTA_POST_LOGOUT_URI`.

## Security considerations

- **PKCE is mandatory.** SPAs cannot safely hold a client secret, so
  `code_challenge` + `code_verifier` proves the callback came from the
  same origin that initiated the flow.
- **Strict redirect URIs.** Only the URIs configured in Okta are
  accepted. If a URI is added in code, it must also be registered in
  Okta.
- **State parameter.** The SPA generates 32 bytes of randomness per
  login, stores it in `sessionStorage`, and rejects callbacks whose
  state does not match.
- **JWKS rotation.** The backend refreshes the JWKS cache once per hour
  and retries once on an unknown `kid`, so Okta-initiated key rotations
  are automatic.
- **Bearer token exposure.** The token lives in `sessionStorage`, not
  `localStorage`, so it is cleared when the tab closes. It is never
  logged by the backend. XSS still gets the token; follow
  `docs/security.md` for CSP and XSS mitigations.
- **Groups claim size.** Okta puts group IDs in the token. For users
  in very many groups, the token can exceed 8 KB. Increase the server
  header buffer or use a groups filter.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Login loop (Okta redirects back, backend returns 401) | Audience mismatch | Ensure `OKTA_AUDIENCE` equals the Audience on the Okta authorization server, not the client id |
| `no matching JWKS key` | Token issued by a different server | Make sure `OKTA_ISSUER` matches the authorization server that signed the token |
| `state mismatch` in the SPA | `sessionStorage` cleared mid-flow | Do not open the callback URL in a new tab; re-run the login |
| `token missing kid` | Token is not JWT-formatted (opaque token) | Confirm the authorization server is set to `JWT`, not `Opaque` |
| CORS error on `/api/auth/me` | Origin not in `CORS_ORIGINS` | Add the SPA origin to `CORS_ORIGINS` |

## Dev-mode fallback

If `AUTH_ENABLED=false` the backend issues a synthetic `dev-user` and
the SPA skips the login screen entirely. This is intended for local
development and CI. Never deploy with `AUTH_ENABLED=false` to an
environment exposed to the internet.

## See also

- `docs/security.md` for the broader threat model.
- `docs/config.md` for every auth environment variable.
- `backend/app/core/security.py` for the JWT verifier.
- `frontend/src/lib/oidc.ts` for the PKCE client.
