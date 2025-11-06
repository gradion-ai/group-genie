# --8<-- [start:imports]
import os

from group_genie.secrets import SecretsProvider

# --8<-- [end:imports]


# --8<-- [start:secrets-provider]
class EnvironmentSecretsProvider(SecretsProvider):
    def get_secrets(self, username: str) -> dict[str, str] | None:
        # For development: use environment variables for all users
        return {
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
            "BRAVE_API_KEY": os.getenv("BRAVE_API_KEY", ""),
        }


# --8<-- [end:secrets-provider]
