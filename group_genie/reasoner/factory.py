from typing import Any, Callable

from group_sense import GroupReasonerFactory as GroupReasonerFactoryBase

from group_genie.reasoner.base import GroupReasoner
from group_genie.secrets import SecretsProvider

GroupReasonerFactoryFn = Callable[[dict[str, str], str], GroupReasoner]
"""Factory function signature for creating group reasoners.

Creates reasoner instances customized for specific users (owners). Each user typically
gets their own reasoner instance to enable concurrent reasoning for different users.

Args:
    secrets (dict[str, str]): User-specific credentials (e.g., API keys) retrieved from a
        [`SecretsProvider`][group_genie.secrets.SecretsProvider]. Common keys include
        "GOOGLE_API_KEY", "BRAVE_API_KEY", etc.
    owner (str): Username of the reasoner owner. Can be used to personalize behavior (e.g.,
        formatting system prompts with the owner's name).

Returns:
    A configured [`GroupReasoner`][group_genie.reasoner.base.GroupReasoner] instance
        for the specified owner.

Example:
    ```python
    def create_reasoner(secrets: dict[str, str], owner: str) -> GroupReasoner:
        template = "You are assisting {owner} in a group chat..."
        system_prompt = template.format(owner=owner)
        model = GoogleModel(
            "gemini-2.5-flash",
            provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
        )
        return DefaultGroupReasoner(
            system_prompt=system_prompt,
            model=model,
        )
    ```
"""


class GroupReasonerFactory(GroupReasonerFactoryBase):
    """Factory for creating group reasoner instances.

    [`GroupReasonerFactory`][group_genie.reasoner.factory.GroupReasonerFactory]
    creates reasoner instances customized for specific users (owners). It provides
    user-specific secrets and stores idle timeout configuration.

    Each user typically gets their own reasoner instance to maintain independent
    reasoning state and conversation history.

    Example:
        ```python
        def create_reasoner(secrets: dict[str, str], owner: str) -> GroupReasoner:
            template = "You are assisting {owner} in a group chat..."
            system_prompt = template.format(owner=owner)
            return DefaultGroupReasoner(system_prompt=system_prompt)

        factory = GroupReasonerFactory(
            group_reasoner_factory_fn=create_reasoner,
            group_reasoner_idle_timeout=600,
            secrets_provider=my_secrets_provider,
        )

        # Factory creates reasoner for specific user
        reasoner = factory.create_group_reasoner(owner="alice")
        ```
    """

    def __init__(
        self,
        group_reasoner_factory_fn: GroupReasonerFactoryFn,
        group_reasoner_idle_timeout: float | None = None,
        secrets_provider: SecretsProvider | None = None,
    ):
        """Initialize the group reasoner factory.

        Args:
            group_reasoner_factory_fn: Factory function that creates a GroupReasoner
                for a specific owner. Receives secrets and owner ID.
            group_reasoner_idle_timeout: Optional timeout in seconds after which an idle
                reasoner is stopped to free resources. Defaults to 600s (10 minutes).
            secrets_provider: Optional provider for user-specific secrets (e.g., API keys).
        """
        self._group_reasoner_factory_fn = group_reasoner_factory_fn
        self._group_reasoner_idle_timeout = group_reasoner_idle_timeout or 600
        self._secrets_provider = secrets_provider

    @property
    def group_reasoner_idle_timeout(self) -> float | None:
        return self._group_reasoner_idle_timeout

    def create_group_reasoner(self, owner: str, **kwargs: Any) -> GroupReasoner:
        """Create a group reasoner instance for a specific owner.

        Retrieves secrets for the owner and creates a reasoner instance using the
        factory function.

        Args:
            owner: User ID of the reasoner owner.
            **kwargs: Additional keyword arguments passed to the factory function.

        Returns:
            A new [`GroupReasoner`][group_genie.reasoner.base.GroupReasoner] instance
                configured for the owner.
        """
        secrets = self._get_secrets(owner)
        return self._group_reasoner_factory_fn(secrets, owner, **kwargs)

    def _get_secrets(self, owner: str) -> dict[str, str]:
        if self._secrets_provider is None:
            return {}
        return self._secrets_provider.get_secrets(owner) or {}
