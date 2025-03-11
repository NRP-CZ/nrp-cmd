import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

runner = CliRunner()

# import logging

# logging.basicConfig(level=logging.ERROR)
# logging.getLogger("nrp_cmd.communication").setLevel(logging.INFO)

def test_file_ops(nrp_repository_config, run_cmdline_and_check):
    # region: Create files
    run_cmdline_and_check(
        [
            "create",
            "record",
            "--model",
            "simple",
            "--community",
            "acom",
            json.dumps({
                "title": "Test record A",
            }),
            "--set",
            "recid",
        ],
        """
        title Test record A
        """,
    )
    
    recid = nrp_repository_config.load_variables()["recid"][0]
    
    with tempfile.NamedTemporaryFile(suffix=".txt") as greeting:
        greeting.write(b"Hello, World!")
        greeting.flush()

        run_cmdline_and_check(
            [
                "upload",
                "file",
                "@recid",
                greeting.name,
                "{ \"title\": \"Greeting\" }",
                "--verbose"
            ],
            {"COLUMNS": "1000"},
            f"""
            File {Path(greeting.name).name} @ record {recid}
            """
        )
        first_file_output = f"{Path(greeting.name).name} 13 {recid}/files/{Path(greeting.name).name}/content"
        first_key = Path(greeting.name).name

    with tempfile.NamedTemporaryFile(suffix=".txt", mode='wb') as greeting:
        for __ in range(1000):
            greeting.write(b'0' * 1024 * 1024)
        greeting.flush()

        run_cmdline_and_check(
            [
                "upload",
                "file",
                "@recid",
                greeting.name,
                '{ "title": "Greeting 2" }',
            ],
            {"COLUMNS": "1000"},
            f"""
            {Path(greeting.name).name} 1048576000 {recid}/files/{Path(greeting.name).name}/content 
            """,
        )
        second_file_output = f"{Path(greeting.name).name} 1048576000 {recid}/files/{Path(greeting.name).name}/content"
    # endregion
    
    # region: list files
    sorted_lines = sorted([first_file_output, second_file_output])
    run_cmdline_and_check(
        [
            "list",
            "files",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        f"""
        {sorted_lines[0]}
        {sorted_lines[1]}
        """
    )
    
    # endregion
    
    # region update metadata

    run_cmdline_and_check(
        [
            "update",
            "file",
            recid,
            first_key,
            json.dumps({
                "title": "Greeting 3",
            }),
            "--verbose",
        ],
        {"COLUMNS": "1000"},
        "Metadata {'title': 'Greeting 3'}",
    )

    # endregion
    
    # region: delete files
    
    run_cmdline_and_check(
        [
            "delete",
            "file",
            recid,
            first_key,
        ],
        {"COLUMNS": "1000"},
        f"""
        Deleted file {first_key} in record {recid}.
        """
    )
    
    output = run_cmdline_and_check(
        [
            "list",
            "files",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        f"""
        {second_file_output}
        """
    )
    assert "Greeting 3" not in output
    assert first_key not in output


def test_create_record_with_files(nrp_repository_config, run_cmdline_and_check):
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as greeting:
        for __ in range(20):
            greeting.write(b"0" * 1024 * 1024)
        greeting.flush()

        create_output = run_cmdline_and_check(
            [
                "create",
                "record",
                "--model",
                "simple",
                "--community",
                "acom",
                "--quiet",
                "--no-progress",
                json.dumps({
                    "title": "Test record A",
                }),
                str(greeting.name),
                "{}",
            ],
            "",
        )
        record_url = [x.strip() for x in create_output.splitlines() if x.strip()][0]
        print("Record URL: ", record_url)

    # list files on the record
    run_cmdline_and_check(
        [
            "list",
            "files",
            record_url,
        ],
        {"COLUMNS": "1000"},
        f"""
        {Path(greeting.name).name} 20971520 {record_url}/files/{Path(greeting.name).name}/content
        """,
    )


def test_download_record_with_files(nrp_repository_config, run_cmdline_and_check):
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as greeting:
        greeting.write(b"Hello, World!")
        greeting.flush()

        create_output = run_cmdline_and_check(
            [
                "create",
                "record",
                "--model",
                "simple",
                "--community",
                "acom",
                "--quiet",
                "--no-progress",
                json.dumps({
                    "title": "Test record A",
                }),
                str(greeting.name),
                "{}",
            ],
            "",
        )
        record_url = [x.strip() for x in create_output.splitlines() if x.strip()][0]
        print("Record URL: ", record_url)

    with tempfile.TemporaryDirectory() as tempdir:
        run_cmdline_and_check(
            ["download", "record", record_url, "-o", tempdir, "--no-progress"],
            {
                "COLUMNS": "1000",
            },
            f"Record {record_url} downloaded to {tempdir}",
        )
        metadata = Path(tempdir) / "metadata.json"
        print("Metadata text", metadata.read_text())
        assert "Test record A" in metadata.read_text()

        attachment = Path(tempdir) / Path(greeting.name).name
        assert attachment.read_bytes() == b"Hello, World!"
