import pytest
from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from custom_components.greenchoice.config_flow import GreenchoiceConfigFlow
from custom_components.greenchoice.const import DOMAIN, DEFAULT_NAME

@pytest.fixture
def mock_setup_entry():
    """Mock the setup entry function."""
    with patch("custom_components.greenchoice.async_setup_entry", return_value=True) as mock:
        yield mock

@pytest.mark.asyncio
async def test_config_flow_user(hass, mock_setup_entry):
    """Test the user step of the config flow."""
    flow = GreenchoiceConfigFlow()
    flow.hass = hass

    # Simulate user input
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_pass",
        "name": "Test Name",
    }

    with patch(
        "custom_components.greenchoice.config_flow.GreenchoiceConfigFlow.async_create_entry",
        return_value=config_entries.ConfigEntry(
            1, DOMAIN, "Test Name", user_input, "test_source", {}, None
        ),
    ) as mock_create_entry:

        result = await flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Name"
        assert result["data"] == user_input
        mock_create_entry.assert_called_once_with(title="Test Name", data=user_input)

@pytest.mark.asyncio
async def test_config_flow_user_invalid_auth(hass):
    """Test the user step with invalid authentication."""
    flow = GreenchoiceConfigFlow()
    flow.hass = hass

    # Simulate user input with invalid credentials
    user_input = {
        CONF_USERNAME: "",
        CONF_PASSWORD: "",
    }

    result = await flow.async_step_user(user_input)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert "errors" in result
    assert result["errors"]["base"] == "invalid_auth"

@pytest.mark.asyncio
async def test_config_flow_import(hass, mock_setup_entry):
    """Test the import step of the config flow."""
    flow = GreenchoiceConfigFlow()
    flow.hass = hass

    # Simulate YAML import
    yaml_input = {
        CONF_USERNAME: "yaml_user",
        CONF_PASSWORD: "yaml_pass",
    }

    with patch(
        "custom_components.greenchoice.config_flow.GreenchoiceConfigFlow.async_create_entry",
        return_value=config_entries.ConfigEntry(
            1, DOMAIN, "Greenchoice", yaml_input, "test_source", {}, None
        ),
    ) as mock_create_entry:

        result = await flow.async_step_import(yaml_input)

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"] == yaml_input
        mock_create_entry.assert_called_once_with(title=DEFAULT_NAME, data=yaml_input)
