from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.greenchoice import async_setup, async_setup_entry, async_unload_entry, DOMAIN


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return config_entries.ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Greenchoice",
        data={"username": "test_user", "password": "test_pass"},
        source=config_entries.SOURCE_USER,
        connection_class=config_entries.CONN_CLASS_CLOUD_POLL,
        system_options={"disable_new_entities": False},
        options={},
        entry_id="test",
    )


@pytest.fixture
def hass():
    """Provide a Home Assistant instance."""
    return AsyncMock(spec=HomeAssistant)


async def test_async_setup(hass):
    """Test async setup with YAML configuration."""
    with patch("custom_components.greenchoice.migrate_yaml_to_config_flow") as mock_migrate:
        config = {DOMAIN: {"username": "yaml_user", "password": "yaml_pass"}}
        assert await async_setup(hass, config) is True
        mock_migrate.assert_called_once_with(hass)


async def test_async_setup_entry(hass, mock_config_entry):
    """Test async setup entry."""
    assert await async_setup_entry(hass, mock_config_entry) is True


async def test_async_unload_entry(hass, mock_config_entry):
    """Test async unload entry."""
    hass.data[DOMAIN] = {mock_config_entry.entry_id: True}
    assert await async_unload_entry(hass, mock_config_entry) is True
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
