from invenio_rdm_records.services.config import RDMRecordServiceConfig
from invenio_records_resources.services import (
    ConditionalLink,
    LinksTemplate,
    RecordLink,
    pagination_links,
)
from oarepo_communities.services.components.default_workflow import (
    CommunityDefaultWorkflowComponent,
)
from oarepo_communities.services.components.include import CommunityInclusionComponent
from oarepo_communities.services.links import CommunitiesLinks
from oarepo_runtime.services.components import (
    CustomFieldsComponent,
    OwnersComponent,
    process_service_configs,
)
from oarepo_runtime.services.config import (
    has_draft,
    has_file_permission,
    has_permission,
    has_published_record,
    is_published_record,
)
from oarepo_runtime.services.config.service import PermissionsPresetsConfigMixin
from oarepo_runtime.services.records import pagination_links_html
from oarepo_workflows.services.components.workflow import WorkflowComponent

from simple.records.api import SimpleDraft, SimpleRecord
from simple.services.records.permissions import SimplePermissionPolicy
from simple.services.records.results import SimpleRecordItem, SimpleRecordList
from simple.services.records.schema import SimpleSchema
from simple.services.records.search import (
    SimpleSearchDraftsOptions,
    SimpleSearchOptions,
)


class SimpleServiceConfig(PermissionsPresetsConfigMixin, RDMRecordServiceConfig):
    """SimpleRecord service config."""

    result_item_cls = SimpleRecordItem

    result_list_cls = SimpleRecordList

    PERMISSIONS_PRESETS = ["community-workflow"]

    url_prefix = "/simple/"

    base_permission_policy_cls = SimplePermissionPolicy

    schema = SimpleSchema

    search = SimpleSearchOptions

    record_cls = SimpleRecord

    service_id = "simple"

    search_item_links_template = LinksTemplate
    draft_cls = SimpleDraft
    search_drafts = SimpleSearchDraftsOptions

    @property
    def components(self):
        return process_service_configs(self) + [
            CommunityDefaultWorkflowComponent,
            CommunityInclusionComponent,
            OwnersComponent,
            CustomFieldsComponent,
            WorkflowComponent,
        ]

    model = "simple"

    @property
    def links_item(self):
        return {
            "applicable-requests": ConditionalLink(
                cond=is_published_record(),
                if_=RecordLink("{+api}/simple/{id}/requests/applicable"),
                else_=RecordLink("{+api}/simple/{id}/draft/requests/applicable"),
            ),
            "communities": CommunitiesLinks(
                {
                    "self": "{+api}/communities/{id}",
                    "self_html": "{+ui}/communities/{slug}/records",
                }
            ),
            "draft": RecordLink(
                "{+api}/simple/{id}/draft",
                when=has_draft() & has_permission("read_draft"),
            ),
            "edit_html": RecordLink(
                "{+ui}/simple/{id}/edit", when=has_draft() & has_permission("update")
            ),
            "files": ConditionalLink(
                cond=is_published_record(),
                if_=RecordLink(
                    "{+api}/simple/{id}/files", when=has_file_permission("list_files")
                ),
                else_=RecordLink(
                    "{+api}/simple/{id}/draft/files",
                    when=has_file_permission("list_files"),
                ),
            ),
            "latest": RecordLink(
                "{+api}/simple/{id}/versions/latest", when=has_permission("read")
            ),
            "latest_html": RecordLink(
                "{+ui}/simple/{id}/latest", when=has_permission("read")
            ),
            "publish": RecordLink(
                "{+api}/simple/{id}/draft/actions/publish",
                when=has_permission("publish"),
            ),
            "record": RecordLink(
                "{+api}/simple/{id}",
                when=has_published_record() & has_permission("read"),
            ),
            "requests": ConditionalLink(
                cond=is_published_record(),
                if_=RecordLink("{+api}/simple/{id}/requests"),
                else_=RecordLink("{+api}/simple/{id}/draft/requests"),
            ),
            "self": ConditionalLink(
                cond=is_published_record(),
                if_=RecordLink("{+api}/simple/{id}", when=has_permission("read")),
                else_=RecordLink(
                    "{+api}/simple/{id}/draft", when=has_permission("read_draft")
                ),
            ),
            "self_html": ConditionalLink(
                cond=is_published_record(),
                if_=RecordLink("{+ui}/simple/{id}", when=has_permission("read")),
                else_=RecordLink(
                    "{+ui}/simple/{id}/preview", when=has_permission("read_draft")
                ),
            ),
            "versions": RecordLink(
                "{+api}/simple/{id}/versions", when=has_permission("search_versions")
            ),
        }

    @property
    def links_search_item(self):
        return {
            "self": ConditionalLink(
                cond=is_published_record(),
                if_=RecordLink("{+api}/simple/{id}", when=has_permission("read")),
                else_=RecordLink(
                    "{+api}/simple/{id}/draft", when=has_permission("read_draft")
                ),
            ),
            "self_html": ConditionalLink(
                cond=is_published_record(),
                if_=RecordLink("{+ui}/simple/{id}", when=has_permission("read")),
                else_=RecordLink(
                    "{+ui}/simple/{id}/preview", when=has_permission("read_draft")
                ),
            ),
        }

    @property
    def links_search(self):
        return {
            **pagination_links("{+api}/simple/{?args*}"),
            **pagination_links_html("{+ui}/simple/{?args*}"),
        }

    @property
    def links_search_drafts(self):
        return {
            **pagination_links("{+api}/user/simple/{?args*}"),
            **pagination_links_html("{+ui}/user/simple/{?args*}"),
        }

    @property
    def links_search_versions(self):
        return {
            **pagination_links("{+api}/simple/{id}/versions{?args*}"),
        }
