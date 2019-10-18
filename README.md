# Release Tool

## Init

### Prerequisites:

1. Install [poetry](https://github.com/sdispater/poetry) inside your virtualenv or in global python (preferable for python developers)

2. Prepare virtual env with your tool of choice (like [pyenv](https://github.com/pyenv/pyenv)) based on python version specified in [pyproject.toml](./pyproject.toml)

Example of how it can be done:

```bash
brew install pyenv
brew install pyenv-virtualenv

# "socialfeed" is a project name where we are integrating release-tools
pyenv virtualenv 3.7.3 socialfeed
pyenv local socialfeed
pip install poetry

# add `.python-version` to `.gitignore`
```

### Integration to project

```bash
# cd (to your project folder)
# activate virtual env created in previous step

# add release tool as a submodule
git submodule add git@github.com:TangleInc/release-tool.git submodules/release_tool
cd submodules/release_tool
poetry install
```

You need to create a config and provide your auth and other info there in order to login to Github and Jira.

To get Github token `Settings` -> `Developer settings` -> `Personal access tokens` -> `Generate new token`
select option repo: `Full control of private repositories`

To get Jira token use [this doc](https://confluence.atlassian.com/cloud/api-tokens-938839638.html)

```bash
# return to project folder
cd -
# create a personal config, release_tool.yml is a name used by default, so it's strongly suggested
cp submodules/release_tool/config-stub.yml release_tool.yml
# add "release_tool.yml" to .gitignore 
```

Now you do the magic!

```bash
python -m submodules.release_tool.release -h
```

Or even better — make aliases to use it like this `./release [command]`

```bash
echo 'python -m submodules.release_tool.release $*' > release
chmod +x release
# you can either commit "release" or add it to .gitignore 
```

## Usage

**Important:** during release creation the script alerts you about pull requests not linked to any task. You need to check these PRs manually to ensure everything is OK.

### New full branch release

Make a release branch from the entire `develop`.

```bash
./release prepare
```

### New specific commits release

Cherry pick specified pull requests using their numbers to a release branch.

```bash
./release hotfix --pr=XXX --pr=...
```

### Finish release

Merge a release branch to master, mark the merge commit with a tag and merge `master` to `develop`. Also move jira tasks and release as "Done".

```bash
./release finish
```

### Manual
```bash
./release make-task

# release / hotfix
./release make-branch
./release make-hotfix-branch --pr=XXX --pr=...
./release make-links
./release merge-release
./release merge-to-master
./release merge-master-to-develop
./release mark-tasks-done


```
