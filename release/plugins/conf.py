import argparse
from dataclasses import MISSING, dataclass, fields
from enum import Enum

import yaml
from semver import VersionInfo, bump_minor, bump_patch

from .common import Hooks
from .env import ENV_VARIABLE_NAMES, get_parameter


class ParameterMixin:
    SUBCLASSES = []

    def __init_subclass__(cls, **kwargs):
        # collect subclasses for validation
        # validation can't be done here as dataclass decorator
        # is not executed at this point
        cls.SUBCLASSES.append(cls)

    @classmethod
    def validate(cls):
        """Validate that all parameters have env variable representation"""
        for subclass in cls.SUBCLASSES:
            env_variable_names = ENV_VARIABLE_NAMES.get(subclass.__name__, {})
            for field_name in subclass._parameter_defaults():
                assert (
                    field_name in env_variable_names
                ), f'"{field_name}" has no env variable'

    @classmethod
    def from_config(cls, config: dict):
        env_variable_names = ENV_VARIABLE_NAMES.get(cls.__name__, {})
        return cls(
            **{
                name: get_parameter(config, name, env_variable_names.get(name), default)
                for name, default in cls._parameter_defaults().items()
            }
        )

    @classmethod
    def _parameter_defaults(cls):
        return {
            field.name: None if field.default is MISSING else field.default
            for field in fields(cls)
        }


class Command(str, Enum):
    PREPARE = "prepare"
    HOTFIX = "hotfix"
    MAKE_TASK = "make-task"
    MAKE_BRANCH = "make-branch"
    MAKE_HOTFIX_BRANCH = "make-hotfix-branch"
    MAKE_LINKS = "make-links"

    FINISH = "finish"

    MARK_CHILDREN_TASKS_DONE = "mark-children-tasks-done"
    MARK_RELEASE_TASK_DONE = "mark-release-task-done"

    MERGE_RELEASE = "merge-release"
    MERGE_TO_MASTER = "merge-to-master"
    MERGE_MASTER_TO_DEVELOP = "merge-master-to-develop"

    def __str__(self):
        return str(self.value)

    @classmethod
    def values(cls):
        return {e.value for e in cls.__members__.values()}


@dataclass
class JiraConnection(ParameterMixin):
    server: str
    user: str
    token: str


@dataclass
class JiraReleaseTaskParams(ParameterMixin):
    project: str
    component: str
    name: str = "{component} release {version}"
    link_type: str = "parent of"
    type: str = "Task"


@dataclass
class JiraTaskTransitionParams(ParameterMixin):
    child_from_status: str = "To Deploy"
    child_to_status: str = "Done"
    child_final_statuses: str = (child_to_status, "Closed")
    child_task_types_to_skip: str = ("Story",)

    release_from_status: str = "On Production"
    release_to_status: str = "Release Merged"


class JiraSettings:
    def __init__(self, **kwargs):
        self.connection = JiraConnection.from_config(kwargs["connection"])
        self.release_task = JiraReleaseTaskParams.from_config(kwargs["release_task"])
        self.transition = JiraTaskTransitionParams.from_config(
            kwargs.get("transition", {})
        )


@dataclass
class GitHubSettings(ParameterMixin):
    token: str
    task_re: str


@dataclass
class GitSettings(ParameterMixin):
    base: str = "develop"
    master: str = "master"
    release_name: str = "release-{version}"


class Settings:
    version: VersionInfo

    def __init__(self, config, args=None):
        if args:
            self._commands = set(args.commands)
            self.prs = args.pr
            self.no_input = args.noinput
            assert (
                self.require_creation_of_hotfix_branch or not self.prs
            ), "'--pr' should be specified only for hotfix"
        else:
            # for debug purpose, to create settings without command line call
            self._commands = set()
            self.prs = ()
            self.no_input = False

        self.jira = JiraSettings(**config.get("jira", {}))
        self.git = GitSettings.from_config(config.get("git", {}))
        self.hooks = Hooks(**config.get("hooks", {}))
        self.github = GitHubSettings.from_config(config.get("github", {}))

    def parse_project_version(self):
        self.version = self._get_version()

    def _get_version(self) -> VersionInfo:
        hook_result = self.hooks.get_version()()
        proposed_version = VersionInfo.parse(hook_result.strip())

        print(f"Current version: {proposed_version}")

        if self.require_creation_of_release_branch:
            proposed_version = VersionInfo.parse(bump_minor(str(proposed_version)))
        if self.require_creation_of_hotfix_branch:
            proposed_version = VersionInfo.parse(bump_patch(str(proposed_version)))

        if self.no_input:
            return proposed_version

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
    def require_clean_repo(self) -> bool:
        return bool(
            self._commands
            & {
                Command.PREPARE,
                Command.MAKE_BRANCH,
                Command.HOTFIX,
                Command.MAKE_HOTFIX_BRANCH,
                Command.FINISH,
                Command.MERGE_RELEASE,
                Command.MERGE_TO_MASTER,
                Command.MERGE_MASTER_TO_DEVELOP,
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
            & {
                Command.FINISH,
                Command.MAKE_LINKS,
                Command.MARK_CHILDREN_TASKS_DONE,
                Command.MARK_RELEASE_TASK_DONE,
            }
        )

    @property
    def require_jira_links(self) -> bool:
        return self.require_creation_of_jira_task or bool(
            self._commands & {Command.MAKE_LINKS}
        )

    @property
    def require_mark_chldren_tasks_done(self) -> bool:
        return bool(self._commands & {Command.FINISH, Command.MARK_CHILDREN_TASKS_DONE})

    @property
    def require_mark_release_task_done(self) -> bool:
        return bool(self._commands & {Command.FINISH, Command.MARK_RELEASE_TASK_DONE})

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
        "--config",
        default="release_tool.yml",
        type=str,
        help="Path to config file (default release_tool.yml)",
    )

    parser.add_argument(
        "--noinput", help="run without user interaction", action="store_true"
    )

    parser.add_argument(
        "--pr",
        action="append",
        type=int,
        default=[],
        help="Github pull request for hotfix release",
    )

    return parser.parse_args()


def _load_config_file(config_path: str):
    with open(config_path) as fo:
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

    return Settings(config, args)


def get_debug_settings(config_file: str) -> Settings:
    config = _load_config_file(config_file)
    config = _to_snake_case(config)

    return Settings(config)


# validate subclasses after all of them are created
ParameterMixin.validate()
