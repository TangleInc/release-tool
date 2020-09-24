#!/usr/bin/env python

import sys

from .plugins import git
from .plugins.conf import Settings
from .plugins.github import GitHubAPI
from .plugins.jira import JiraAPI


def run(settings: Settings):
    sys.stderr.write("ERROR")
    exit(1)

    github_api = GitHubAPI(settings)
    jira_api = JiraAPI(settings)

    if settings.require_jira_version and not settings.no_input:
        jira_version = jira_api.get_version()
    else:
        jira_version = None
    print(f"Jira version: {jira_version.name if jira_version else '-'}")

    git_flows = git.GitFlows(settings)

    if settings.require_creation_of_release_branch:
        assert settings.hooks.set_version
        git.check_repo_changes()
        git_flows.make_release_branch(release_set=settings.hooks.set_version)

    if settings.require_creation_of_hotfix_branch:
        assert settings.hooks.set_version
        git.check_repo_changes()
        pulls = (github_api.repository.get_pull(pr) for pr in settings.prs)
        list_of_commit_sha = (
            pull.merge_commit_sha for pull in pulls if pull.merge_commit_sha
        )

        git_flows.make_hotfix_branch(
            list_of_commit_sha=list_of_commit_sha,
            release_set=settings.hooks.set_version,
        )
        print("Made hotfix branch")

    if settings.require_creation_of_jira_task or settings.require_jira_task_search:
        release_task_key = jira_api.get_release_task()

    if settings.require_jira_links:
        print("check jira links")
        assert release_task_key

        relations = github_api.get_related_tasks()

        if relations.pull_requests_without_task:
            print("PR without tasks:")
            sys.stderr.write(
                "Pull requests without tasks: {}\n".format(
                    ", ".join(map(str, relations.pull_requests_without_task))
                )
            )

        if not relations.tasks:
            print("no tasks")
            sys.stderr.write("Did not find related tasks")
            exit(1)

        jira_api.make_links(
            version=jira_version,
            release_task_key=release_task_key,
            related_keys=relations.tasks,
        )

        print(
            "Made links from {} to {}".format(
                release_task_key, ", ".join(relations.tasks)
            )
        )

    if settings.require_merge_to_master:
        git_flows.merge_release_to_master()

    if settings.require_merge_to_develop:
        git_flows.merge_master_to_develop()

    if settings.require_mark_release_task_done:
        assert release_task_key
        jira_api.mark_release_task_done(release_task_key)

    if settings.require_mark_chldren_tasks_done:
        assert release_task_key
        jira_api.mark_children_tasks_done(release_task_key)
        jira_api.release_version(release_task_key)
