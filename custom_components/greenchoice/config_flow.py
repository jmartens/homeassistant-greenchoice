from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional("name", default=DEFAULT_NAME): str,
    }
)

class GreenchoiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Greenchoice."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
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
                _LOGGER.info(
                    "Creating config entry for username=%s, name=%s", username, name
                )
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