from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class UserContext:
    username: str
    plan: str
    locale: str
    organization: str
    feature_flags: Dict[str, bool]


class UserManagementService:
    """In-memory user registry that exposes plan and locale configuration."""

    _USERS: Dict[str, UserContext] = {
        "sohail": UserContext(
            username="sohail",
            plan="team",
            locale="en",
            organization="DevGuardian Labs",
            feature_flags={
                "advanced_monitoring": True,
                "priority_support": True,
                "krutrim_access": False,
            },
        ),
        "anika": UserContext(
            username="anika",
            plan="pro",
            locale="hi",
            organization="DevGuardian India",
            feature_flags={
                "advanced_monitoring": False,
                "priority_support": False,
                "krutrim_access": True,
            },
        ),
    }

    def get_user_context(self, username: str) -> UserContext:
        return self._USERS.get(
            username,
            UserContext(
                username=username,
                plan="free",
                locale="en",
                organization="Community",
                feature_flags={
                    "advanced_monitoring": False,
                    "priority_support": False,
                    "krutrim_access": False,
                },
            ),
        )
