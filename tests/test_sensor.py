import pytest
from unittest.mock import AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from custom_components.greenchoice.const import DOMAIN, DEFAULT_NAME
from custom_components.greenchoice.sensor import async_setup_entry


@pytest.fixture
def mock_greenchoice_api():
    """Mock the Greenchoice API."""
    api = AsyncMock()
    api.async_update = AsyncMock(return_value={
        "electricity_consumption_high": 100,
        "electricity_consumption_low": 50,
        "measurement_date_electricity": "2025-01-01",
    })
    return api


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        domain=DOMAIN,
        title=DEFAULT_NAME,
        data={
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_pass",
        },
        source="user",
        entry_id="test",
    )


async def test_async_setup_entry(hass: HomeAssistant, mock_greenchoice_api, mock_config_entry):
    """Test setting up the Greenchoice sensor integration."""
    with patch(
        "custom_components.greenchoice.sensor.GreenchoiceApi", return_value=mock_greenchoice_api
    ), patch(
        "custom_components.greenchoice.sensor.GreenchoiceCoordinator.async_config_entry_first_refresh",
        return_value=None,
    ) as mock_refresh:
        # Call async_setup_entry
        result = await async_setup_entry(hass, mock_config_entry, AsyncMock())

        # Verify setup completed successfully
        assert result is True
        mock_refresh.assert_called_once()


async def test_sensor_values(hass: HomeAssistant, mock_greenchoice_api, mock_config_entry):
    """Test the sensor entity values."""
    with patch(
        "custom_components.greenchoice.sensor.GreenchoiceApi", return_value=mock_greenchoice_api
    ), patch(
        "custom_components.greenchoice.sensor.GreenchoiceCoordinator.async_config_entry_first_refresh",
        return_value=None,
    ):
        async_add_entities = AsyncMock()
        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Verify sensor entities were added
        assert async_add_entities.call_count == 1
        sensors = async_add_entities.call_args[0][0]

        # Verify sensor attributes
        for sensor in sensors:
            if sensor._measurement_type == "electricity_consumption_high":
                assert sensor.native_value == 100
                assert sensor.extra_state_attributes["measurement_date"] == "2025-01-01"


async def test_update_failure(hass: HomeAssistant, mock_greenchoice_api, mock_config_entry):
    """Test handling an update failure in the coordinator."""
    mock_greenchoice_api.async_update.side_effect = Exception("API error")

    with patch(
        "custom_components.greenchoice.sensor.GreenchoiceApi", return_value=mock_greenchoice_api
    ), patch(
        "custom_components.greenchoice.sensor.GreenchoiceCoordinator.async_config_entry_first_refresh",
        side_effect=UpdateFailed("Failed to fetch data"),
    ):
        async_add_entities = AsyncMock()
        with pytest.raises(UpdateFailed):
            await async_setup_entry(hass, mock_config_entry, async_add_entities)
