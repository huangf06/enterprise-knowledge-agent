"""Per-source Pydantic schemas. Foreign keys point at User identities defined in entity_consistency.User."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["Critical", "High", "Medium", "Low"]
IssueStatus = Literal["Open", "In Progress", "Blocked", "In Review", "Done"]
PRState = Literal["open", "merged", "closed"]


class SlackMessage(BaseModel):
    message_id: str
    channel: str
    thread_id: str | None = None
    author: str  # slack_handle FK
    text: str
    timestamp: datetime
    mentions: list[str] = Field(default_factory=list)  # slack_handles


class SlackChannel(BaseModel):
    name: str
    members: list[str]  # slack_handles
    is_private: bool = False
    description: str = ""


class SlackDM(BaseModel):
    dm_id: str
    sender: str  # slack_handle FK
    recipient: str  # slack_handle FK
    text: str
    timestamp: datetime


class JiraIssue(BaseModel):
    issue_key: str
    project: str
    title: str
    description: str
    assignee: str  # jira_user FK
    reporter: str  # jira_user FK
    priority: Priority
    status: IssueStatus
    blockers: list[str] = Field(default_factory=list)  # issue_keys
    created_at: datetime
    updated_at: datetime
    labels: list[str] = Field(default_factory=list)


class CalendarEvent(BaseModel):
    event_id: str
    title: str
    description: str = ""
    organizer: str  # calendar_id (email) FK
    attendees: list[str]  # calendar_ids
    start: datetime
    end: datetime
    is_recurring: bool = False
    mandatory: bool = False
    location: str = ""


class GitHubPR(BaseModel):
    pr_id: str
    repo: str
    title: str
    body: str
    author: str  # github_username FK
    reviewers: list[str]  # github_usernames
    state: PRState
    created_at: datetime
    labels: list[str] = Field(default_factory=list)


class GitHubRepo(BaseModel):
    name: str
    description: str = ""
    prs: list[GitHubPR] = Field(default_factory=list)


class GDoc(BaseModel):
    doc_id: str
    title: str
    content: str
    owner: str  # gdocs_author_id FK
    shared_with: list[str] = Field(default_factory=list)  # gdocs_author_ids
    acl: list[str] = Field(default_factory=list)  # role names ("hr", "leadership") if restricted
    created_at: datetime
    updated_at: datetime


class Email(BaseModel):
    email_id: str
    thread_id: str | None = None
    sender: str  # email FK
    recipients: list[str]  # email FKs
    subject: str
    body: str
    sent_at: datetime
    importance: Literal["high", "normal", "low"] = "normal"
    unread: bool = True
