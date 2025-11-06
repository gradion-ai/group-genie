## group_genie.secrets.SecretsProvider

Bases: `ABC`

Abstract base class for providing user-specific secrets.

SecretsProvider supplies credentials (like API keys) to agents and reasoners on a per-user basis. This enables agents to act on behalf of individual users with their own credentials while preventing unauthorized access to other users' resources.

Implementations should return secrets as key-value pairs where keys are credential names (e.g., "GOOGLE_API_KEY") and values are the actual credentials.

Example

```python
class EnvironmentSecretsProvider(SecretsProvider):
    def get_secrets(self, username: str) -> dict[str, str] | None:
        # For development: use environment variables for all users
        return {
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        }

class DatabaseSecretsProvider(SecretsProvider):
    def get_secrets(self, username: str) -> dict[str, str] | None:
        # For production: fetch user-specific credentials from database
        user = database.get_user(username)
        if not user:
            return None
        return {
            "GOOGLE_API_KEY": user.google_api_key,
            "OPENAI_API_KEY": user.openai_api_key,
        }
```

### get_secrets

```python
get_secrets(username: str) -> dict[str, str] | None
```

Retrieve secrets for a specific user.

Parameters:

| Name       | Type  | Description                   | Default    |
| ---------- | ----- | ----------------------------- | ---------- |
| `username` | `str` | User ID to fetch secrets for. | *required* |

Returns:

| Type             | Description |
| ---------------- | ----------- |
| \`dict[str, str] | None\`      |
