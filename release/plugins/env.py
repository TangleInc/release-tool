import os
from typing import Optional


# it can be automated, but I find it much easy to read/search in hardcoded way
# {Scope: {VariableName: VARIABLE_ENV_NAME}}
ENV_VARIABLE_NAMES = {
    "JiraConnection": {
        "server": "RELEASE_TOOL_JIRA_SERVER",
        "user": "RELEASE_TOOL_JIRA_USER",
        "token": "RELEASE_TOOL_JIRA_TOKEN",
    },
    "JiraReleaseTaskParams": {
        "project": "RELEASE_TOOL_JIRA_PROJECT",
        "component": "RELEASE_TOOL_JIRA_COMPONENT",
        "name": "RELEASE_TOOL_JIRA_NAME",
        "link_type": "RELEASE_TOOL_JIRA_LINK_TYPE",
        "type": "RELEASE_TOOL_JIRA_TYPE",
    },
    "JiraTaskTransitionParams": {
        "child_from_status": "RELEASE_TOOL_JIRA_CHILD_FROM_STATUS",
        "child_to_status": "RELEASE_TOOL_JIRA_CHILD_TO_STATUS",
        "child_final_statuses": "RELEASE_TOOL_JIRA_CHILD_FINAL_STATUSES",
        "child_task_types_to_skip": "RELEASE_TOOL_JIRA_CHILD_TASK_TYPES_TO_SKIP",
        "release_from_status": "RELEASE_TOOL_JIRA_RELEASE_FROM_STATUS",
        "release_to_status": "RELEASE_TOOL_JIRA_RELEASE_TO_STATUS",
    },
    "GitHubSettings": {
        "token": "RELEASE_TOOL_GITHUB_TOKEN",
        "task_re": "RELEASE_TOOL_GITHUB_TASK_RE",
    },
    "GitSettings": {
        "base": "RELEASE_TOOL_GIT_BASE",
        "master": "RELEASE_TOOL_GIT_MASTER",
        "release_name": "RELEASE_TOOL_GIT_RELEASE_NAME",
    },
}


def get_parameter(config: dict, name: str, env_name: Optional[str], default=None):
    value = config.get(name, default)
    if env_name:
        value = os.environ.get(env_name, value)
    return value
