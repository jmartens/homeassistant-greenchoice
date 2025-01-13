from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional("name", default=DEFAULT_NAME): str,
})


# Helper function for migrating YAML config
def migrate_yaml_to_config_flow(hass: HomeAssistant):
    yaml_config = hass.data.get(DOMAIN)
    if not yaml_config:
        _LOGGER.debug("No YAML configuration found to migrate.")
        return

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source == config_entries.SOURCE_IMPORT:
            _LOGGER.info("Updating existing config entry with YAML configuration.")
            hass.config_entries.async_update_entry(entry, data=yaml_config)
            break
    else:
        _LOGGER.info("Creating new config flow from YAML configuration.")
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=yaml_config
            )
        )

    hass.data.pop(DOMAIN, None)


class GreenchoiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Greenchoice."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)
            name = user_input.get("name", DEFAULT_NAME)

            _LOGGER.debug("User input received: username=%s, name=%s", username, name)

            # Validate input (replace this with actual validation logic)
            if not username or not password:
                _LOGGER.warning("Invalid authentication provided.")
                errors["base"] = "invalid_auth"
            else:
                _LOGGER.info("Creating config entry for username=%s, name=%s", username, name)
                # Save the config entry
                return self.async_create_entry(title=name, data=user_input)

        # Show the form
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(self, user_input: ConfigType):
        """Handle import of existing YAML configuration."""
        _LOGGER.info("Importing YAML configuration into config flow.")
        return await self.async_step_user(user_input)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up Greenchoice integration from YAML config."""
    _LOGGER.debug("Setting up Greenchoice integration from YAML config.")
    if DOMAIN in config:
        hass.data[DOMAIN] = config[DOMAIN]
        migrate_yaml_to_config_flow(hass)


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Set up Greenchoice from a config entry."""
    _LOGGER.info("Setting up Greenchoice integration from config entry.")
    hass.data[DOMAIN] = entry.data

    # Forward setup to the sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Unload a Greenchoice config entry."""
    _LOGGER.info("Unloading Greenchoice integration.")
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    # Forward unload to the sensor platform
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")
