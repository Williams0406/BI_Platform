from workspaces.models import Membership


CONNECT_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


def user_can_manage_datasource(user, data_source):
    return Membership.objects.filter(
        organization=data_source.workspace.organization,
        user=user,
        is_active=True,
        role__in=CONNECT_ROLES,
    ).exists()
