"""Tool registry surface. Importing this module registers all v1 tools."""

from src.tools import calendar_query as _calendar  # noqa: F401
from src.tools import email_query as _email  # noqa: F401
from src.tools import gdocs_search as _gdocs  # noqa: F401
from src.tools import github_pr_review as _github  # noqa: F401
from src.tools import jira_query as _jira  # noqa: F401
from src.tools import slack_query as _slack  # noqa: F401
from src.tools.base import Tool, ToolRegistry, registry

__all__ = ["Tool", "ToolRegistry", "registry"]
