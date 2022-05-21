#
# This Dockerfile is for Travis builds, so:
# 1. it requires release/deploy tools.
# 2. it doesn't bake in project dependencies at the build stage
#
FROM brunneis/python:3.7.7-ubuntu-18.04

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    # required to manage release branches
    git \
    # clean
    && rm -rf /var/lib/apt/lists/*

# Install installation tools
RUN pip3 install --upgrade pip \
    && pip3 install poetry==1.1.10 \
    && poetry config virtualenvs.create false

# Install release_tool dependencies
COPY poetry.lock /poetry.lock
COPY pyproject.toml /pyproject.toml
RUN poetry install

# Install deployment dependencies
# would be great to drop them
RUN pip3 install awscli click==7.0

# place of release-tool
COPY . /release_tool/
ENV PYTHONPATH="/release_tool:${PYTHONPATH}"

# place of application that release-tool will be applied to
WORKDIR /app

ENTRYPOINT ["python", "-m", "release", "--noinput"]
