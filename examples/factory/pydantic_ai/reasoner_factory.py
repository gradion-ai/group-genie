# --8<-- [start:imports]
from functools import partial

from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from examples.utils import load_reasoner_template
from group_genie.agent.provider.pydantic_ai import DefaultGroupReasoner
from group_genie.reasoner import GroupReasoner, GroupReasonerFactory
from group_genie.secrets import SecretsProvider

# --8<-- [end:imports]


# --8<-- [start:create-group-reasoner]
def create_group_reasoner(
    system_template: str,
    secrets: dict[str, str],
    owner: str,
) -> GroupReasoner:
    model = GoogleModel(
        "gemini-3-flash-preview",
        provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
    )
    return DefaultGroupReasoner(
        system_prompt=system_template.format(owner=owner),
        model=model,
    )


# --8<-- [end:create-group-reasoner]


# --8<-- [start:group-reasoner-factory]
def get_group_reasoner_factory(
    secrets_provider: SecretsProvider | None = None,
    template_name: str = "general_assist",
):
    system_template = load_reasoner_template(template_name)
    return GroupReasonerFactory(
        group_reasoner_factory_fn=partial(create_group_reasoner, system_template),
        secrets_provider=secrets_provider,
    )


# --8<-- [end:group-reasoner-factory]
