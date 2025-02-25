#!/bin/bash

set -e
set -x

BASEDIR="$(realpath "$(dirname "$0")")"
cd "$BASEDIR"

TEST_REPOSITORY_BASE="$BASEDIR/tests/test-repository"
TEST_REPOSITORY_PATH="$TEST_REPOSITORY_BASE/repo"
TEST_REPOSITORY_NRP_CMD="$TEST_REPOSITORY_PATH/nrp"

export TEST_REPOSITORY_BASE TEST_REPOSITORY_PATH TEST_REPOSITORY_NRP_CMD BASEDIR

export NRP_USE_UV=1
uv cache clean

# TODO: remove this once the installer is fixed

install_test_repository() {
  if [ -d "$TEST_REPOSITORY_PATH" ]; then
    rm -rf "$TEST_REPOSITORY_PATH"
  fi
  cd "$TEST_REPOSITORY_BASE"
  curl -sSL https://raw.githubusercontent.com/oarepo/nrp-devtools/main/nrp-installer.sh > nrp-installer.sh
  chmod +x nrp-installer.sh
  ./nrp-installer.sh repo --no-input --initial-config "$BASEDIR/tests/test-repository/oarepo.yaml" </dev/null

  cd repo
  docker compose -f docker/docker-compose.yml down || true
  ./nrp check --fix
  ./nrp model create simple --copy-model-config ../simple.yaml
  ./nrp model compile simple

  # apply patches
  cp ../patches/common/workflows.py common/workflows.py
  cat ../patches/invenio.cfg >>invenio.cfg

  # drop database so that tables from the model are created (otherwise would need to run alembic ...)
  docker compose -f docker/docker-compose.yml down || true
  ./nrp check --fix
  ./nrp build

  source .venv/bin/activate
  

  invenio users create a@test.com --password atestcom -c -a
  invenio users create b@test.com --password btestcom -c -a

  invenio tokens create -n token -u a@test.com >.token_a
  invenio tokens create -n token -u b@test.com >.token_b

  invenio oarepo communities create --public acom "Community A"
  invenio oarepo communities create --public bcom "Community B"

  invenio oarepo communities members add acom a@test.com owner
  invenio oarepo communities members add bcom b@test.com owner
}

(
  # run in a subshell in case environment or cwd is changed
  install_test_repository
)

(
  cd "$TEST_REPOSITORY_BASE"
  cd repo
  source .venv/bin/activate
  FLASK_DEBUG=1 invenio run --cert ./docker/development.crt --key ./docker/development.key &
  invenio_pid=$!
  sleep 10
  echo "$invenio_pid" >.invenio_pid
)

kill_invenio() {
  if [ -f "$TEST_REPOSITORY_BASE/repo/.invenio_pid" ]; then
    invenio_pid=$(cat "$TEST_REPOSITORY_BASE/repo/.invenio_pid")
    kill -9 "$invenio_pid" || true
    rm -f "$TEST_REPOSITORY_BASE/repo/.invenio_pid"
  fi
}

trap kill_invenio EXIT

# run tests
(
  python -m venv .venv
  source .venv/bin/activate
  pip install -U setuptools pip wheel
  pip install -e '.[tests]'
  pytest -v tests/invenio_tests
)