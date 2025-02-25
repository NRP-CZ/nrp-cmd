from invenio_rdm_records.services.config import (
    RDMSearchDraftsOptions as RDMRecordSearchDraftsOptions,
)
from invenio_rdm_records.services.config import (
    RDMSearchOptions as RDMRecordSearchOptions,
)

from . import facets


class SimpleSearchOptions(RDMRecordSearchOptions):
    """SimpleRecord search options."""

    facet_groups = {}

    facets = {
        "metadata_version": facets.metadata_version,
        "state": facets.state,
        "state_timestamp": facets.state_timestamp,
        **getattr(RDMRecordSearchOptions, "facets", {}),
        "record_status": facets.record_status,
        "has_draft": facets.has_draft,
    }


class SimpleSearchDraftsOptions(RDMRecordSearchDraftsOptions):
    """SimpleRecord search options."""

    facet_groups = {}

    facets = {
        "metadata_version": facets.metadata_version,
        "state": facets.state,
        "state_timestamp": facets.state_timestamp,
        **getattr(RDMRecordSearchDraftsOptions, "facets", {}),
        "record_status": facets.record_status,
        "has_draft": facets.has_draft,
    }
