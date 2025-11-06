from abc import ABC, abstractmethod


class PreferencesSource(ABC):
    """Abstract base class for providing user-specific preferences.

    [`PreferencesSource`][group_genie.preferences.PreferencesSource] supplies user
    preferences that customize agent behavior and response style. Preferences are
    typically free-form text (often bullet points) describing formatting, tone,
    verbosity, and other stylistic choices.

    Preferences are included in agent prompts to personalize responses without
    modifying agent system prompts.

    Example:
        ```python
        class DatabasePreferencesSource(PreferencesSource):
            async def get_preferences(self, username: str) -> str | None:
                user = await database.get_user(username)
                if not user or not user.preferences:
                    return None

                return user.preferences
                # Example preferences:
                # "- Prefer concise responses
                #  - Use bullet points for lists
                #  - Include code examples when relevant
                #  - Avoid technical jargon"

        class StaticPreferencesSource(PreferencesSource):
            def __init__(self, preferences_map: dict[str, str]):
                self._preferences = preferences_map

            async def get_preferences(self, username: str) -> str | None:
                return self._preferences.get(username)
        ```
    """

    @abstractmethod
    async def get_preferences(self, username: str) -> str | None:
        """Retrieve preferences for a specific user.

        Args:
            username: User ID to fetch preferences for.

        Returns:
            Free-form text describing user preferences, or None if the user has
                no preferences configured. When None, preferences are not included
                in agent prompts.
        """
        ...
