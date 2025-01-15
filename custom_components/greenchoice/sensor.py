import logging
from collections import namedtuple
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME, CURRENCY_EURO, UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import GreenchoiceApi
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

# Constants
SCAN_INTERVAL = timedelta(hours=1)


class Unit:
    """Unit constants for sensor measurements."""
    KWH = UnitOfEnergy.KILO_WATT_HOUR
    EUR_KWH = f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}"
    M3 = UnitOfVolume.CUBIC_METERS
    EUR_M3 = f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}"


SensorInfo = namedtuple("SensorInfo", ["device_class", "unit", "icon"])
sensor_infos = {
    "electricity_consumption_high": SensorInfo(
        SensorDeviceClass.ENERGY, Unit.KWH, "weather-sunset-up"
    ),
    "electricity_consumption_low": SensorInfo(
        SensorDeviceClass.ENERGY, Unit.KWH, "weather-sunset-down"
    ),
    "electricity_consumption_total": SensorInfo(
        SensorDeviceClass.ENERGY, Unit.KWH, "transmission-tower-export"
    ),
    "electricity_return_high": SensorInfo(
        SensorDeviceClass.ENERGY, Unit.KWH, "solar-power"
    ),
    "electricity_return_low": SensorInfo(
        SensorDeviceClass.ENERGY, Unit.KWH, "solar-power"
    ),
    "electricity_return_total": SensorInfo(
        SensorDeviceClass.ENERGY, Unit.KWH, "transmission-tower-import"
    ),
    "electricity_price_low": SensorInfo(
        SensorDeviceClass.MONETARY, Unit.EUR_KWH, "currency-eur"
    ),
    "electricity_price_high": SensorInfo(
        SensorDeviceClass.MONETARY, Unit.EUR_KWH, "currency-eur"
    ),
    "electricity_price_single": SensorInfo(
        SensorDeviceClass.MONETARY, Unit.EUR_KWH, "currency-eur"
    ),
    "electricity_return_price": SensorInfo(
        SensorDeviceClass.MONETARY, Unit.EUR_KWH, "currency-eur"
    ),
    "electricity_return_cost": SensorInfo(
        SensorDeviceClass.MONETARY, Unit.EUR_KWH, "currency-eur"
    ),
    "gas_consumption": SensorInfo(SensorDeviceClass.GAS, Unit.M3, "fire"),
    "gas_price": SensorInfo(SensorDeviceClass.MONETARY, Unit.EUR_M3, "currency-eur"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Greenchoice sensors from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)

    _LOGGER.debug("Setting up Greenchoice sensors")
    api = GreenchoiceApi(username, password)

    # Coordinator for managing updates
    coordinator = GreenchoiceCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    # Create sensor entities
    sensors = [
        GreenchoiceSensor(coordinator, name, sensor_name)
        for sensor_name in sensor_infos
    ]
    async_add_entities(sensors, update_before_add=False)


class GreenchoiceCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Greenchoice data from API."""

    def __init__(self, hass: HomeAssistant, api: GreenchoiceApi) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Greenchoice",
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch data from API."""
        _LOGGER.debug("Fetching data from Greenchoice API")
        return await self.api.async_update()


class GreenchoiceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Greenchoice sensor."""

    def __init__(self, coordinator, name, measurement_type):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._measurement_type = measurement_type
        self._measurement_date_key = (
            "measurement_date_electricity"
            if "electricity" in self._measurement_type
            else "measurement_date_gas"
        )

        sensor_info = sensor_infos[self._measurement_type]

        self._attr_unique_id = f"{name}_{measurement_type}"
        self._attr_name = f"{name} {measurement_type.replace('_', ' ').title()}"
        self._attr_icon = f"mdi:{sensor_info.icon}"
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_device_class = sensor_info.device_class
        self._attr_native_unit_of_measurement = sensor_info.unit

    @property
    def native_value(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or {}
        return data.get(self._measurement_type)

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        data = self.coordinator.data or {}
        return {"measurement_date": data.get(self._measurement_date_key)}