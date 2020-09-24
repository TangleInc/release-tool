from functools import partial
from typing import Callable, Iterable

from plugins.common import print_title

from .common import BashFunc, print_error
from .conf import Settings


__all__ = ["GitFuncs", "GitFlows", "check_repo_changes"]


class GitFuncs:
    check_repo_for_changes = partial(BashFunc, "git status --porcelain")

    fetch = partial(BashFunc, "git fetch")
    create_release_branch = partial(
        BashFunc, "git checkout -q -b {branch} --no-track origin/{source}"
    )
    delete_remote_branch = partial(BashFunc, "git push -q origin :{branch}")

    cherry_pick = partial(BashFunc, "git cherry-pick {sha}")
    commit = partial(BashFunc, 'git commit --allow-empty -am "Release {version}"')
    push = partial(BashFunc, "git push -q -u origin {branch}")
    checkout = partial(BashFunc, "git checkout -q {branch}")
    hard_reset = partial(BashFunc, "git reset -q --hard {branch}")

    create_tag = partial(BashFunc, "git tag {version}")
    push_tag = partial(BashFunc, "git push -q origin {version}")
    merge = partial(
        BashFunc, 'git merge -q --commit --no-ff {branch} -m "Merge, {branch}"'
    )


class GitFlows:
    def __init__(self, settings: Settings):
        self.version = settings.version
        self.release_branch = settings.git.release_name.format(version=self.version)

    def _create_tag(self) -> Iterable[BashFunc]:
        return [
            GitFuncs.checkout(branch=f"origin/{self.release_branch}"),
            GitFuncs.create_tag(version=self.version),
            GitFuncs.push_tag(version=self.version),
        ]

    @staticmethod
    def _merge(source, target) -> Iterable[BashFunc]:
        return [
            GitFuncs.checkout(branch=target),
            GitFuncs.hard_reset(branch=f"origin/{target}"),
            GitFuncs.merge(branch=f"origin/{source}"),
            GitFuncs.push(branch=target),
        ]

    def make_release_branch(self, release_set: Callable[..., BashFunc]):

        execute_commands(
            "Make release branch",
            GitFuncs.fetch(),
            GitFuncs.create_release_branch(
                source="develop", branch=self.release_branch
            ),
            release_set(version=self.version),
            GitFuncs.commit(version=self.version),
            GitFuncs.push(branch=self.release_branch),
        )

        print("Created release branch")

    def make_hotfix_branch(
        self, list_of_commit_sha, release_set: Callable[..., BashFunc]
    ):
        execute_commands(
            "Make hotfix branch",
            GitFuncs.fetch(),
            GitFuncs.create_release_branch(source="master", branch=self.release_branch),
            *[
                GitFuncs.cherry_pick(sha=commit_sha)
                for commit_sha in list_of_commit_sha
            ],
            release_set(version=self.version),
            GitFuncs.commit(version=self.version),
            GitFuncs.push(branch=self.release_branch),
        )

    def merge_release_to_master(self):
        execute_commands("Create tag", GitFuncs.fetch(), *self._create_tag())
        execute_commands(
            "Merge release to master",
            *self._merge(source=self.release_branch, target="master"),
            GitFuncs.delete_remote_branch(branch=self.release_branch),
        )

    @classmethod
    def merge_master_to_develop(cls):
        execute_commands(
            "Merge master to develop",
            GitFuncs.fetch(),
            *cls._merge(source="master", target="develop"),
        )


def execute_commands(name, *commands: BashFunc):

    print_title(f"Running suite: {name}")
    print("\n".join(map(str, commands)))
    print()

    for command in commands:
        command()


def check_repo_changes():
    repo_changes = GitFuncs.check_repo_for_changes()()
    if repo_changes:
        print_error("Your repo has changes, commit or stash them:")
        print_error(repo_changes)
        exit(1)
