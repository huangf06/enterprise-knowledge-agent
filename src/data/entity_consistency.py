from pathlib import Path

import yaml
from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    name: str
    department: str
    office: str
    role: str
    manager_id: str | None
    slack_handle: str
    jira_user: str
    email: str
    github_username: str
    gdocs_author_id: str
    calendar_id: str


USERS_YAML = Path(__file__).parents[2] / "data" / "eval" / "users_seed.yaml"


def load_users() -> list[User]:
    with USERS_YAML.open() as f:
        return [User(**u) for u in yaml.safe_load(f)]
