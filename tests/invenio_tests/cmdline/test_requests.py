def test_list_requests(nrp_repository_config, run_cmdline_and_check) -> None:
    # region: Create a record
    create_output = run_cmdline_and_check(
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
        ],
        """
      title                 Test record A   
      """,
    )

    recid = nrp_repository_config.load_variables()["recid"][0]

    list_requests_output = run_cmdline_and_check(
        [
            "list",
            "requests",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        f"""
        id publish_draft                                                               
        actions                                                                                  
        create   {recid}/requests/publish_draft  
      """,
    )


def test_accept_publish_request(nrp_repository_config, run_cmdline_and_check) -> None:
    # region: Create a record
    create_output = run_cmdline_and_check(
        [
            "create",
            "record",
            "--model",
            "simple",
            "--metadata-only",
            "--community",
            "acom",
            '{"title": "Test record A"}',
            "--set",
            "recid",
        ],
        """
      title                 Test record A   
      """,
    )

    recid = nrp_repository_config.load_variables()["recid"][0]

    create_request_output = run_cmdline_and_check(
        ["create", "request", "publish_draft", "@recid", "@reqid"],
        {"COLUMNS": "1000"},
        """
        status         submitted                                                                                 
        type           publish_draft 
        """,
    )

    reqid = nrp_repository_config.load_variables()["reqid"][0]

    list_requests_output = run_cmdline_and_check(
        [
            "list",
            "requests",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        """
        status         submitted                                                                                   
        type           publish_draft 
        """,
    )

    # publish the record
    accept_request_output = run_cmdline_and_check(
        [
            "accept",
            "request",
            "@reqid",
        ],
        {"COLUMNS": "1000"},
        """
        status         accepted                                                                                   
        type           publish_draft 
        """,
    )

    assert "published record" in accept_request_output
    assert "published record html" in accept_request_output


def test_decline_publish_request(nrp_repository_config, run_cmdline_and_check) -> None:
    # region: Create a record
    create_output = run_cmdline_and_check(
        [
            "create",
            "record",
            "--model",
            "simple",
            "--metadata-only",
            "--community",
            "acom",
            '{"title": "Test record A"}',
            "--set",
            "recid",
        ],
        """
      title                 Test record A   
      """,
    )

    recid = nrp_repository_config.load_variables()["recid"][0]

    create_request_output = run_cmdline_and_check(
        ["create", "request", "publish_draft", "@recid", "@reqid"],
        {"COLUMNS": "1000"},
        """
        status         submitted                                                                                 
        type           publish_draft 
        """,
    )

    reqid = nrp_repository_config.load_variables()["reqid"][0]

    list_requests_output = run_cmdline_and_check(
        [
            "list",
            "requests",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        """
        status         submitted                                                                                   
        type           publish_draft 
        """,
    )

    # publish the record
    accept_request_output = run_cmdline_and_check(
        [
            "decline",
            "request",
            "@reqid",
        ],
        {"COLUMNS": "1000"},
        """
        status         declined                                                                                   
        type           publish_draft 
        """,
    )

    assert "published record" not in accept_request_output
    assert "published record html" not in accept_request_output

    # can create the request
    list_requests_output = run_cmdline_and_check(
        [
            "list",
            "requests",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        f"""
        create   {recid}/requests/publish_draft  
      """,
    )


def test_cancel_publish_request(nrp_repository_config, run_cmdline_and_check) -> None:
    # region: Create a record
    create_output = run_cmdline_and_check(
        [
            "create",
            "record",
            "--model",
            "simple",
            "--metadata-only",
            "--community",
            "acom",
            '{"title": "Test record A"}',
            "--set",
            "recid",
        ],
        """
      title                 Test record A   
      """,
    )

    recid = nrp_repository_config.load_variables()["recid"][0]

    create_request_output = run_cmdline_and_check(
        [
            "create",
            "request",
            "publish_draft",
            "--no-submit",  # so that it can be cancelled
            "@recid",
            "@reqid",
        ],
        {"COLUMNS": "1000"},
        """
        status         created                                                                                 
        type           publish_draft 
        """,
    )

    reqid = nrp_repository_config.load_variables()["reqid"][0]

    list_requests_output = run_cmdline_and_check(
        [
            "list",
            "requests",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        """
        status         created                                                                                   
        type           publish_draft 
        """,
    )

    # publish the record
    accept_request_output = run_cmdline_and_check(
        [
            "cancel",
            "request",
            "@reqid",
        ],
        {"COLUMNS": "1000"},
        """
        status         cancelled                                                                                   
        type           publish_draft 
        """,
    )

    assert "published record" not in accept_request_output
    assert "published record html" not in accept_request_output

    # can create the request
    list_requests_output = run_cmdline_and_check(
        [
            "list",
            "requests",
            "@recid",
        ],
        {"COLUMNS": "1000"},
        f"""
        create   {recid}/requests/publish_draft  
      """,
    )
