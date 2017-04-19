#!env/bin/python

import argparse
import json
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

    MERGE_RELEASE = 'merge-release'


PR_RE = re.compile(r'\(#(\d+)\)', flags=re.U | re.I)
REPO_RE = re.compile(r'[/:](\w+/\w+)\.git')

ARGUMENTS = (
    'github-password',
    'github-user',
    'jira-password',
    'jira-project',
    'jira-release-project'
    'jira-server',
    'jira-task-extra',
    'jira-user',
    'release-set',
)

GetTaskResponse = namedtuple('GetTaskResponse', ('tasks', 'left_pulls'))


def git_fetch():
    subprocess.check_call('git fetch', shell=True, stdout=subprocess.PIPE)


def get_branch_name(release_project, version):
    return '{}-{}'.format(release_project.lower(), version)


def get_pr_task(github_repository, pr, task_re):
    pull = github_repository.get_pull(pr)
    return task_re.findall(pull.title)


def execute_commands(commands, **format_kwargs):
    return subprocess.check_output(
        (' && '.join(commands)).format(**format_kwargs),
        shell=True
    )


def get_related_tasks(github_repository, task_re, release_project, release_version):
    git_fetch()
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
        left_pulls=list(sorted(left_pulls))
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


def make_release_branch(release_set, release_version, release_project):
    git_fetch()
    execute_commands(
        [
            'git checkout origin/develop',
            'git checkout -b {branch}',
            '{release_set} {release_version}',
            'git commit -am "Release {release_version}"',
            'git push origin {branch}'
        ],
        branch=get_branch_name(
            release_project=release_project,
            version=release_version),
        release_set=release_set,
        release_version=release_version
    )


def merge_release(github_repository, release_project, release_version):
    git_fetch()
    branch = get_branch_name(
        release_project=release_project,
        version=release_version)

    execute_commands(
        [
            'git checkout origin/{branch}'
            'git tag {version}',
            'git push origin {version}',
            'git checkout master',
            'git reset --hard origin/master',
            'git merge --no-ff origin/{branch} -m "Merge origin/{branch}"',
            'git push origin master',
            'git push origin :{branch}'
        ],
        branch=branch,
        version=release_version
    )

    github_repository.create_pull(
        title='Release {version}'.format(version=release_version),
        body='',
        base='develop',
        head='master'
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


def run(commands, api_client, jira_task_extra, task_key, task_re, release_project,
        release_version, release_set):

    assert release_project
    assert release_version
    assert task_re

    if Command.PREPARE in commands or Command.MAKE_TASK in commands:
        task_key = make_release_task(
            jira_client=api_client.jira,
            extra_fields=jira_task_extra,
            release_project=release_project,
            release_version=release_version)
        print('Made new task: {}'.format(task_key))

    if Command.PREPARE in commands or Command.MAKE_BRANCH in commands:
        assert release_set
        make_release_branch(
            release_set=release_set,
            release_version=release_version,
            release_project=release_project)
        print('Made release branch')

    if Command.PREPARE in commands or Command.MAKE_RELATIONS in commands:
        assert task_key
        assert api_client.github_repository

        relations = get_related_tasks(
            github_repository=api_client.github_repository,
            task_re=task_re,
            release_project=release_project,
            release_version=release_version
        )

        if relations.left_pulls:
            sys.stderr.write('Pull requests without tasks: {}\n'.format(
                ', '.join(map(str, relations.left_pulls))
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

        if relations.left_pulls:
            exit(1)

    if Command.MERGE_RELEASE in commands:
        assert api_client.github_repository

        merge_release(
            github_repository=api_client.github_repository,
            release_project=release_project,
            release_version=release_version
        )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'commands',
        nargs='+',
        choices=[
            Command.PREPARE,
            Command.MAKE_TASK,
            Command.MAKE_BRANCH,
            Command.MAKE_RELATIONS,
            Command.MERGE_RELEASE
        ])
    parser.add_argument('--task')
    parser.add_argument('--release-version')
    parser.add_argument('--config')

    for arg in ARGUMENTS:
        if arg == 'jira-task-extra':
            parser.add_argument(
                '--{}'.format(arg),
                type=lambda value: json.loads(value),
                help='Something like \'{"component": "Backend"}\'')
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
    if not config:
        return args

    for name in ARGUMENTS:
        if name not in config:
            continue

        if getattr(args, name.replace('-', '_')) is None:
            setattr(args, name.replace('-', '_'), config[name])

    return args


if __name__ == '__main__':
    _args = parse_and_combine_args()
    assert _args.jira_project

    _release_task = _args.task.upper() if _args.task else None
    _task_re = re.compile(r'({}-\d+)\s'.format(_args.jira_project), flags=re.U | re.I)
    run(
        commands=_args.commands,
        api_client=API(_args),
        jira_task_extra=_args.jira_task_extra,
        task_key=_release_task,
        task_re=_task_re,
        release_project=_args.jira_release_project,
        release_version=_args.release_version,
        release_set=_args.release_set,
    )
