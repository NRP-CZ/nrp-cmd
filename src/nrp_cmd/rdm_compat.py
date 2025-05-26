import math
import re
from urllib.parse import urlparse

from yarl import URL

from .types.info import (
    ModelInfo,
    ModelInfoContentType,
    ModelInfoLinks,
    RepositoryInfo,
    RepositoryInfoLinks,
)


def _generate_rdm_vocabulary(
    url: URL, vocabulary_type: str, vocabulary_name: str, special: bool, schema: str
) -> ModelInfo:
    url_prefix = url / "api" if special else url / "api" / "vocabularies"
    return ModelInfo(
        schema=schema,
        type=vocabulary_type,
        name=vocabulary_name,
        description="Vocabulary for " + vocabulary_name,
        version="unknown",
        features=[
            "rdm",
        ],
        links=ModelInfoLinks(
            records=url_prefix / vocabulary_type,
        ),
        content_types=[
            ModelInfoContentType(
                content_type="application/json",
                name="Invenio RDM JSON",
                description="Vocabulary JSON",
                schema=None,
                can_export=True,
                can_deposit=False,
            )
        ],
        metadata=False
    )


def make_rdm_info(url: URL, verify_tls: bool = True) -> RepositoryInfo:
    """If repository does not provide the info endpoint, we assume it is a plain invenio rdm."""
    url = url.with_path("/")
    import requests

    homepage = requests.get(str(url), verify=verify_tls).text
    grp = re.search('meta name="generator" content="InvenioRDM ([0-9.]+)"', homepage)
    if grp:
        rdm_version = math.floor(float(grp.group(1)))
    else:
        raise ValueError("Could not determine Invenio RDM version from homepage")

    transfers = ["L"]
    if rdm_version >= 13:
        transfers.extend(["F", "R", "M"])

    if urlparse(str(url)).netloc in ("zenodo.org", "sandbox.zenodo.org"):
        version = "Zenodo"
        default_content_type = "application/vnd.inveniordm.v1+json"
    else:
        version = "RDM"
        default_content_type = "application/json"

    return RepositoryInfo(
        schema="local://introspection-v1.0.0.json",
        name="RDM repository",
        description="",
        version=version,
        invenio_version=f"RDM {rdm_version}",
        transfers=transfers,
        links=RepositoryInfoLinks(
            self_=url,
            records=url / "api" / "records",
            drafts=url / "api" / "user" / "records",
            requests=url / "api" / "requests",
            models=None,
        ),
        default_model="records",
        default_content_type=default_content_type,
        models={
            "records": ModelInfo(
                schema="local://records-v6.0.0.json",
                type="rdm-records",
                name="RDM Records",
                description="RDM Records",
                version="unknown",
                features=[
                    "rdm",
                ],
                links=ModelInfoLinks(
                    html=url / "records",
                    records=url / "api" / "records",
                    drafts=url / "api" / "user" / "records",
                    model=None,
                ),
                content_types=[
                    ModelInfoContentType(
                        content_type="application/json",
                        name="Invenio RDM JSON",
                        description="Invenio RDM JSON as described in "
                        "https://inveniordm.docs.cern.ch/reference/metadata/",
                        schema=url / "schemas" / "records" / "record-v6.0.0.json",
                        can_export=True,
                        can_deposit=True,
                    )
                ],
                metadata=True,
            ),
            "affiliations": _generate_rdm_vocabulary(
                url,
                "affiliations",
                "Affiliations",
                special=True,
                schema="local://affiliation-v1.0.0.json",
            ),
            "awards": _generate_rdm_vocabulary(
                url,
                "awards",
                "Awards",
                special=True,
                schema="local://award-v1.0.0.json",
            ),
            "funders": _generate_rdm_vocabulary(
                url,
                "funders",
                "Funders",
                special=True,
                schema="local://funder-v1.0.0.json",
            ),
            "subjects": _generate_rdm_vocabulary(
                url,
                "subjects",
                "Subjects",
                special=True,
                schema="local://subject-v1.0.0.json",
            ),
            "names": _generate_rdm_vocabulary(
                url,
                "names",
                "Names",
                special=True,
                schema="local://name-v1.0.0.json",
            ),
            "licenses": _generate_rdm_vocabulary(
                url,
                "licenses",
                "Licenses",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
            "resource_types": _generate_rdm_vocabulary(
                url,
                "resource_types",
                "Resource Types",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
            "languages": _generate_rdm_vocabulary(
                url,
                "languages",
                "Languages",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
            "titletypes": _generate_rdm_vocabulary(
                url,
                "titletypes",
                "Title Types",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
            "creatorsroles": _generate_rdm_vocabulary(
                url,
                "creatorsroles",
                "Creators Roles",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
            "contributorsroles": _generate_rdm_vocabulary(
                url,
                "contributorsroles",
                "Contributors Roles",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
            "descriptiontypes": _generate_rdm_vocabulary(
                url,
                "descriptiontypes",
                "Description Types",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
            "datetypes": _generate_rdm_vocabulary(
                url,
                "datetypes",
                "Date Types",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
            "relationtypes": _generate_rdm_vocabulary(
                url,
                "relationtypes",
                "Relation Types",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
            "removalreasons": _generate_rdm_vocabulary(
                url,
                "removalreasons",
                "Removal Reasons",
                special=False,
                schema="local://vocabulary-v1.0.0.json",
            ),
        },
    )
