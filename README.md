# Release Tool

## Init

### Prerequisites:

1. Install [poetry](https://github.com/sdispater/poetry) inside your virtualenv or in global python (preferable for python developers)

2. Prepare virtual env with your tool of choice (like [pyenv](https://github.com/pyenv/pyenv)) based on python version specified in [pyproject.toml](./pyproject.toml)

Example of how it can be done:

done once per computer:
```bash
brew install pyenv
brew install pyenv-virtualenv

# update your profile (e.g. `.bash_profile`)
echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bash_profile

# reload you bash

# "socialfeed" is a project name where we are integrating release-tools
pyenv install 3.7.3
# choose appropriate ENV_NAME, e.g. socialfeed
pyenv virtualenv 3.7.3 {{ENV_NAME}}
```

done once per repository
```bash
pyenv local {{ENV_NAME}}
pip install poetry==1.0.10

# add `.python-version` to `.gitignore`
```

### Step 1. Init submodule

```bash
# cd (to your project folder)
```

#### Option 1. Integration to project (done once per repository)

```bash
# add release tool as a submodule
git submodule add git@github.com:TangleInc/release-tool.git submodules/release_tool
```

#### Option 2. For developer to configure release tool

```bash
submodule update --init
```

### Step 2. Install dependencies

```bash
# activate virtual env created in previous step
cd submodules/release_tool
poetry install

# return to project folder
cd -
```

### Step 3. Create configuration file

You need to create a config and provide your auth and other info there in order to login to Github and Jira.

To get Github token `Settings` -> `Developer settings` -> `Personal access tokens` -> `Generate new token`
select option repo: `Full control of private repositories`

To get Jira token use [this doc](https://confluence.atlassian.com/cloud/api-tokens-938839638.html)

```bash
# create a personal config, release_tool.yml is a name used by default, so it's strongly suggested
cp submodules/release_tool/config-stub.full.yml release_tool.yml
# add "release_tool.yml" to .gitignore 
```

### Step 4. Create handy command

To avoid typing long commands such as:
```bash
python -m submodules.release_tool.release -h
```

Make alias to use it like this `./release [command]`
```bash
echo 'python -m submodules.release_tool.release $*' > release
chmod +x release
# you can either commit "release" or add it to .gitignore 
```

## Usage

Now you do the magic!

```bash
./release -h
```

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
