#
# This Dockerfile is for Travis builds, so:
# 1. it requires release/deploy tools.
# 2. it doesn't bake in project dependencies at the build stage
#
FROM python:3.10.4-slim

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    # required to manage release branches
    git \
	# to get/set version in json files
	jq \
    # clean
    && rm -rf /var/lib/apt/lists/*

# Global git config
RUN git config --global core.excludesFile /root/.gitignore_global \
	&& git config --global --add safe.directory /app

# Install installation tools
RUN pip3 install --upgrade pip \
    && pip3 install poetry==1.1.10 \
    && poetry config virtualenvs.create false

# Install release_tool dependencies
COPY poetry.lock /poetry.lock
COPY pyproject.toml /pyproject.toml
RUN poetry install

# place of release-tool
COPY . /release_tool/
ENV PYTHONPATH="/release_tool:${PYTHONPATH}"

# place of application that release-tool will be applied to
WORKDIR /app

ENTRYPOINT ["python", "-m", "release"]
