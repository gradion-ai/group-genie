from group_genie.agent.base import AgentInput
from group_genie.message import Attachment


def user_prompt(input: AgentInput) -> list[str]:
    if input.attachments or input.preferences:
        query = format_query(input.query)
    else:
        query = input.query

    prompt = []

    if input.attachments:
        prompt.append(format_attachments(input.attachments))

    if input.preferences:
        prompt.append(format_user_preferences(input.preferences))

    prompt.append(query)
    return prompt


def format_query(query: str) -> str:
    return f"<query>\n{query}\n</query>"


def format_attachments(attachments: list[Attachment]) -> str:
    attachments_str = "\n".join(format_attachment(attachment) for attachment in attachments)
    return f"<attachments>\n{attachments_str}\n</attachments>"


def format_attachment(attachment: Attachment) -> str:
    return f'<attachment name="{attachment.name}" media_type="{attachment.media_type}">{attachment.path}</attachment>'


def format_user_preferences(preferences: str) -> str:
    return f"<user-preferences>\n{preferences}\n</user-preferences>"


def example():
    query = "What's the weather?"
    attachments = [
        Attachment(path="/path/to/image.png", name="image.png", media_type="image/png"),
        Attachment(path="/path/to/doc.pdf", name="document.pdf", media_type="application/pdf"),
    ]
    preferences = "I like sunny weather"

    for part in user_prompt(AgentInput(query=query, attachments=attachments, preferences=preferences)):
        print(part)


if __name__ == "__main__":
    example()
