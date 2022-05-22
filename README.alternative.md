# Alternative installation - as a submodule or full installation


> &#x26a0;&#xfe0f; **Not recommended, unless you want to contribute. Use Recommended way to use releaso-tool is [README.md](README.md).**


Table of Contents
=================

* [Alternative installation \- as a submodule or full installation](#alternative-installation---as-a-submodule-or-full-installation)
    * [1\. Prerequisites:](#1-prerequisites)
      * [1\.1\. Install poetry](#11-install-poetry)
      * [1\.2\. Install virtual env manager](#12-install-virtual-env-manager)
    * [2\. Initial integration of release\-tool](#2-initial-integration-of-release-tool)
    * [3\. Configuration: for each local repository that already has release\-tool integrated as a submodule](#3-configuration-for-each-local-repository-that-already-has-release-tool-integrated-as-a-submodule)
      * [3\.1\. Create virtual env](#31-create-virtual-env)
      * [3\.2\. Tell git to download submodule](#32-tell-git-to-download-submodule)
      * [3\.3\. Install dependencies](#33-install-dependencies)
      * [3\.4\. Configure](#34-configure)

Created by [gh-md-toc](https://github.com/ekalinin/github-markdown-toc.go)

```bash
gh-md-toc README.alternative.md
```


### 1. Prerequisites:

> &#x26a0;&#xfe0f; **Done once per each computer**

#### 1.1. Install poetry

Install [poetry](https://github.com/sdispater/poetry) inside your virtualenv (prone to errors) or in a global python (preferable for python developers)

```shell
pip install poetry==1.0.10
```

#### 1.2. Install virtual env manager

Install virtual env manager that you are comfortable with (like [pyenv](https://github.com/pyenv/pyenv)).

Example:

```shell
brew install pyenv
brew install pyenv-virtualenv

# this version is officially supports MacBook on M1 chipset
pyenv install 3.8.10
```


### 2. Initial integration of release-tool

> &#x26a0;&#xfe0f; **Done only once per repository, scripts and configs are committed to repo**

To start using release-tool in your project, add it as a git submodule.

```shell
# add release tool as a submodule
git submodule add git@github.com:TangleInc/release-tool.git submodules/release_tool

git add submodules/release_tool
git commit -m "Integrate release_tool"
git push
```

### 3. Configuration: for each local repository that already has release-tool integrated as a submodule

> &#x26a0;&#xfe0f; **Done once per each local repository**

#### 3.1. Create virtual env

```shell
cd {{project folder}}

# choose appropriate ENV_NAME, e.g. socialfeed
pyenv virtualenv 3.8.10 {{ENV_NAME}}
pyenv local {{ENV_NAME}}
```

add `.python-version` to `.gitignore`

#### 3.2. Tell git to download submodule

```shell
git submodule update --init
```

#### 3.3. Install dependencies

```shell
# activate virtual env created in previous step
cd submodules/release_tool
poetry install

# return to project folder
cd -
```

#### 3.4. Configure

Configuration is the same as (See [README.md](README.md#2.2-Configuration)). 

After configuration, you will be able to use release-tool as follows:

```bash
./release native [command]
```
