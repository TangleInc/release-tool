# Release Tool

Table of contents:

* [1. Usage](1-Usage)
    * [1.1. Start release](11-Start-release)
    * [1.2. Start hotfix](12-Start-hotfix)
    * [1.3. Finish release](13-Finish-release)
    * [1.4. Manual](14-Manual)
* [2. Init](2-Init)
    * [2.1. Prerequisites:](21-Prerequisites)
        * [2.1.1. Install poetry](211-Install poetryhttpsgithubcomsdispaterpoetry)
        * [2.1.2. Install virtual env manager](212-Install-virtual-env-manager)
    * [2.2. Configuration: for each local repository](22-Configuration-for-each-local-repository)
        * [2.2.1. Create virtual env](221-Create virtual env)
        * [2.2.2. Tell git to download submodule](222-Tell git to download submodule)
        * [2.2.3. Install dependencies](223-Install dependencies)
        * [2.2.4. Create configuration file `./release_tool.yml`](224-Create-configuration-file-release_toolyml)
        * [2.2.5. Create handy command `./release`](225-Create-handy-command-release)
    * [2.3. (Optional) How to integrate to new repository](23-Optional-How-to-integrate-to-new-repository)


## 1. Usage

```shell
./release -h
```

> **Important:** during release creation the script alerts you about pull requests not linked to any task. You need to check these PRs manually to ensure everything is OK.

### 1.1. Start release

* creates `release-X.X.X` branch from `develop`
* creates Jira release task `{component} release X.X.X`
* detects new commits/PR linked to Jira tasks and links them to Jira release task
* can also link tasks to Jira version (create new or use existing one)

```shell
./release prepare
```

### 1.2. Start hotfix

* creates `release-X.X.X` branch from `master`
* cherry pick specified pull requests using their numbers to a release branch
* creates Jira release task `{component} release X.X.X`
* detects new commits/PR linked to Jira tasks and links them to Jira release task
* can also link tasks to Jira version (create new or use existing one)

```shell
# create hotfix without any commits
./release hotfix
# or cherry pick pull requests
./release hotfix --pr=XXX --pr=...
```

### 1.3. Finish release

* merge a release branch to master
* mark the merge commit with a tag
* merge `master` to `develop`
* move jira tasks to final status ("Done" by default)

```shell
./release finish
```

### 1.4. Manual
```shell
# ./release prepare
./release make-task
./release make-branch
./release make-links

# ./release hotfix --pr=XXX --pr=...
./release make-task
./release make-hotfix-branch --pr=XXX --pr=...
./release make-links

# ./release finish
./release merge-release
./release mark-tasks-done

# ./release merge-release
./release merge-to-master
./release merge-master-to-develop
```


## 2. Init

### 2.1. Prerequisites:

> &#x26a0;&#xfe0f; **Done once per each local machine**

#### 2.1.1. Install [poetry](https://github.com/sdispater/poetry)

Install [poetry](https://github.com/sdispater/poetry) inside your virtualenv (prone to errors) or in a global python (preferable for python developers)

```shell
pip install poetry==1.0.10
```

#### 2.1.2. Install virtual env manager

Install virtual env manager that you are comfortable with (like [pyenv](https://github.com/pyenv/pyenv)).

Example:

```shell
brew install pyenv
brew install pyenv-virtualenv

# this version is officially supports MacBook on M1 chipset
pyenv install 3.8.10
```

Configuration choices:
1. For permanent access to virtual environment put these lines to your shell config (e.g. `.bash_profile`) and then reload your shell
```shell
export PATH=${HOME}/.pyenv/bin
eval "$(pyenv init --path)"
eval "$(pyenv virtualenv-init -)"
```

2. For one time run: simply save these lines or create alias. Then, each time you want to use release_tool you will need to execute them before running release_tool commands.

3. While creating [handy command](#225-Create-handy-command-release`) you can also configure shell environment

After you created `./release` file, edit it to make it like that:

```shell
# these lines for pyenv and can be different for your virtual env manager
export PATH=${HOME}/.pyenv/bin
eval "$(pyenv init --path)"
eval "$(pyenv virtualenv-init -)"

python -m submodules.release_tool.release $*
```


### 2.2. Configuration: for each local repository

> &#x26a0;&#xfe0f; **Done once per each local repository**

#### 2.2.1. Create virtual env

```shell
cd {{project folder}}

# choose appropriate ENV_NAME, e.g. socialfeed
pyenv virtualenv 3.8.10 {{ENV_NAME}}
pyenv local {{ENV_NAME}}
```

add `.python-version` to `.gitignore`

#### 2.2.2. Tell git to download submodule

```shell
submodule update --init
```

#### 2.2.3. Install dependencies

```shell
# activate virtual env created in previous step
cd submodules/release_tool
poetry install

# return to project folder
cd -
```

#### 2.2.4. Create configuration file `./release_tool.yml`

You need to create a config and provide your auth and other info there in order to login to Github and Jira.

To get Github token `Settings` -> `Developer settings` -> `Personal access tokens` -> `Generate new token`
select option repo: `Full control of private repositories`

To get Jira token use [this doc](https://confluence.atlassian.com/cloud/api-tokens-938839638.html)

```shell
# create a personal config, release_tool.yml is a name used by default, so it's strongly suggested
cp submodules/release_tool/config-stub.full.yml release_tool.yml
# add "release_tool.yml" to .gitignore 
```

#### 2.2.5. Create handy command `./release`

To avoid typing long commands such as:
```shell
python -m submodules.release_tool.release -h
```

Make alias to use it like this `./release [command]`
```shell
echo 'python -m submodules.release_tool.release $*' > release
chmod +x release
# you can either commit "release" or add it to .gitignore 
```

### 2.3. (Optional) How to integrate to new repository

> &#x26a0;&#xfe0f; **Done only once per repository**

To start using release_tool in your project add it as a git submodule.

```shell
# add release tool as a submodule
git submodule add git@github.com:TangleInc/release-tool.git submodules/release_tool

git add submodules/release_tool
git commit -m "Integrate release_tool"
git push
```

Then configure your local installation of release_tool check this guide [2.2. Configuration: for each local repository](#22-Configuration-for-each-local-repository)
