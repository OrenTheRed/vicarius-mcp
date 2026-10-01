import json

import httpx
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_tenants import (
    list_configured_tenants,
    list_organizations,
    list_organization_sites,
    list_api_keys,
    create_api_key,
    get_api_key,
    delete_api_key,
    list_org_members,
    invite_members,
    remove_org_member,
    resend_member_invitation,
    list_user_groups,
    create_user_group,
    list_user_group_members,
    batch_add_group_members,
    get_user_site_permissions,
    update_user_site_permission,
)


def test_list_configured_tenants(vicarius_v2_env):
    result = json.loads(list_configured_tenants())
    assert sorted(result["tenants"]) == ["acme", "beta"]


@respx.mock
def test_list_organizations(vicarius_v2_env):
    respx.get(f"{_base('acme')}/me/availableOrganization").mock(
        return_value=httpx.Response(200, json=[{"name": "Acme Corp", "org_id": "o-1"}])
    )
    result = json.loads(list_organizations())
    assert result[0]["name"] == "Acme Corp"


@respx.mock
def test_list_organization_sites(vicarius_v2_env):
    respx.get(f"{_base('acme')}/me/organizations/o-1/sites").mock(
        return_value=httpx.Response(200, json=[{"name": "Global", "site_id": "s-1"}])
    )
    result = json.loads(list_organization_sites("o-1"))
    assert result[0]["site_id"] == "s-1"


@respx.mock
def test_list_api_keys(vicarius_v2_env):
    route = respx.get(f"{_base('acme')}/apiKeys").mock(
        return_value=httpx.Response(200, json=[{"id": "k-1", "name": "ci-key"}])
    )
    result = json.loads(list_api_keys())
    assert result[0]["name"] == "ci-key"
    assert route.calls.last.request.url.params["sort"] == "createdAt"


@respx.mock
def test_create_api_key(vicarius_v2_env):
    route = respx.post(f"{_base('acme')}/apiKeys").mock(
        return_value=httpx.Response(200, json={"secret": "s3cr3t"})
    )
    result = json.loads(create_api_key("ci-key", expiration_date_ms=1735689600000))
    assert result["secret"] == "s3cr3t"
    body = json.loads(route.calls.last.request.content)
    assert body == {"name": "ci-key", "expirationDate": 1735689600000}


@respx.mock
def test_get_and_delete_api_key(vicarius_v2_env):
    respx.get(f"{_base('acme')}/apiKeys/k-1").mock(return_value=httpx.Response(200, json={"id": "k-1"}))
    respx.delete(f"{_base('acme')}/apiKeys/k-1").mock(return_value=httpx.Response(200, json=True))
    assert json.loads(get_api_key("k-1"))["id"] == "k-1"
    assert json.loads(delete_api_key("k-1")) is True


@respx.mock
def test_list_org_members(vicarius_v2_env):
    respx.get(f"{_base('acme')}/organizations/members").mock(
        return_value=httpx.Response(200, json=[{"userId": "u-1", "email": "a@example.com"}])
    )
    result = json.loads(list_org_members())
    assert result[0]["email"] == "a@example.com"


@respx.mock
def test_invite_members(vicarius_v2_env):
    route = respx.post(f"{_base('acme')}/organizations/invitations/batch").mock(
        return_value=httpx.Response(200, json=[{"identityId": "u-2", "status": "invited"}])
    )
    result = json.loads(invite_members(["new@example.com"], first_names=["New"], site_id="s-1"))
    assert result[0]["status"] == "invited"
    body = json.loads(route.calls.last.request.content)
    assert body["users"][0] == {"email": "new@example.com", "firstName": "New", "siteId": "s-1"}


@respx.mock
def test_remove_and_resend(vicarius_v2_env):
    respx.delete(f"{_base('acme')}/organizations/members/u-1").mock(return_value=httpx.Response(200, json={}))
    respx.post(f"{_base('acme')}/organizations/members/u-1/resend-invitation").mock(return_value=httpx.Response(200, json={}))
    assert not remove_org_member("u-1").startswith("ERROR")
    assert not resend_member_invitation("u-1").startswith("ERROR")


@respx.mock
def test_user_groups(vicarius_v2_env):
    respx.get(f"{_base('acme')}/settings/user-groups").mock(return_value=httpx.Response(200, json=[{"id": "g-1"}]))
    respx.post(f"{_base('acme')}/settings/user-groups").mock(return_value=httpx.Response(200, json={"id": "g-2", "displayName": "Admins"}))
    respx.get(f"{_base('acme')}/settings/user-groups/g-1/members").mock(return_value=httpx.Response(200, json=[{"userId": "u-1"}]))
    route = respx.post(f"{_base('acme')}/settings/user-groups/g-1/members/batchAdd").mock(return_value=httpx.Response(200, json={}))

    assert json.loads(list_user_groups())[0]["id"] == "g-1"
    assert json.loads(create_user_group("Admins"))["displayName"] == "Admins"
    assert json.loads(list_user_group_members("g-1"))[0]["userId"] == "u-1"
    batch_add_group_members("g-1", ["u-1", "u-2"])
    body = json.loads(route.calls.last.request.content)
    assert body == {"userIds": ["u-1", "u-2"]}


@respx.mock
def test_site_permissions(vicarius_v2_env):
    respx.get(f"{_base('acme')}/settings/user/u-1/site-permissions").mock(
        return_value=httpx.Response(200, json=[{"siteId": "s-1", "permission": "VIEWER"}])
    )
    route = respx.put(f"{_base('acme')}/settings/user/u-1/site-permissions/s-1").mock(
        return_value=httpx.Response(200, json={"userId": "u-1", "siteId": "s-1", "status": "updated"})
    )
    assert json.loads(get_user_site_permissions("u-1"))[0]["permission"] == "VIEWER"
    result = json.loads(update_user_site_permission("u-1", "s-1", "ADMIN"))
    assert result["status"] == "updated"
    assert "x-idempotency-key" in route.calls.last.request.headers


def test_update_user_site_permission_rejects_bad_value(vicarius_v2_env):
    result = update_user_site_permission("u-1", "s-1", "OWNER")
    assert result.startswith("ERROR")
