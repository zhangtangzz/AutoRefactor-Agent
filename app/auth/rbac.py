from enum import Enum
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.auth.jwt_handler import TokenPayload, get_current_user


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


# 角色权限矩阵
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN: {
        "ask", "upload", "delete_doc", "list_docs",
        "manage_users", "view_stats",
    },
    Role.USER: {
        "ask", "upload", "list_docs",
    },
    Role.VIEWER: {
        "ask", "list_docs",
    },
}


def require_role(*allowed_roles: Role) -> Callable:
    async def role_checker(
        current_user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        user_role = Role(current_user.role)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


def require_permission(permission: str) -> Callable:
    async def permission_checker(
        current_user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        user_role = Role(current_user.role)
        allowed = ROLE_PERMISSIONS.get(user_role, set())
        if permission not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {permission}",
            )
        return current_user

    return permission_checker
