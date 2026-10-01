import json
import respx
import httpx
from vicarius_mcp.server import (
    list_users, list_user_invitations, invite_user,
    resend_invitation, delete_invitation, _base,
)

USER_STUB = {"userId": "u-1", "userEmail": "alice@example.com", "userRole": "admin"}
INV_STUB = {"userInvitationId": "inv-1", "userInvitationEmail": "bob@example.com"}


@respx.mock
def test_list_users(vicarius_env):
    respx.get(f"{_base()}/user/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [USER_STUB]})
    )
    result = json.loads(list_users())
    assert result["serverResponseObject"][0]["userEmail"] == "alice@example.com"


@respx.mock
def test_list_user_invitations(vicarius_env):
    respx.get(f"{_base()}/userInvitation/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [INV_STUB]})
    )
    result = json.loads(list_user_invitations())
    assert result["serverResponseObject"][0]["userInvitationEmail"] == "bob@example.com"


@respx.mock
def test_invite_user(vicarius_env):
    respx.put(f"{_base()}/userInvitation/insert").mock(
        return_value=httpx.Response(200, json={"userInvitationId": "inv-2"})
    )
    result = json.loads(invite_user("carol@example.com", "viewer"))
    assert result["userInvitationId"] == "inv-2"


@respx.mock
def test_resend_invitation(vicarius_env):
    respx.post(f"{_base()}/userInvitation/resend").mock(
        return_value=httpx.Response(200, json={"resent": True})
    )
    result = json.loads(resend_invitation("inv-1"))
    assert result["resent"] is True


@respx.mock
def test_delete_invitation(vicarius_env):
    respx.delete(f"{_base()}/userInvitation/delete").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )
    result = json.loads(delete_invitation("inv-1"))
    assert result["deleted"] is True
