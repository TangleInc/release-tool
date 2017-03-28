import json
import re
import subprocess

import sys
import argparse
from collections import namedtuple
from functools import lru_cache

from jira import JIRA

TASK_PROJECT = 'TAN'
RELEASE_PROJECT = 'RELEASE'
TASK_RE = re.compile(r'({}-\d+)\s'.format(TASK_PROJECT), flags=re.U | re.I)
PR_RE = re.compile(r'\((#\d+)\)', flags=re.U | re.I)

GetTaskResponse = namedtuple('GetTaskResponse', ('tasks', 'left_pulls'))


def git_fetch():
    subprocess.check_call('git fetch', shell=True, stdout=subprocess.PIPE)


def get_related_tasks(task_key, origin_branch):
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
        pull_request = PR_RE.search(line)
        if pull_request and not tasks:
            pr_number = pull_request.group(1)
            left_pulls.add(pr_number)
        if not pull_request:
            continue
        all_tasks |= {task.upper() for task in tasks}

    return GetTaskResponse(
        tasks=list(sorted(all_tasks)),
        left_pulls=list(sorted(left_pulls))
    )


def make_links(jira, task_key, related_keys):
    for related_key in related_keys:
        jira.create_issue_link('relates to', task_key, related_key)


def make_release_task(jira, extra_fields):
    if not extra_fields:
        extra_fields = {}

    component_name = extra_fields.pop('component', None)
    if component_name:
        extra_fields['components'] = [{'name': component_name}]

    summary = '{} release'.format(component_name) if component_name else 'Release'
    issue = jira.create_issue(
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


@lru_cache()
def get_jira_api(jira_server, jira_user, jira_password):
    assert jira_server
    assert jira_user
    assert jira_password

    return JIRA({
        'server': jira_server
    }, basic_auth=(jira_user, jira_password))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'commands',
        nargs='+',
        choices=['all', 'make-task', 'make-branch', 'make-relations'])
    parser.add_argument('--release-task')
    parser.add_argument('--origin-branch', default='master')
    parser.add_argument('--jira-server')
    parser.add_argument('--jira-user')
    parser.add_argument('--jira-password')
    parser.add_argument(
        '--jira-task-extra',
        type=lambda value: json.loads(value),
        help='Something like \'{"component": "Backend"}\'')

    args = parser.parse_args()

    task_key = args.release_task

    if 'all' in args.commands or 'make-task' in args.commands:
        task_key = make_release_task(
            get_jira_api(args.jira_server, args.jira_user, args.jira_password),
            args.jira_task_extra)
        print('Made new task: {}'.format(task_key))

    if 'all' in args.commands or 'make-branch' in args.commands:
        assert task_key
        make_release_branch(task_key)
        print('Made release branch')

    if 'all' in args.commands or 'make-relations' in args.commands:
        assert task_key
        relations = get_related_tasks(task_key, args.origin_branch)

        if relations.left_pulls:
            sys.stderr.write('Pull requests without tasks: {}\n'.format(
                ', '.join(relations.left_pulls)
            ))

        if not relations.tasks:
            sys.stderr.write('Did not find related tasks')
            exit(1)

        make_links(
            get_jira_api(args.jira_server, args.jira_user, args.jira_password),
            task_key,
            relations.tasks)

        print('Made links from {} to {}'.format(
            task_key,
            ', '.join(relations.tasks)
        ))

        if relations.left_pulls:
            exit(1)
