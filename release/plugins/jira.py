from datetime import datetime
from functools import partial
from multiprocessing.pool import ThreadPool
from typing import Optional

from jira import JIRA
from jira.resources import Project, Version

from .common import print_error, print_title
from .conf import Settings


class JiraAPI:
    """
    Jira client has no documentation, so if you need one, use one for REST API:
    https://developer.atlassian.com/cloud/jira/platform/rest/v3/
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self.transition = settings.jira.transition
        self.release_task = settings.jira.release_task
        self.release_task_name = self.release_task.name.format(
            version=settings.version, component=self.release_task.component
        )

        self._api = JIRA(
            {"server": settings.jira.connection.server},
            basic_auth=(settings.jira.connection.user, settings.jira.connection.token),
        )

    def _create_version(self, project: Project):
        proposed_name = "Hotfix" if self._settings.version.minor > 0 else "Release"
        user_input = input(f"Input new Jira version name: [{proposed_name}]: ")
        name = user_input if user_input else proposed_name

        return self._api.create_version(name, project, startDate=_get_formatted_date())

    def _select_version(
        self, project: Project, unreleased_versions
    ) -> Optional[Version]:
        print("Jira versions:")
        print("1) Skip")
        print("2) Create new")
        print("or select existing one:")

        unreleased_versions = {
            idx: version for idx, version in enumerate(unreleased_versions, 3)
        }

        for idx, version in unreleased_versions.items():
            print(f"{idx}) {version.name}")

        user_input = 0
        valid_choices = list(range(1, len(unreleased_versions) + 3))

        while user_input not in valid_choices:
            try:
                user_input = int(
                    input("\nChoose which Jira version use for this release: ")
                )
            except Exception:
                continue

        if user_input == 1:
            return None
        elif user_input == 2:
            return self._create_version(project)
        else:
            return unreleased_versions[user_input]

    def get_version(self) -> Optional[Version]:
        print_title(f"Searching for Jira release version")
        project = self._api.project(self.release_task.project)

        unreleased_versions = [
            v for v in self._api.project_versions(project) if not v.released
        ]

        return self._select_version(project, unreleased_versions)

    def _get_jira_release_unfinished_tasks(self, version: Version):
        """
        To check that all tasks in Jira release is finished
        select them using jql
        """
        final_statuses = '", "'.join(self.transition.child_final_statuses)
        types_to_skip = '", "'.join(self.transition.child_task_types_to_skip)

        return self._api.search_issues(
            f'project = "{self.release_task.project}"'
            f' AND fixVersion = "{version.name}"'
            f' AND fixVersion in unreleasedVersions("{self.release_task.project}")'
            f' AND status NOT IN ("{final_statuses}")'
            f' AND type NOT IN ("{types_to_skip}")'
        )

    def _get_transition(self, issue, transition_name):
        transitions = [
            t
            for t in self._api.transitions(issue)
            if t["name"].lower() == transition_name.lower()
        ]
        if not transitions:
            return None

        return transitions[0]

    def release_version(self, release_task_key: str):
        print_title(f"Releasing Jira version of release task {release_task_key}")
        release_task = self._api.issue(release_task_key)

        for version in release_task.fields.fixVersions:
            version: Version
            print(f'Checking Jira release version: "{version.name}"...')

            if version.released:
                print_error("Version is already released")
                continue

            unfinished_tasks = self._get_jira_release_unfinished_tasks(version)
            if unfinished_tasks:
                tasks_str = ", ".join([i.key for i in unfinished_tasks])
                print_error(
                    f'Can\'t release Jira version: "{version.name}", it has unfinished tasks: {tasks_str}'
                )
                continue

            print("Jira version is safe to release, releasing...", end=" ")
            version.update(released=True, releaseDate=_get_formatted_date())
            print("Ok!")

    def _add_to_release_version(self, version: Version, release_task_key: str):
        issue = self._api.issue(release_task_key)
        issue.add_field_value("fixVersions", {"name": version.name})

    def make_links(self, version: Optional[Version], release_task_key, related_keys):
        version_name = version.name if version else "-"
        print_title(
            f"Linking tasks found in release branch"
            f" to release task ({release_task_key})"
            f' and to Jira version "{version_name}"'
        )
        if version:
            self._add_to_release_version(version, release_task_key)

        print(f"Linking {len(related_keys)} tasks:")
        partial_make_links = partial(self._make_links, version, release_task_key)
        with ThreadPool(5) as pool:
            pool.map(partial_make_links, related_keys)

    def _make_links(
        self, version: Optional[Version], release_task_key: str, child_task_key: str
    ):
        print(f"* {child_task_key}")
        self._api.create_issue_link(
            self.release_task.link_type, release_task_key, child_task_key
        )
        if version:
            self._add_to_release_version(version, child_task_key)

    def make_release_task(self):
        print_title("Creating Jira release task")
        extra_fields = {"components": [{"name": self.release_task.component}]}

        issue = self._api.create_issue(
            project=self.release_task.project,
            summary=self.release_task_name,
            issuetype={"name": self.release_task.type},
            **extra_fields,
        )
        print(f"Created Jira release task: {issue.key}")
        return issue.key

    def get_release_task(self):
        print_title("Searching for Jira release task")
        query = (
            f'project = "{self.release_task.project}"'
            f' AND summary ~ "{self.release_task_name}"'
            f' AND type = "{self.release_task.type}"'
        )
        found_issues = self._api.search_issues(query)

        if not found_issues:
            print_error("Did not find existing release task")
            return self.make_release_task()

        if len(found_issues) > 1:
            issues_str = ", ".join([i.key for i in found_issues])
            print_error(
                f"Your release task has not unique name, fix it before using this functionality,"
                f" found issues: {issues_str}"
            )
            exit(1)

        release_issue = found_issues[0]
        print(f"Found Jira release task: {release_issue.key}")
        return release_issue.key

    def mark_release_task_done(self, release_task_key):
        print_title(
            f'Transition release task "{release_task_key}" from "{self.transition.release_from_status}" to "{self.transition.release_to_status}"'
        )

        release_issue = self._api.issue(release_task_key)
        print_title(f'Current release task status is "{release_issue.fields.status}"')

        if (
            release_issue.fields.status.name.lower()
            != self.transition.release_from_status.lower()
        ):
            print_error(f'Release task "{release_task_key}" has inproper status')
            return

        transition = self._get_transition(
            release_issue, self.transition.release_to_status
        )

        if not transition:
            print_error(
                f'Release task "{release_task_key}" has no transition to "{self.transition.release_to_status}"'
            )
            return

        self._api.transition_issue(release_issue, transition["id"])

        print(
            f'Release task {release_issue.key} has been transited to status "{transition["name"]}"'
        )

    def mark_children_tasks_done(self, release_task_key):
        print_title(
            f'Transition children of "{release_task_key}" from "{self.transition.child_from_status}" to "{self.transition.child_to_status}"'
        )

        query = (
            f'issue in linkedIssues("{release_task_key}")'
            f' AND status = "{self.transition.child_from_status}"'
        )
        found_issues = self._api.search_issues(query)

        to_status = self.transition.child_to_status.lower()

        if not found_issues:
            print_error("Did not find any task for transition")
            return

        for issue in found_issues:
            transition = self._get_transition(issue, to_status)
            if not transition:
                print_error(
                    f'Issue "{issue.key}" does not have transition to status "{self.transition.child_to_status}"'
                )
                continue

            self._api.transition_issue(issue, transition["id"])
            print(
                f'Task {issue.key} has been transited to status "{transition["name"]}"'
            )


def _get_formatted_date():
    return datetime.today().strftime("%Y-%m-%d")
