import argparse
import json
import os
import re
import subprocess
import sys
from collections import namedtuple

import yaml
from cached_property import cached_property
from github import Github
from jira import JIRA


class Command:
    PREPARE = 'prepare'
    MAKE_TASK = 'make-task'
    MAKE_BRANCH = 'make-branch'
    MAKE_RELATIONS = 'make-relations'


TASK_PROJECT = 'TAN'
RELEASE_PROJECT = 'RELEASE'
TASK_RE = re.compile(r'({}-\d+)\s'.format(TASK_PROJECT), flags=re.U | re.I)
PR_RE = re.compile(r'\(#(\d+)\)', flags=re.U | re.I)
REPO_RE = re.compile(r'[/:](\w+/\w+)\.git')

GetTaskResponse = namedtuple('GetTaskResponse', ('tasks', 'left_pulls'))


def git_fetch():
    subprocess.check_call('git fetch', shell=True, stdout=subprocess.PIPE)


def get_pr_task(api_client, pr):
    pull = api_client.github_repository.get_pull(pr)
    return TASK_RE.findall(pull.title)


def get_related_tasks(task_key, origin_branch, api_client):
    assert origin_branch
    git_fetch()
    commit_messages = subprocess.check_output(
        'git log origin/{}..origin/{} --pretty=%B'.format(
            origin_branch, task_key.lower()),
        shell=True
    ).decode('utf-8')

    all_tasks = set()
    left_pulls = set()
    for line in commit_messages.split('\n'):
        tasks = TASK_RE.findall(line)
        pull_request_match = PR_RE.search(line)
        if pull_request_match and not tasks:
            pr_number = int(pull_request_match.group(1))
            tasks = get_pr_task(api_client=api_client, pr=pr_number)
            if not tasks:
                left_pulls.add(pr_number)
        if not pull_request_match:
            continue
        all_tasks |= {task.upper() for task in tasks}

    return GetTaskResponse(
        tasks=list(sorted(all_tasks)),
        left_pulls=list(sorted(left_pulls))
    )


def make_links(api_client, task_key, related_keys):
    for related_key in related_keys:
        api_client.jira.create_issue_link('relates to', task_key, related_key)


def make_release_task(api_client, extra_fields):
    if not extra_fields:
        extra_fields = {}

    component_name = extra_fields.pop('component', None)
    if component_name:
        extra_fields['components'] = [{'name': component_name}]

    summary = '{} release'.format(component_name) if component_name else 'Release'
    issue = api_client.jira.create_issue(
        project=RELEASE_PROJECT,
        summary=summary,
        issuetype={'name': 'Task'},
        **extra_fields
    )
    issue_key_id = issue.key.split('-')[1]
    issue.update(summary='{} {}'.format(summary, issue_key_id))
    return issue.key


def make_release_branch(task_key):
    git_fetch()
    commands = [
        'git checkout origin/develop',
        'git checkout -b {branch}',
        'git push origin {branch}'
    ]
    subprocess.check_call(
        (' && '.join(commands)).format(branch=task_key.lower()),
        shell=True
    )


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
        assert self._args.github_user
        assert self._args.github_password
        return Github(self._args.github_user, self._args.github_password)

    @cached_property
    def github_repository(self):
        github_repo_match = REPO_RE.search(
            subprocess.check_output('git remote -v', shell=True).decode('utf-8')
        )
        assert github_repo_match
        return self.github.get_repo(github_repo_match.group(1))


def run(commands, api_client, origin_branch, jira_task_extra, task_key=None):
    if Command.PREPARE in commands or Command.MAKE_TASK in commands:
        task_key = make_release_task(api_client, jira_task_extra)
        print('Made new task: {}'.format(task_key))

    if Command.PREPARE in commands or Command.MAKE_BRANCH in commands:
        assert task_key
        make_release_branch(task_key)
        print('Made release branch')

    if Command.PREPARE in commands or Command.MAKE_RELATIONS in commands:
        assert task_key
        relations = get_related_tasks(task_key, origin_branch, api_client=api_client)

        if relations.left_pulls:
            sys.stderr.write('Pull requests without tasks: {}\n'.format(
                ', '.join(map(str, relations.left_pulls))
            ))

        if not relations.tasks:
            sys.stderr.write('Did not find related tasks')
            exit(1)

        make_links(api_client, task_key, relations.tasks)

        print('Made links from {} to {}'.format(
            task_key, ', '.join(relations.tasks)))

        if relations.left_pulls:
            exit(1)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'commands',
        nargs='+',
        choices=[
            Command.PREPARE,
            Command.MAKE_TASK,
            Command.MAKE_BRANCH,
            Command.MAKE_RELATIONS
        ])
    parser.add_argument('--release-task')
    parser.add_argument('--origin-branch')
    parser.add_argument('--jira-server')
    parser.add_argument('--jira-user')
    parser.add_argument('--jira-password')
    parser.add_argument(
        '--jira-task-extra',
        type=lambda value: json.loads(value),
        help='Something like \'{"component": "Backend"}\'')
    parser.add_argument('--github-user')
    parser.add_argument('--github-password')

    return parser.parse_args()


def parse_config():
    path = os.path.join(os.path.dirname(__file__), 'config.yml')
    if not os.path.exists(path=path):
        return None

    with open(path) as fo:
        return yaml.load(fo.read())


def parse_and_combine_args():
    config = parse_config()
    args = parse_args()
    if not config:
        return args

    names = (
        'origin-branch', 'jira-server', 'jira-user', 'jira-password',
        'jira-task-extra', 'github-user', 'github-password')
    for name in names:
        if name not in config:
            continue

        if getattr(args, name.replace('-', '_')) is None:
            setattr(args, name.replace('-', '_'), config[name])
    return args


if __name__ == '__main__':
    args = parse_and_combine_args()
    run(
        commands=args.commands,
        api_client=API(args),
        origin_branch=args.origin_branch,
        jira_task_extra=args.jira_task_extra,
        task_key=args.release_task)
