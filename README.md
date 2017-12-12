Release Tool
============


# Init
```bash
git clone git@github.com:megabuz/release-tool.git ../release-tool
pip install -r ../release-tool/requirements.txt
```

now you can use

```bash
python ../release-tool/release.py --config=../release-tool/release.yml [command]
```

or make aliases to use it like this `./release --config=release.yml [command]`

```bash
ln -s ../release-tool/release.py release
chmod +x release

cp ../release-tool/release.yml .
# edit release.yml

# add these 2 files to .gitignore if they are not already there
```

# Usage

## 1. New release
```bash
./release --config=release.yml --version=X.Y.Z prepare
```

## 2. Hotfix
```bash
./release --config=release.yml --version=X.Y.Z hotfix --pr=XXX --pr=...
```

## 3. Merge
```bash
./release --config=release.yml --version=X.Y.Z merge-release
```

## 4. Manual
```bash
./release --config=release.yml --version=X.Y.Z make-task

# release / hotfix
./release --config=release.yml --version=X.Y.Z make-branch
./release --config=release.yml --version=X.Y.Z make-hotfix-branch --pr=XXX --pr=...

./release --config=release.yml --version=X.Y.Z make-relations --task=XXX

./release --config=release.yml --version=X.Y.Z merge-to-master
./release --config=release.yml --version=X.Y.Z merge-master-to-develop
```
