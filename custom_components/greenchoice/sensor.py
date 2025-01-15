import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    CONF_NAME,
    CURRENCY_EURO,
    UnitOfEnergy,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify, Throttle

from .api import GreenchoiceApi

_LOGGER = logging.getLogger(__name__)

CONF_USERNAME = "username"
CONF_PASSWORD = "password"  # nosec:B105

DEFAULT_NAME = "Energieverbruik"
DEFAULT_DATE_FORMAT = "%y-%m-%dT%H:%M:%S"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3600)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


class Unit:
    KWH = UnitOfEnergy.KILO_WATT_HOUR
    EUR_KWH = f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}"
    M3 = UnitOfVolume.CUBIC_METERS
    EUR_M3 = f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}"


# Define sensor information
sensor_infos = {
    "electricity_consumption_low": {
        "unit": Unit.KWH,
        "icon": "mdi:flash"
    },
    "electricity_consumption_high": {
        "unit": Unit.KWH,
        "icon": "mdi:flash"
    },
    "electricity_consumption_total": {
        "unit": Unit.KWH,
        "icon": "mdi:flash"
    },
    "electricity_return_low": {
        "unit": Unit.KWH,
        "icon": "mdi:flash"
    },
    "electricity_return_high": {
        "unit": Unit.KWH,
        "icon": "mdi:flash"
    },
    "electricity_return_total": {
        "unit": Unit.KWH,
        "icon": "mdi:flash"
    },
    "gas_consumption": {
        "unit": Unit.M3,
        "icon": "mdi:fire"
    },
    "measurement_date_electricity": {
        "unit": None,
        "icon": "mdi:calendar"
    },
    "measurement_date_gas": {
        "unit": None,
        "icon": "mdi:calendar"
    },
}


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    name = config.get(CONF_NAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    _LOGGER.debug("Set up platform")
    try:
        greenchoice_api = GreenchoiceApi(username, password)
        await throttled_api_update(greenchoice_api)

        sensors = [
            GreenchoiceSensor(
                greenchoice_api,
                name,
                sensor_name,
            )
            for sensor_name in sensor_infos
        ]

        async_add_entities(sensors, True)
    except Exception as ex:
        _LOGGER.error("Failed to set up Greenchoice sensor platform: %s", ex)
        raise ConfigEntryNotReady from ex


@Throttle(MIN_TIME_BETWEEN_UPDATES)
async def throttled_api_update(api):
    _LOGGER.debug("Throttled update called.")
    api_result = await api.async_update()
    _LOGGER.debug("Api result: %s", api_result)
    return api_result


class GreenchoiceSensor(SensorEntity):
    def __init__(
        self,
        greenchoice_api,
        name,
        measurement_type,
    ):
        self._api = greenchoice_api
        self._measurement_type = measurement_type
        self._measurement_date = None
        self._name = f"{name} {measurement_type}"
        self._state = None
        self._unit_of_measurement = sensor_infos[measurement_type]["unit"]
        self._icon = sensor_infos[measurement_type]["icon"]

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def icon(self):
        return self._icon

    async def async_update(self):
        _LOGGER.debug("Update called")
        await self._api.async_update()
        self._state = self._api.result.get(self._measurement_type)
        self._measurement_date = self._api.result.get(
            f"measurement_date_{self._measurement_type}"
        )