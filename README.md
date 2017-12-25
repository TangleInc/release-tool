Release Tool
============


# Init
```bash
mkdir $PROJECT_ROOT && cd $PROJECT_ROOT                                 # create a project dir and enter
git clone git@github.com:TangleInc/release-tool.git ../release-tool     # clone the project
python3 -m venv ./env && source ./env/bin/activate                      # create and activate virtual env
pip install -r ./requirements.txt                                       # install requirements
```

You need to create a config and provide your auth and other info there in order to login to Github and Jira.

```bash
cp config-stub.yml config.yml                                           # create a personal config
open config.yml
```

Now you do the magic!

```bash
source ./env/bin/activate
python ./release.py --config=./config.yml [command]
```

Or even better — make aliases to use it like this `./release --config=config.yml [command]`

```bash
ln -s ../release-tool/release.py release
chmod +x release

cp ../release-tool/release.yml .
# edit release.yml

# add these 2 files to .gitignore if they are not already there
```

# Usage

**Important:** during release creation the script alerts you about pull requests not linked to any task. You need to check these PRs manually to ensure everything is OK.

## New full branch release

Make a release branch from the entire `develop`.

```bash
./release --config=config.yml --version=X.Y.Z prepare
```

## New specific commits release

Cherry pick specified pull requests using their numbers to a release branch.

```bash
./release --config=config.yml --version=X.Y.Z hotfix --pr=XXX --pr=...
```

## Merge

Merge a release branch to master, mark the merge commit with a tag and merge `master` to `develop`.

```bash
./release --config=config.yml --version=X.Y.Z merge-release
```

## Manual
```bash
./release --config=config.yml --version=X.Y.Z make-task

# release / hotfix
./release --config=config.yml --version=X.Y.Z make-branch
./release --config=config.yml --version=X.Y.Z make-hotfix-branch --pr=XXX --pr=...

./release --config=config.yml --version=X.Y.Z make-links --task=XXX

./release --config=config.yml --version=X.Y.Z merge-to-master
./release --config=config.yml --version=X.Y.Z merge-master-to-develop
```
