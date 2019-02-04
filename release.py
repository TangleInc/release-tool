#!/usr/bin/env python

import argparse
import json
import re
import subprocess
import sys
from typing import NamedTuple, List

import yaml
from cached_property import cached_property
from github import Github
from jira import JIRA

import git


class Command:
    PREPARE = 'prepare'
    HOTFIX = 'hotfix'
    MAKE_TASK = 'make-task'
    MAKE_BRANCH = 'make-branch'
    MAKE_HOTFIX_BRANCH = 'make-hotfix-branch'
    MAKE_LINKS = 'make-links'

    MERGE_RELEASE = 'merge-release'
    MERGE_TO_MASTER = 'merge-to-master'
    MERGE_MASTER_TO_DEVELOP = 'merge-master-to-develop'


PR_RE = re.compile(r'#(\d+)', flags=re.U | re.I)
REPO_RE = re.compile(r'[/:](\w+/\w+)\.git')

ARGUMENTS = (
    'github-token',
    'jira-password',
    'jira-project',
    'jira-release-project',
    'jira-server',
    'jira-task-extra',
    'jira-user',
    'release-set',
    'pr',
)


class GetTaskResponse(NamedTuple):
    tasks: List[str]
    pull_requests_without_task: List[int]


def get_branch_name(release_project, version):
    return '{}-{}'.format(release_project.lower(), version)


def get_pr_task(github_repository, pr, task_re):
    pull = github_repository.get_pull(pr)
    return task_re.findall(pull.title)


def get_related_tasks(github_repository, task_re, release_project, release_version):
    git.GitFuncs.fetch()()
    commit_messages = subprocess.check_output(
        'git log origin/master..origin/{} --pretty=%B'.format(
            get_branch_name(
                release_project=release_project,
                version=release_version
            )),
        shell=True
    ).decode('utf-8')

    all_tasks = set()
    left_pulls = set()
    for line in commit_messages.split('\n'):
        tasks = task_re.findall(line)
        pull_request_match = PR_RE.search(line)
        if pull_request_match and not tasks:
            pr_number = int(pull_request_match.group(1))
            tasks = get_pr_task(
                github_repository=github_repository,
                pr=pr_number,
                task_re=task_re
            )
            if not tasks:
                left_pulls.add(pr_number)
        if not pull_request_match:
            continue
        all_tasks |= {task.upper() for task in tasks}

    return GetTaskResponse(
        tasks=list(sorted(all_tasks)),
        pull_requests_without_task=list(sorted(left_pulls))
    )


def make_links(jira_client, task_key, related_keys):
    for related_key in related_keys:
        jira_client.create_issue_link('relates to', task_key, related_key)


def make_release_task(jira_client, extra_fields, release_project, release_version):
    if not extra_fields:
        extra_fields = {}

    component_name = extra_fields.pop('component', None)
    if component_name:
        extra_fields['components'] = [{'name': component_name}]

    if component_name:
        summary = '{component} release {release_version}'.format(
            component=component_name,
            release_version=release_version)
    else:
        summary = 'Release {release_version}'.format(
            release_version=release_version)

    issue = jira_client.create_issue(
        project=release_project,
        summary=summary,
        issuetype={'name': 'Task'},
        **extra_fields
    )
    return issue.key


class API:
    def __init__(self, arguments):
        self._args = arguments

    @cached_property
    def jira(self):
        assert self._args.jira_server
        assert self._args.jira_user
        assert self._args.jira_password

        return JIRA({
            'server': self._args.jira_server
        }, basic_auth=(self._args.jira_user, self._args.jira_password))

    @cached_property
    def github(self):
        assert self._args.github_token
        return Github(self._args.github_token)

    @cached_property
    def github_repository(self):
        github_repo_match = REPO_RE.search(
            subprocess.check_output('git remote -v', shell=True).decode('utf-8')
        )
        assert github_repo_match
        return self.github.get_repo(github_repo_match.group(1))


