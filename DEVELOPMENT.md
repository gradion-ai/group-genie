# Development Environment

Clone the repository:

```bash
git clone https://github.com/gradion-ai/group-genie.git
cd group-genie
```

Create a virtual environment and install dependencies:

```bash
uv sync
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install pre-commit hooks:

```bash
invoke precommit-install
```

Enforce coding conventions (also enforced by pre-commit hooks):

```bash
invoke cc
```

Run tests:

```bash
pytest -s tests
```
