import argparse
from enum import Enum
from pathlib import Path
from typing import NamedTuple

import yaml
from semver import VersionInfo, bump_minor, bump_patch

from .common import Hooks


class Command(str, Enum):
    PREPARE = "prepare"
    HOTFIX = "hotfix"
    MAKE_TASK = "make-task"
    MAKE_BRANCH = "make-branch"
    MAKE_HOTFIX_BRANCH = "make-hotfix-branch"
    MAKE_LINKS = "make-links"

    FINISH = "finish"

    MARK_TASKS_DONE = "mark-tasks-done"

    MERGE_RELEASE = "merge-release"
    MERGE_TO_MASTER = "merge-to-master"
    MERGE_MASTER_TO_DEVELOP = "merge-master-to-develop"

    def __str__(self):
        return str(self.value)

    @classmethod
    def values(cls):
        return {e.value for e in cls.__members__.values()}


class JiraConnection(NamedTuple):
    server: str
    user: str
    token: str


class JiraReleaseTaskParams(NamedTuple):
    project: str
    component: str
    name: str = "{component} release {version}"
    link_type: str = "parent of"
    type: str = "Task"


class JiraTaskTransitionParams(NamedTuple):
    from_status = "To Deploy"
    done_status = "Done"


class JiraSettings:
    def __init__(self, **kwargs):
        self.connection = JiraConnection(**kwargs["connection"])
        self.release_task = JiraReleaseTaskParams(**kwargs["release_task"])
        self.transition = JiraTaskTransitionParams(**kwargs.get("transition", {}))


class GitHubSettings(NamedTuple):
    token: str
    task_re: str


class GitSettings(NamedTuple):
    base: str = "develop"
    master: str = "master"
    release_name: str = "release-{version}"


class Settings:
    def __init__(self, args, config):
        self._commands = set(args.commands)
        self.jira = JiraSettings(**config.get("jira", {}))
        self.git = GitSettings(**config.get("git", {}))
        self.hooks = Hooks(**config.get("hooks", {}))
        self.github = GitHubSettings(**config.get("github", {}))

        self.version = self._get_version()

        self.prs = args.pr
        assert self.require_creation_of_hotfix_branch or not self.prs, "'--pr' should be specified only for hotfix"

    def _get_version(self):
        proposed_version = VersionInfo.parse(self.hooks.get_version()())

        print(f"Current version: {proposed_version}")

        if self.require_creation_of_release_branch:
            proposed_version = VersionInfo.parse(bump_minor(str(proposed_version)))
        if self.require_creation_of_hotfix_branch:
            proposed_version = VersionInfo.parse(bump_patch(str(proposed_version)))

        version = None
        while version is None:
            user_input = input(f"Input version to use [{proposed_version}]: ")
            if user_input:
                try:
                    version = VersionInfo.parse(user_input)
                except ValueError as exc:
                    print(exc)
                    continue
            else:
                version = proposed_version

        return version

    @property
    def release_branch_name(self) -> str:
        return self.git.release_name.format(version=self.version)

    @property
    def require_version(self) -> bool:
        return bool(
            self._commands
            & {
                Command.PREPARE,
                Command.MAKE_BRANCH,
                Command.HOTFIX,
                Command.MAKE_HOTFIX_BRANCH,
                Command.MAKE_LINKS,
            }
        )

    @property
    def require_jira_version(self) -> bool:
        return bool(
            self._commands & {Command.PREPARE, Command.HOTFIX, Command.MAKE_LINKS}
        )

    @property
    def require_creation_of_jira_task(self) -> bool:
        return bool(
            self._commands & {Command.PREPARE, Command.HOTFIX, Command.MAKE_TASK}
        )

    @property
    def require_jira_task_search(self) -> bool:
        return bool(
            self._commands
            & {Command.FINISH, Command.MAKE_LINKS, Command.MARK_TASKS_DONE}
        )

    @property
    def require_jira_links(self) -> bool:
        return self.require_creation_of_jira_task or bool(
            self._commands & {Command.MAKE_LINKS}
        )

    @property
    def require_mark_tasks_done(self) -> bool:
        return bool(self._commands & {Command.FINISH, Command.MARK_TASKS_DONE})

    @property
    def require_merge_to_master(self) -> bool:
        return bool(
            self._commands
            & {Command.FINISH, Command.MERGE_RELEASE, Command.MERGE_TO_MASTER}
        )

    @property
    def require_merge_to_develop(self) -> bool:
        return bool(
            self._commands
            & {Command.FINISH, Command.MERGE_RELEASE, Command.MERGE_MASTER_TO_DEVELOP}
        )

    @property
    def require_creation_of_release_branch(self) -> bool:
        return bool(self._commands & {Command.PREPARE, Command.MAKE_BRANCH})

    @property
    def require_creation_of_hotfix_branch(self) -> bool:
        return bool(self._commands & {Command.HOTFIX, Command.MAKE_HOTFIX_BRANCH})


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("commands", nargs="+", choices=list(Command.values()))
    parser.add_argument(
        "--config", default=Path("release_tool.yml"), type=argparse.FileType("r")
    )
    parser.add_argument(
        "--pr",
        action="append",
        type=int,
        default=[],
        help="Github pull request for hotfix release",
    )

    return parser.parse_args()


def _load_config_file(config_path):
    with open(config_path.name) as fo:
        return yaml.safe_load(fo.read())


def _to_snake_case(value):
    if not isinstance(value, dict):
        return value

    return {
        key.replace("-", "_"): _to_snake_case(value) for key, value in value.items()
    }


def parse_and_combine_args() -> Settings:
    args = _parse_args()

    config = _load_config_file(args.config)
    config = _to_snake_case(config)

    return Settings(args, config)
