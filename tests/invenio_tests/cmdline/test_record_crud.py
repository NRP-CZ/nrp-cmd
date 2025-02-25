import json
import time

from typer.testing import CliRunner

runner = CliRunner()


def test_create_record(nrp_repository_config, run_cmdline_and_check) -> None:
    # region: Create a record
    create_output = run_cmdline_and_check(
        [
            "create",
            "record",
            "--model",
            "simple",
            "--community",
            "acom",
            json.dumps(
                {
                    "title": "Test record A",
                }
            ),
        ],
        """
      title                 Test record A   
      """,
    )
    rec = [
        x.strip() for x in create_output.splitlines() if x.strip().startswith("Record ")
    ][0]
    rec_id = rec.split()[-1]
    assert rec_id[5] == "-"
    print("Record ID: ", rec_id)
    # endregion
    create_output = f"Record {rec_id}"

    # region: Get the record
    get_output = run_cmdline_and_check(
        [
            "get",
            "record",
            "--draft",
            rec_id,
            "--expand",
        ],
        create_output
    )

    get_output_full = run_cmdline_and_check(
        [
            "get",
            "record",
            "--draft",
            rec_id,
            "--expand",
            "--verbose"
        ],
        "state draft"
    )
    assert len(get_output_full) > 200

    print("Get quiet")
    get_output_quiet = run_cmdline_and_check(
        ["get", "record", "--draft", rec_id, "--quiet"],
        f"https://127.0.0.1:5000/api/simple/{rec_id}/draft",
    )
    assert (
        get_output_quiet.strip() == f"https://127.0.0.1:5000/api/simple/{rec_id}/draft"
    )
    # endregion

    # region: Update the record
    update_output = run_cmdline_and_check(
        [
            "update",
            "record",
            rec_id,
            json.dumps(
                {
                    "title": "Test record B",
                }
            ),
        ],
        """
        title                 Test record B
        """,
    )
    # endregion

    # region: Get the record to check if the metadata has been updated
    read_updated = run_cmdline_and_check(
        [
            "get",
            "record",
            "--draft",
            rec_id,
            "--expand",
        ],
        """
        title                 Test record B
        """,
    )
    # endregion

    # region: Search for the record by its id
    # propagating the changes to the search index takes 
    # app. 5 seconds, so waiting a bit longer here
    time.sleep(10)
    search_output = run_cmdline_and_check(
        [
            "search",
            "records",
            "--draft",
            f"id:{rec_id}",
        ],
        create_output.replace("Test record A", "Test record B"),
    )
    # endregion


def test_scan(nrp_repository_config, run_cmdline_and_check):
    # region: Create records
    records = [{"title": f"Test record {i}"} for i in range(1, 2)]
    run_cmdline_and_check(
        [
            "create",
            "record",
            "--model",
            "simple",
            "--community",
            "acom",
            json.dumps(records),
            "--set",
            "recid",
        ],
        """
        title                Test record 1
        """,
    )
    # endregion

    variables = nrp_repository_config.load_variables()
    rec_ids = variables["recid"]

    import nrp_cmd.async_client.invenio.records as records_module

    _previous = (
        records_module.OPENSEARCH_SCAN_WINDOW,
        records_module.OPENSEARCH_SCAN_PAGE,
    )

    records_module.OPENSEARCH_SCAN_WINDOW = 20
    records_module.OPENSEARCH_SCAN_PAGE = 10

    # wait for refresh
    time.sleep(5)
    try:
        scan_output = run_cmdline_and_check(
            ["scan", "records", "--model", "simple", "--draft", "--quiet"],
            rec_ids[-1],
        )
        for recid in variables["recid"]:
            assert recid in scan_output

    finally:
        records_module.OPENSEARCH_SCAN_WINDOW = _previous[0]
        records_module.OPENSEARCH_SCAN_PAGE = _previous[1]


def test_delete(nrp_repository_config, run_cmdline_and_check):
    # region: Create records
    run_cmdline_and_check(
        [
            "create",
            "record",
            "--model",
            "simple",
            "--community",
            "acom",
            '{"title": "Test record A"}',
            "--set",
            "recid",
            "--no-progress",
        ],
        """
        title                Test record A
        """,
    )
    # endregion

    variables = nrp_repository_config.load_variables()
    rec_id = variables["recid"][0]

    run_cmdline_and_check(
        [
            "delete",
            "record",
            "--model",
            "simple",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        f"""
        Record with id {rec_id} has been deleted.
        """,
    )

    run_cmdline_and_check(
        [
            "get",
            "record",
            "--model",
            "simple",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        f"""
        Record with id {rec_id} does not exist.
        """,
    )


def test_publish_record_cmd_request(nrp_repository_config, run_cmdline_and_check):
    create_output = run_cmdline_and_check(
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
            "--metadata-only",
            "--set",
            "recid",
        ],
        """
      title                 Test record A   
      """,
    )

    run_cmdline_and_check(
        ["publish", "record", "@recid"],
        """
status submitted
type publish_draft                                           
""",
    )

    # approve
