import re
import subprocess
from typing import List, NamedTuple

from github import Github

from . import git
from .conf import Settings


PR_RE = re.compile(r"#(\d+)", flags=re.U | re.I)
REPO_RE = re.compile(r"[/:]([-\w_]+/[-\w_]+)\.git")


class GetTaskResponse(NamedTuple):
    tasks: List[str]
    pull_requests_without_task: List[int]


class GitHubAPI:
    def __init__(self, settings: Settings):
        self._api = Github(settings.github.token)
        self._master_branch_name = settings.git.master
        self._release_branch_name = settings.release_branch_name
        self._task_re = re.compile(settings.github.task_re, flags=re.U | re.I)
        self.repository = self._get_repository()
        self.skip_git_fetch = settings.skip_git_fetch

    def _get_repository(self):
        github_repo_match = REPO_RE.search(
            subprocess.check_output("git remote -v", shell=True).decode("utf-8")
        )
        assert github_repo_match
        return self._api.get_repo(github_repo_match.group(1))

    def get_pr_task(self, pr):
        pull = self.repository.get_pull(pr)
        return self._task_re.findall(pull.title)

    def get_commit_message_in_release(self):
        if not self.skip_git_fetch:
            git.GitFuncs.fetch()()
        return subprocess.check_output(
            "git log origin/{}..origin/{} --pretty=%B".format(
                self._master_branch_name, self._release_branch_name
            ),
            shell=True,
        ).decode("utf-8")

    def get_related_tasks(self):
        commit_messages = self.get_commit_message_in_release()

        all_tasks = set()
        left_pulls = set()

        for line in commit_messages.split("\n"):
            tasks = self._task_re.findall(line)
            pull_request_match = PR_RE.search(line)

            if pull_request_match and not tasks:
                pr_number = int(pull_request_match.group(1))
                tasks = self.get_pr_task(pr=pr_number)
                if not tasks:
                    left_pulls.add(pr_number)

            all_tasks |= {task.upper() for task in tasks}

        return GetTaskResponse(
            tasks=list(sorted(all_tasks)),
            pull_requests_without_task=list(sorted(left_pulls)),
        )
