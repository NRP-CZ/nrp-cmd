from yarl import URL

from nrp_cmd.async_client.invenio import AsyncInvenioRepositoryClient
from nrp_cmd.converter import converter


async def test_can_handle_nrp_repository(local_repository_url):
    api_url = await AsyncInvenioRepositoryClient.can_handle_repository(
        url=local_repository_url,
        verify_tls=False,
    )
    assert api_url == local_repository_url.with_path("/api")


async def test_can_handle_zenodo_repository(zenodo_url):
    api_url = await AsyncInvenioRepositoryClient.can_handle_repository(
        url=zenodo_url,
        verify_tls=True,
    )
    assert api_url == zenodo_url.with_path("/api")


async def test_can_handle_rdm_demo_repository(rdm_demo_url):
    api_url = await AsyncInvenioRepositoryClient.can_handle_repository(
        url=rdm_demo_url,
        verify_tls=True,
    )
    assert api_url == rdm_demo_url.with_path("/api")


async def test_can_handle_arl(arl_url):
    api_url = await AsyncInvenioRepositoryClient.can_handle_repository(
        url=arl_url,
        verify_tls=True,
    )
    assert api_url == None


async def test_can_handle_repository_with_invalid_url():
    api_url = await AsyncInvenioRepositoryClient.can_handle_repository(
        url=URL("https://cesnet.cz"),
        verify_tls=True,
    )
    assert api_url == None


async def test_can_handle_clarin(clarin_url):
    api_url = await AsyncInvenioRepositoryClient.can_handle_repository(
        url=clarin_url,
        verify_tls=True,
    )
    assert api_url == None


