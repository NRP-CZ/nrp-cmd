#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# invenio-nrp is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#

##
## workflows
##

from functools import partial

from invenio_records_permissions.generators import AnyUser, AuthenticatedUser
from oarepo_communities.services.permissions.generators import PrimaryCommunityRole
from oarepo_communities.services.permissions.policy import (
    CommunityDefaultWorkflowPermissions,
)
from oarepo_runtime.services.permissions.generators import RecordOwners
from oarepo_workflows import (
    IfInState,
    Workflow,
    WorkflowRequest,
    WorkflowRequestPolicy,
    WorkflowTransitions,
)


class PermissiveWorkflowWithoutAutoApprovePermissions(
    CommunityDefaultWorkflowPermissions
):
    can_read = [
        IfInState("published", [AnyUser()]),  # changed this
    ] + CommunityDefaultWorkflowPermissions.can_read

    can_read_deleted = can_read
    can_manage_files = [AuthenticatedUser()]


class PermissiveWorkflowWithoutAutoApproveRequests(WorkflowRequestPolicy):
    publish_draft = WorkflowRequest(
        # if the record is in draft state, the owner or curator can request publishing
        requesters=[IfInState("draft", then_=[RecordOwners()])],
        recipients=[PrimaryCommunityRole("owner")],
        transitions=WorkflowTransitions(accepted="published"),
    )

    edit_published_record = WorkflowRequest(
        requesters=[
            IfInState(
                "published",
                then_=[
                    RecordOwners(),
                ],
            )
        ],
        recipients=[PrimaryCommunityRole("owner")],
    )

    delete_published_record = WorkflowRequest(
        requesters=[
            IfInState(
                "published",
                then_=[
                    RecordOwners(),
                ],
            )
        ],
        recipients=[PrimaryCommunityRole("owner")],
        transitions=WorkflowTransitions(accepted="deleted"),
    )


PermissiveWorkflowWithoutAutoApprove = partial(
    Workflow,
    label="Permissive workflow without auto approve",
    permission_policy_cls=PermissiveWorkflowWithoutAutoApprovePermissions,
    request_policy_cls=PermissiveWorkflowWithoutAutoApproveRequests,
)


##
## end of workflows
##
