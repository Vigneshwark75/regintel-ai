from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from regintel_domain import UserRole
from regintel_shared.config import Settings, get_settings

# Demo-only in-memory user store, mapping username -> (password, role). A real
# deployment swaps this for an identity provider (SSO/LDAP/etc.) — nothing else
# in this module needs to change, since everything downstream only cares about
# the (username, role) pair a login produces.
_DEMO_USERS: dict[str, tuple[str, UserRole]] = {
    "cro": ("cro-demo-password", UserRole.CRO),
    "compliance": ("compliance-demo-password", UserRole.COMPLIANCE_OFFICER),
    "risk": ("risk-demo-password", UserRole.RISK),
    "auditor": ("auditor-demo-password", UserRole.AUDITOR),
    "ops": ("ops-demo-password", UserRole.OPS),
}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthenticatedUser(BaseModel):
    username: str
    role: UserRole


def authenticate(username: str, password: str) -> UserRole | None:
    record = _DEMO_USERS.get(username)
    if record is None or record[0] != password:
        return None
    return record[1]


def create_access_token(username: str, role: UserRole, settings: Settings) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": username, "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username = payload["sub"]
        role = UserRole(payload["role"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise credentials_error from exc
    return AuthenticatedUser(username=username, role=role)


def require_roles(*roles: UserRole) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    def dependency(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' is not permitted to perform this action",
            )
        return user

    return dependency
