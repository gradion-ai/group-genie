# --8<-- [start:imports]
import os

from group_genie.secrets import SecretsProvider

# --8<-- [end:imports]


# --8<-- [start:secrets-provider]
class EnvironmentSecretsProvider(SecretsProvider):
    def get_secrets(self, username: str) -> dict[str, str] | None:
        # For development: use environment variables for all users
        var_names = ["OPENAI_API_KEY", "GOOGLE_API_KEY", "BRAVE_API_KEY"]
        return {var_name: os.getenv(var_name, "") for var_name in var_names}


# --8<-- [end:secrets-provider]
