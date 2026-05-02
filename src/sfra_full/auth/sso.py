"""APTRANSCO SSO placeholder — wired up in Phase 3.

Spec v2 §2: ``auth/sso.py`` exists as a clear hook for integrating with
APTRANSCO's identity provider once its details are confirmed. For now
this module returns a 501 NOT IMPLEMENTED response with the field set
needed for the eventual SAML / OIDC flow.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/api/auth/sso", tags=["auth"])


@router.get("/login")
def sso_login() -> dict:
    """Initiate SSO login. Returns the IdP redirect URL once configured."""
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "APTRANSCO SSO not yet configured. Use /api/auth/login with username + password.",
    )


@router.post("/callback")
def sso_callback() -> dict:
    """SSO assertion callback (SAML POST or OIDC code exchange)."""
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "APTRANSCO SSO callback not yet configured.",
    )


__all__ = ["router"]
