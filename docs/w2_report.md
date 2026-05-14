# W2 hard gate report

Agent end-to-end smoke against the 3-tool catalog (slack_query / jira_query / calendar_query), streaming events through the LangGraph 5-node skeleton. Per design Section 8 W2 gate criteria.

**Query** (Sarah Chen, role=manager):
> Morning briefing for today across Slack, Jira, and Calendar. What should I focus on? Highlight conflicts and blockers.

**Tool calls**: 3

| # | Tool | Args (keys) |
|---:|---|---|
| 1 | `calendar_query` | `['end', 'include_conflicts', 'start', 'user_calendar_id']` |
| 2 | `jira_query` | `['assignee', 'has_blockers', 'max_items', 'priority_min']` |
| 3 | `slack_query` | `['include_dms', 'include_mentions', 'max_items', 'since', 'user_handle']` |

**Final answer**:

Good morning, Sarah. Here’s your briefing for Monday, 11 May 2026.

**Schedule**  
No meetings or events today-zero conflicts [cal:evt-0-events]. The day is entirely open for focused work.

**Top Priority; Jira Blockers**  
Two unresolved tickets assigned to you are blocked, both high-impact:
- **MOBILE-029** [Critical / In Progress] – *Blocked by MOBILE-018* [jira:MOBILE-029]. This is your highest urgency item; critical work is stalled.
- **MOBILE-003** [High / In Review] – *Blocked by MOBILE-002* [jira:MOBILE-003]. A high‑priority review is stuck.

Neither blocker belongs to you-immediate action is required to unblock these via the owners of MOBILE-018 and MOBILE-002.

**Slack Catch-up**  
17 mentions since Friday, 0 DMs [slack:query-17-mentions-0-dms]. Mentions span #engineering [slack:msg-00059], #design-review [slack:msg-00133], #berlin [slack:msg-00727], #amsterdam [slack:msg-00699], #career-talk [slack:msg-01167], and others. Message snippets contain no obvious escalation (mostly noise), but the volume warrants a quick scan of #engineering and #design-review for any weekend asks. No direct messages suggests nothing personally paging you.

**Recommended Focus**  
1. Unblock **MOBILE-029**; chase the owner of MOBILE-018 immediately (highest impact).  
2. Unblock **MOBILE-003**; follow up on MOBILE-002 to keep the review moving.  
3. 5‑minute Slack scan of #engineering and #design-review to clear the weekend backscroll.

Audit: 3 tool calls.

### W2 hard gate: **PASS**

