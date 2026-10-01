import json

import httpx
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_reports import (
    list_scan_reports,
    download_scan_report,
    list_reports,
    create_report,
    delete_report,
    generate_report,
    list_report_executions,
    list_audit_logs,
    list_filter_values,
    get_deployment_settings,
    update_deployment_settings,
)


@respx.mock
def test_list_scan_reports(vicarius_v2_env):
    respx.get(f"{_base('acme')}/evidence-files").mock(return_value=httpx.Response(200, json=[{"id": "ev-1"}]))
    assert json.loads(list_scan_reports())[0]["id"] == "ev-1"


@respx.mock
def test_download_scan_report_binary(vicarius_v2_env):
    respx.get(f"{_base('acme')}/evidence-files/ev-1/download").mock(
        return_value=httpx.Response(200, content=b"%PDF-fakebytes", headers={"content-type": "application/pdf"})
    )
    result = json.loads(download_scan_report("ev-1"))
    assert result["contentType"] == "application/pdf"
    assert result["contentLength"] == len(b"%PDF-fakebytes")


@respx.mock
def test_reports_crud(vicarius_v2_env):
    respx.get(f"{_base('acme')}/reports").mock(return_value=httpx.Response(200, json=[{"id": "rpt-1"}]))
    route = respx.post(f"{_base('acme')}/reports").mock(return_value=httpx.Response(200, json={"id": "rpt-2"}))
    respx.delete(f"{_base('acme')}/reports/rpt-1").mock(return_value=httpx.Response(200, json={"type": "deleted"}))
    respx.post(f"{_base('acme')}/reports/generate").mock(return_value=httpx.Response(200, json={"id": "rpt-3"}))

    assert json.loads(list_reports())[0]["id"] == "rpt-1"
    assert json.loads(create_report("Monthly", {"filters": {}}))["id"] == "rpt-2"
    assert json.loads(route.calls.last.request.content) == {"name": "Monthly", "specJson": {"filters": {}}}
    assert json.loads(delete_report("rpt-1"))["type"] == "deleted"
    assert json.loads(generate_report("critical findings last 30 days"))["id"] == "rpt-3"


@respx.mock
def test_list_report_executions(vicarius_v2_env):
    respx.get(f"{_base('acme')}/reports/executions").mock(return_value=httpx.Response(200, json=[{"executionId": "e-1"}]))
    assert json.loads(list_report_executions(size=25))[0]["executionId"] == "e-1"


@respx.mock
def test_list_audit_logs(vicarius_v2_env):
    respx.get(f"{_base('acme')}/settings/auditLogs").mock(return_value=httpx.Response(200, json=[{"action": "LOGIN"}]))
    assert json.loads(list_audit_logs())[0]["action"] == "LOGIN"


@respx.mock
def test_list_filter_values(vicarius_v2_env):
    respx.get(f"{_base('acme')}/filters/severity/values").mock(return_value=httpx.Response(200, json=["Critical", "High"]))
    assert json.loads(list_filter_values("severity")) == ["Critical", "High"]


@respx.mock
def test_deployment_settings(vicarius_v2_env):
    respx.get(f"{_base('acme')}/settings/deployment").mock(return_value=httpx.Response(200, json={"batchSizePerHour": 10}))
    route = respx.put(f"{_base('acme')}/settings/deployment").mock(return_value=httpx.Response(200, json={"batchSizePerHour": 20}))
    assert json.loads(get_deployment_settings())["batchSizePerHour"] == 10
    result = json.loads(update_deployment_settings({"batchSizePerHour": 20}))
    assert result["batchSizePerHour"] == 20
    assert json.loads(route.calls.last.request.content) == {"batchSizePerHour": 20}
