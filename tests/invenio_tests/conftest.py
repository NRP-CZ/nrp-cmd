#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
import logging
import re
import tempfile
from pathlib import Path

import pytest
from yarl import URL

from nrp_cmd.config import Config, RepositoryConfig

logging.basicConfig(level=logging.ERROR)


@pytest.fixture(scope="session")
def token_a() -> str:
    """Return the bearer token for the local test repository."""
    return (
        (Path(__file__).parent.parent / "test-repository" / "repo" / ".token_a")
        .read_text()
        .strip()
    )


@pytest.fixture(scope="session")
def local_repository_url() -> URL:
    """Return the URL of the local test repository."""
    return URL("https://127.0.0.1:5000")


@pytest.fixture(scope="session")
def zenodo_url() -> URL:
    """Return the URL of the local test repository."""
    return URL("https://www.zenodo.org")


@pytest.fixture(scope="session")
def rdm_demo_url() -> URL:
    """Return the URL of the local test repository."""
    return URL("https://inveniordm.web.cern.ch/")


@pytest.fixture(scope="session")
def arl_url() -> URL:
    """Return the URL of the local test repository."""
    return URL("https://asep.lib.cas.cz/arl-cav/cs/vyhledavani/")


@pytest.fixture(scope="session")
def clarin_url() -> URL:
    """Return the URL of the local test repository."""
    return URL("https://lindat.mff.cuni.cz/repository/xmlui/")


@pytest.fixture(scope="function")
def empty_config():
    """Return an empty configuration."""
    with tempfile.NamedTemporaryFile(suffix=".json") as f:
        config = Config.from_file(Path(f.name))
        config.save()
        yield config


@pytest.fixture(scope="function")
def nrp_repository_config(token_a, local_repository_url, zenodo_url, rdm_demo_url):
    """Return the configuration of the NRP client with a local test repository as well as zenodo."""
    with tempfile.NamedTemporaryFile(suffix=".json") as f:
        config = Config.from_file(Path(f.name))
        config.per_directory_variables = True
        config.add_repository(
            RepositoryConfig(
                alias="local",
                url=local_repository_url,
                token=token_a,
                verify_tls=False,
                retry_count=5,
                retry_after_seconds=10,
            )
        )
        config.add_repository(
            RepositoryConfig(
                alias="zenodo",
                url=zenodo_url,
                token=None,
                verify_tls=True,
                retry_count=5,
                retry_after_seconds=10,
            )
        )
        config.add_repository(
            RepositoryConfig(
                alias="rdm_demo",
                url=rdm_demo_url,
                token=None,
                verify_tls=True,
                retry_count=5,
                retry_after_seconds=10,
            )
        )
        config.default_alias = "local"
        config.save()
        yield config


@pytest.fixture(scope="function")
def local_repository_config(nrp_repository_config: Config):
    return nrp_repository_config.get_repository("local")

@pytest.fixture(scope="function")
def zenodo_repository_config(nrp_repository_config):
    return nrp_repository_config.get_repository("zenodo")

@pytest.fixture(scope="function")
def rdm_demo_repository_config(nrp_repository_config):
    return nrp_repository_config.get_repository("rdm_demo")


@pytest.fixture
def in_output():
    def in_output_func(output, expected, ignore_extra_lines=True):
        expected = re.sub(" +", " ", expected)
        expected_lines = [x.strip() for x in expected.split("\n")]
        expected_lines = [x for x in expected_lines if x]

        output = re.sub(" +", " ", output)
        output_lines = [x.strip() for x in output.split("\n")]
        output_lines = [x for x in output_lines if x]

        ok = True
        while output_lines and expected_lines:
            if output_lines[0] == expected_lines[0]:
                output_lines.pop(0)
                expected_lines.pop(0)
                ok = True
            else:
                if ok:
                    print("Expected line: ", expected_lines[0])
                ok = False
                print("Skipping line: ", output_lines[0])
                output_lines.pop(0)
        if expected_lines:
            print("Expected lines not found:")
            print("\n".join(expected_lines))
            print("Actual lines:")
            print("\n".join(output_lines))
            return False

        if output_lines and not ignore_extra_lines:
            print("Extra lines found:")
            print("\n".join(output_lines))
            return False

        return True

    return in_output_func
