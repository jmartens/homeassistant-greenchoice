import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import ConfigEntry  # Import ConfigEntry

from .const import DOMAIN
from .api import GreenchoiceApi

_LOGGER = logging.getLogger(__name__)

class GreenchoiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Greenchoice."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Attempt to connect to Greenchoice API
                api = GreenchoiceApi(user_input["username"], user_input["password"])
                await api.async_update()
                return self.async_create_entry(title="Greenchoice", data=user_input)
            except Exception as ex:
                _LOGGER.error("Failed to connect to Greenchoice API: %s", ex)
                errors["base"] = "auth"

        data_schema = vol.Schema({
            vol.Required("username"): str,
            vol.Required("password"): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_import(self, user_input=None) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)

    async def async_step_reauth(self, user_input=None) -> FlowResult:
        """Handle reauthentication."""
        return await self.async_step_user(user_input)

class GreenchoiceOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Greenchoice options."""

    def __init__(self, config_entry: ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the Greenchoice options."""
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input=None) -> FlowResult:
        """Handle options."""
        errors = {}

        if user_input is not None:
            try:
                _LOGGER.debug(f"Updating config entry with data: {user_input}")
                # Attempt to connect to Greenchoice API
                api = GreenchoiceApi(user_input["username"], user_input["password"])
                await api.async_update()
                self.hass.config_entries.async_update_entry(self.config_entry, data=user_input)
                _LOGGER.debug(f"Config entry updated successfully: {self.config_entry.data}")
                return self.async_create_entry(title="", data={})
            except Exception as ex:
                _LOGGER.error("Failed to connect to Greenchoice API: %s", ex)
                errors["base"] = "auth"

        data_schema = vol.Schema({
            vol.Required("username", default=self.config_entry.data.get("username", "")): str,
            vol.Required("password", default=self.config_entry.data.get("password", "")): str,
        })

        return self.async_show_form(step_id="options", data_schema=data_schema, errors=errors)

    @staticmethod
    async def async_supports_options_flow(config_entry: ConfigEntry) -> bool:
        """Return whether the options flow is supported."""
        return True