def run(commands, api_client, jira_task_extra, task_key, task_re, release_project,
        release_version, release_set, prs):

    assert release_project, "`jira-release-project` is not provided"
    assert release_version, "`version` is not provided"
    assert task_re

    git_flows = git.GitFlows(
        version=release_version,
        release_branch_template=f'{release_project.lower()}-{{version}}'
    )

    set_commands = set(commands)

    if {Command.PREPARE, Command.HOTFIX, Command.MAKE_TASK} & set_commands:
        task_key = make_release_task(
            jira_client=api_client.jira,
            extra_fields=jira_task_extra,
            release_project=release_project,
            release_version=release_version)
        print('Made new task: {}'.format(task_key))

    if {Command.PREPARE, Command.MAKE_BRANCH} & set_commands:
        assert release_set
        git_flows.make_release_branch(release_set=release_set)
        print('Made release branch')

    if {Command.HOTFIX, Command.MAKE_HOTFIX_BRANCH} & set_commands:
        assert api_client.github_repository

        pulls = (
            api_client.github_repository.get_pull(pr)
            for pr in prs
        )
        list_of_commit_sha = (
            pull.merge_commit_sha
            for pull in pulls
            if pull.merge_commit_sha
        )

        git_flows.make_hotfix_branch(
            list_of_commit_sha=list_of_commit_sha,
            release_set=release_set,
        )
        print('Made hotfix branch')

    if {Command.PREPARE, Command.MAKE_LINKS, Command.HOTFIX} & set_commands:
        assert task_key
        assert api_client.github_repository

        relations = get_related_tasks(
            github_repository=api_client.github_repository,
            task_re=task_re,
            release_project=release_project,
            release_version=release_version
        )

        if relations.pull_requests_without_task:
            sys.stderr.write('Pull requests without tasks: {}\n'.format(
                ', '.join(map(str, relations.pull_requests_without_task))
            ))

        if not relations.tasks:
            sys.stderr.write('Did not find related tasks')
            exit(1)

        make_links(
            jira_client=api_client.jira,
            task_key=task_key,
            related_keys=relations.tasks)

        print('Made links from {} to {}'.format(
            task_key, ', '.join(relations.tasks)))

        if relations.pull_requests_without_task:
            exit(1)

    if {Command.MERGE_RELEASE, Command.MERGE_TO_MASTER} & set_commands:
        git_flows.merge_release_to_master()

    if {Command.MERGE_RELEASE, Command.MERGE_MASTER_TO_DEVELOP} & set_commands:
        git_flows.merge_master_to_develop()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'commands',
        nargs='+',
        choices=[
            Command.PREPARE,
            Command.HOTFIX,
            Command.MAKE_TASK,
            Command.MAKE_BRANCH,
            Command.MAKE_HOTFIX_BRANCH,
            Command.MAKE_LINKS,
            Command.MERGE_RELEASE,
            Command.MERGE_TO_MASTER,
            Command.MERGE_MASTER_TO_DEVELOP,
        ])
    parser.add_argument('--task')
    parser.add_argument('--version')
    parser.add_argument('--config')

    for arg in ARGUMENTS:
        if arg == 'jira-task-extra':
            parser.add_argument(
                '--{}'.format(arg),
                type=lambda value: json.loads(value),
                help='Something like \'{"component": "Backend"}\'')
        elif arg == 'pr':
            parser.add_argument(
                '--{}'.format(arg),
                action='append',
                type=int,
                default=[],
                help='Github pull request for hotfix release'
            )
        else:
            parser.add_argument('--{}'.format(arg))

    return parser.parse_args()


def parse_config(path):
    with open(path) as fo:
        return yaml.load(fo.read())


def parse_and_combine_args():
    args = parse_args()
    config = None
    if args.config:
        config = parse_config(args.config)
        jira_server = config['jira-server']
        config['jira-server'] = 'https://{}'.format(jira_server) if 'http' not in jira_server else jira_server
    if not config:
        return args

    for name in ARGUMENTS:
        if name not in config:
            continue

        name_snake_cased = name.replace('-', '_')
        if getattr(args, name_snake_cased) is None:
            setattr(args, name_snake_cased, config[name])

    return args


if __name__ == '__main__':
    _args = parse_and_combine_args()
    assert _args.jira_project, "`jira-project` is not passed"

    _release_task = _args.task.upper() if _args.task else None
    _task_re = re.compile(r'({}-\d+)\s'.format(_args.jira_project), flags=re.U | re.I)
    assert (
        Command.HOTFIX in _args.commands
        or Command.MAKE_HOTFIX_BRANCH in _args.commands
        or not _args.pr
    )

    run(
        commands=_args.commands,
        api_client=API(_args),
        jira_task_extra=_args.jira_task_extra,
        task_key=_release_task,
        task_re=_task_re,
        release_project=_args.jira_release_project,
        release_version=_args.version,
        release_set=_args.release_set,
        prs=_args.pr,
    )
