from vicarius_v2_mcp.server import mcp


def test_instructions_tell_the_model_how_tenant_and_params_work():
    text = mcp.instructions
    assert "`tenant` is optional" in text and "default tenant" in text
    assert "Do not ask the user which tenant" in text
    assert "`params` object" in text
    # The instructions are sent to the model with every conversation, so keep them short.
    assert len(text) < 1200
