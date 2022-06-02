# Release Tool

Table of Contents
=================

* [Release Tool](#release-tool)
  * [1\. Usage](#1-usage)
    * [1\.1\. Start release](#11-start-release)
    * [1\.2\. Start hotfix](#12-start-hotfix)
    * [1\.3\. Finish release](#13-finish-release)
    * [1\.4\. Manual](#14-manual)
  * [2\. Init](#2-init)
    * [2\.1 Installation (as a docker container)](#21-installation-as-a-docker-container)
    * [2\.2 Configuration](#22-configuration)
    * [2\.2\.1 Secrets: GitHub token](#221-secrets-github-token)
    * [2\.2\.1 Secrets: Jira token](#221-secrets-jira-token)

Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc.go)

```bash
gh-md-toc README.md
```


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

### 2.1 Installation (as a docker container)

> &#x26a0;&#xfe0f; **Done once per each computer**

1. Install docker
2. login to TangleInc docker account: 

```bash
docker login -u statusmoney -p <DOCKER_TOKEN>
```

3. Download the latest image:
   
```bash
docker pull statusmoney/release-tool:latest
```

### 2.2 Configuration

> &#x26a0;&#xfe0f; **Done once per each repo**

Copy the latest script and config files from ure: add  to your project root (See [examples](examples)).

* `release` - handy shortcuts - make executable and add to git
* `release_tool.yml` - config file for local machine - **add to .gitignore**
* `release_tool.ci.yml` - config file for CI - verify parameters (such as `component`) and add to git

Next, in order to set up integration with GitHub and Jira, secret tokens should be added to `release.yml` (as-is) and to `travis.yml` (encrypted with `travis encrypt <secret>`).

### 2.2.1 Secrets: GitHub token

To get Github token `Settings` -> `Developer settings` -> `Personal access tokens` -> `Generate new token`
select option repo: `Full control of private repositories`

### 2.2.1 Secrets: Jira token

To get Jira token use [this doc](https://confluence.atlassian.com/cloud/api-tokens-938839638.html)
