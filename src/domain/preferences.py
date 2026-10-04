"""Per-player notification preferences (category on/off toggles)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.domain.notification import NotificationCategory


def _all_enabled() -> dict[NotificationCategory, bool]:
    return {category: True for category in NotificationCategory}


class NotificationPreferences(BaseModel):
    """Immutable value object. Opt-out model: anything not disabled is enabled."""

    model_config = ConfigDict(frozen=True)

    player_id: int
    enabled: dict[NotificationCategory, bool] = Field(default_factory=_all_enabled)

    @classmethod
    def default(cls, player_id: int) -> NotificationPreferences:
        return cls(player_id=player_id)

    def is_enabled(self, category: NotificationCategory) -> bool:
        return self.enabled.get(category, True)

    def with_category(
        self, category: NotificationCategory, enabled: bool
    ) -> NotificationPreferences:
        """Return a copy with one category toggled."""
        return self.model_copy(update={"enabled": {**self.enabled, category: enabled}})