async def test_info_nrp_repository(local_repository_config):
    client = await AsyncInvenioRepositoryClient.from_configuration(
        local_repository_config
    )
    info = await client.get_repository_info(refresh=True)
    data = converter.unstructure(info)
    data.pop("invenio_version")
    assert data == {
        "schema": "local://introspection-v1.0.0",
        "name": "Test repository for nrp-cmd",
        "description": "",
        "version": "local development",
        "links": {
            "self": "https://127.0.0.1:5000/.well-known/repository/",
            "records": "https://127.0.0.1:5000/api/search/",
            "drafts": "https://127.0.0.1:5000/api/user/search/",
            "models": "https://127.0.0.1:5000/.well-known/repository/models",
            "requests": "https://127.0.0.1:5000/api/requests/",
            "api": "https://127.0.0.1:5000/api",
        },
        "default_content_type": "application/json",
        "transfers": ["L", "F", "R", "M"],
        "models": {
            "simple": {
                "type": "simple",
                "schema": "local://simple-1.0.0.json",
                "name": "simple",
                "description": "",
                "version": "1.0.0",
                "features": ["requests", "drafts", "files"],
                "links": {
                    "records": "https://127.0.0.1:5000/api/simple/",
                    "html": "https://127.0.0.1:5000/simple/",
                    "drafts": "https://127.0.0.1:5000/api/user/simple/",
                    "deposit": "https://127.0.0.1:5000/api/simple/",
                    "model": "https://127.0.0.1:5000/.well-known/repository/models/simple",
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Internal json serialization of Simple",
                        "description": "This content type is serving this model's native format as described on model link.",
                        "schema": "https://127.0.0.1:5000/.well-known/repository/schema/simple-1.0.0.json",
                        "can_export": True,
                        "can_deposit": True,
                    },
                    {
                        "content_type": "application/vnd.inveniordm.v1+json",
                        "name": "Native UI JSON",
                        "description": "",
                        "can_export": True,
                        "can_deposit": False,
                    },
                ],
                "metadata": True,
            },
            "affiliations": {
                "type": "affiliations",
                "schema": "local://affiliations/affiliation-v1.0.0.json",
                "name": "Affiliations",
                "description": "Vocabulary for Affiliations",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {"records": "https://127.0.0.1:5000/api/affiliations"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/affiliations/affiliation-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "awards": {
                "type": "awards",
                "schema": "local://awards/award-v1.0.0.json",
                "name": "Awards",
                "description": "Vocabulary for Awards",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {"records": "https://127.0.0.1:5000/api/awards"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/awards/award-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "funders": {
                "type": "funders",
                "schema": "local://funders/funder-v1.0.0.json",
                "name": "Funders",
                "description": "Vocabulary for Funders",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {"records": "https://127.0.0.1:5000/api/funders"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/funders/funder-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "subjects": {
                "type": "subjects",
                "schema": "local://subjects/subject-v1.0.0.json",
                "name": "Subjects",
                "description": "Vocabulary for Subjects",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {"records": "https://127.0.0.1:5000/api/subjects"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/subjects/subject-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "names": {
                "type": "names",
                "schema": "local://names/name-v1.0.0.json",
                "name": "Names",
                "description": "Vocabulary for Names",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {"records": "https://127.0.0.1:5000/api/names"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/names/name-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "affiliations-vocab": {
                "type": "affiliations-vocab",
                "schema": "local://affiliations/affiliation-v1.0.0.json",
                "name": "Writable Affiliations",
                "description": "Vocabulary for Writable Affiliations",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {
                    "records": "https://127.0.0.1:5000/api/vocabularies/affiliations-vocab",
                    "deposit": "https://127.0.0.1:5000/api/vocabularies/affiliations-vocab",
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/affiliations/affiliation-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": True,
                    }
                ],
                "metadata": False,
            },
            "awards-vocab": {
                "type": "awards-vocab",
                "schema": "local://awards/award-v1.0.0.json",
                "name": "Writable Awards",
                "description": "Vocabulary for Writable Awards",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {
                    "records": "https://127.0.0.1:5000/api/vocabularies/awards-vocab",
                    "deposit": "https://127.0.0.1:5000/api/vocabularies/awards-vocab",
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/awards/award-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": True,
                    }
                ],
                "metadata": False,
            },
            "funders-vocab": {
                "type": "funders-vocab",
                "schema": "local://funders/funder-v1.0.0.json",
                "name": "Writable Funders",
                "description": "Vocabulary for Writable Funders",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {
                    "records": "https://127.0.0.1:5000/api/vocabularies/funders-vocab",
                    "deposit": "https://127.0.0.1:5000/api/vocabularies/funders-vocab",
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/funders/funder-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": True,
                    }
                ],
                "metadata": False,
            },
            "subjects-vocab": {
                "type": "subjects-vocab",
                "schema": "local://subjects/subject-v1.0.0.json",
                "name": "Writable Subjects",
                "description": "Vocabulary for Writable Subjects",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {
                    "records": "https://127.0.0.1:5000/api/vocabularies/subjects-vocab",
                    "deposit": "https://127.0.0.1:5000/api/vocabularies/subjects-vocab",
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/subjects/subject-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": True,
                    }
                ],
                "metadata": False,
            },
            "names-vocab": {
                "type": "names-vocab",
                "schema": "local://names/name-v1.0.0.json",
                "name": "Writable Names",
                "description": "Vocabulary for Writable Names",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {
                    "records": "https://127.0.0.1:5000/api/vocabularies/names-vocab",
                    "deposit": "https://127.0.0.1:5000/api/vocabularies/names-vocab",
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/names/name-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": True,
                    }
                ],
                "metadata": False,
            },
            "languages": {
                "type": "languages",
                "schema": "local://vocabularies/vocabulary-v1.0.0.json",
                "name": "languages",
                "description": "Vocabulary for languages",
                "version": "unknown",
                "features": ["rdm", "vocabulary"],
                "links": {
                    "records": "https://127.0.0.1:5000/api/vocabularies/languages",
                    "deposit": "https://127.0.0.1:5000/api/vocabularies/languages",
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "schema": "https://127.0.0.1:5000/schemas/vocabularies/vocabulary-v1.0.0.json",
                        "can_export": True,
                        "can_deposit": True,
                    }
                ],
                "metadata": False,
            },
        },
        "default_model": "simple",
        "features": ["drafts", "workflows", "requests", "communities", "request_types"],
    }


async def test_info_zenodo(zenodo_repository_config):
    client = await AsyncInvenioRepositoryClient.from_configuration(
        zenodo_repository_config
    )
    info = await client.get_repository_info(refresh=True)
    print(converter.unstructure(info))
    assert converter.unstructure(info) == {
        "schema": "local://introspection-v1.0.0.json",
        "name": "RDM repository",
        "description": "",
        "version": "RDM",
        "invenio_version": "RDM 13",
        "links": {
            "self": "https://www.zenodo.org/",
            "records": "https://www.zenodo.org/api/records",
            "drafts": "https://www.zenodo.org/api/user/records",
            "requests": "https://www.zenodo.org/api/requests",
        },
        "features": [],
        "transfers": ["L", "F", "R", "M"],
        "default_content_type": "application/json",
        "models": {
            "records": {
                "type": "rdm-records",
                "schema": "local://records-v6.0.0.json",
                "name": "RDM Records",
                "description": "RDM Records",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/records",
                    "html": "https://www.zenodo.org/records",
                    "drafts": "https://www.zenodo.org/api/user/records",
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Invenio RDM JSON as described in https://inveniordm.docs.cern.ch/reference/metadata/",
                        "schema": "https://www.zenodo.org/schemas/records/record-v6.0.0.json",
                        "can_export": True,
                        "can_deposit": True,
                    }
                ],
                "metadata": True,
            },
            "affiliations": {
                "type": "affiliations",
                "schema": "local://affiliation-v1.0.0.json",
                "name": "Affiliations",
                "description": "Vocabulary for Affiliations",
                "version": "unknown",
                "features": ["rdm"],
                "links": {"records": "https://www.zenodo.org/api/affiliations"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "awards": {
                "type": "awards",
                "schema": "local://award-v1.0.0.json",
                "name": "Awards",
                "description": "Vocabulary for Awards",
                "version": "unknown",
                "features": ["rdm"],
                "links": {"records": "https://www.zenodo.org/api/awards"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "funders": {
                "type": "funders",
                "schema": "local://funder-v1.0.0.json",
                "name": "Funders",
                "description": "Vocabulary for Funders",
                "version": "unknown",
                "features": ["rdm"],
                "links": {"records": "https://www.zenodo.org/api/funders"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "subjects": {
                "type": "subjects",
                "schema": "local://subject-v1.0.0.json",
                "name": "Subjects",
                "description": "Vocabulary for Subjects",
                "version": "unknown",
                "features": ["rdm"],
                "links": {"records": "https://www.zenodo.org/api/subjects"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "names": {
                "type": "names",
                "schema": "local://name-v1.0.0.json",
                "name": "Names",
                "description": "Vocabulary for Names",
                "version": "unknown",
                "features": ["rdm"],
                "links": {"records": "https://www.zenodo.org/api/names"},
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "licenses": {
                "type": "licenses",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Licenses",
                "description": "Vocabulary for Licenses",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/licenses"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "resource_types": {
                "type": "resource_types",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Resource Types",
                "description": "Vocabulary for Resource Types",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/resource_types"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "languages": {
                "type": "languages",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Languages",
                "description": "Vocabulary for Languages",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/languages"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "titletypes": {
                "type": "titletypes",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Title Types",
                "description": "Vocabulary for Title Types",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/titletypes"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "creatorsroles": {
                "type": "creatorsroles",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Creators Roles",
                "description": "Vocabulary for Creators Roles",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/creatorsroles"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "contributorsroles": {
                "type": "contributorsroles",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Contributors Roles",
                "description": "Vocabulary for Contributors Roles",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/contributorsroles"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "descriptiontypes": {
                "type": "descriptiontypes",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Description Types",
                "description": "Vocabulary for Description Types",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/descriptiontypes"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "datetypes": {
                "type": "datetypes",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Date Types",
                "description": "Vocabulary for Date Types",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/datetypes"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "relationtypes": {
                "type": "relationtypes",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Relation Types",
                "description": "Vocabulary for Relation Types",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/relationtypes"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
            "removalreasons": {
                "type": "removalreasons",
                "schema": "local://vocabulary-v1.0.0.json",
                "name": "Removal Reasons",
                "description": "Vocabulary for Removal Reasons",
                "version": "unknown",
                "features": ["rdm"],
                "links": {
                    "records": "https://www.zenodo.org/api/vocabularies/removalreasons"
                },
                "content_types": [
                    {
                        "content_type": "application/json",
                        "name": "Invenio RDM JSON",
                        "description": "Vocabulary JSON",
                        "can_export": True,
                        "can_deposit": False,
                    }
                ],
                "metadata": False,
            },
        },
        "default_model": "records",
    }
