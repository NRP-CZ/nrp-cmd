
import re
from collections.abc import Callable

import pytest
from typer.testing import CliRunner

from nrp_cmd.config import Config


@pytest.fixture
def run_cmdline_and_check(
    nrp_repository_config: Config, in_output: Callable[[str, str], bool]
) -> Callable[[list[str], str], str]:
    """Run a command and assert the output."""
    runner = CliRunner()
    from nrp_cmd.cli import app

    def _run(command: list[str], *args) -> str:
        if len(args) == 1:
            env = {}
            expected_output = args[0]
        elif len(args) == 2:
            env = args[0]
            expected_output = args[1]
        else:
            raise ValueError("Invalid number of arguments")

        result = runner.invoke(
            app,
            command,
            catch_exceptions=False,
            env={
                "NRP_CMD_CONFIG_PATH": str(nrp_repository_config._config_file_path),
                **env,
            },
        )
        stdout = result.stdout
        print(stdout)
        stdout = re.sub(" +", " ", stdout)
        assert in_output(
            stdout,
            expected_output,
        )
        return stdout

    return _run