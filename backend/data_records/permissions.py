from workspaces.models import Membership


WRITE_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
}


def can_read_table(user, table_asset):
    return Membership.objects.filter(
        organization=table_asset.data_source.workspace.organization,
        user=user,
        is_active=True,
    ).exists()


def can_write_table(user, table_asset):
    return Membership.objects.filter(
        organization=table_asset.data_source.workspace.organization,
        user=user,
        is_active=True,
        role__in=WRITE_ROLES,
    ).exists()
