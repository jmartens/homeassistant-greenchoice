from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .api import GreenchoiceApi

_LOGGER = logging.getLogger(__name__)

# Helper function for migrating YAML config
def migrate_yaml_to_config_flow(hass: HomeAssistant):
    yaml_config = hass.data.get(DOMAIN)
    if not yaml_config:
        _LOGGER.debug("No YAML configuration found to migrate.")
        return

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source == SOURCE_IMPORT:
            _LOGGER.info("Updating existing config entry with YAML configuration.")
            hass.config_entries.async_update_entry(entry, data=yaml_config)
            break
    else:
        _LOGGER.info("Creating new config flow from YAML configuration.")
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=yaml_config
            )
        )

    hass.data.pop(DOMAIN, None)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Greenchoice integration from YAML config."""
    _LOGGER.debug("Setting up Greenchoice integration from YAML config.")
    if DOMAIN in config:
        hass.data[DOMAIN] = config[DOMAIN]
        _LOGGER.debug("Loaded Greenchoice configuration from YAML: %s", hass.data[DOMAIN])
        migrate_yaml_to_config_flow(hass)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Greenchoice integration from a config entry."""
    _LOGGER.info("Setting up Greenchoice integration from config entry.")
    hass.data.setdefault(DOMAIN, {})

    # Initialize API
    _LOGGER.debug("Greenchoice entry data: %s", entry.data)
    api = GreenchoiceApi(entry.data["username"], entry.data["password"])

    try:
        await api.async_update()
    except Exception as ex:
        _LOGGER.error("Failed to connect to Greenchoice API: %s", ex)
        raise ConfigEntryNotReady from ex

    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Greenchoice config entry."""
    _LOGGER.info("Unloading Greenchoice integration.")
    hass.data[DOMAIN].pop(entry.entry_id)
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Update Greenchoice integration options."""
    _LOGGER.info("Updating Greenchoice integration options.")
    await async_setup_entry(hass, entry)
    return True