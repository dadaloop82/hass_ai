from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .const import DOMAIN

class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hass AI config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the configuration flow."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            return self.async_create_entry(title="HASS AI", data={})

        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return HassAiOptionsFlowHandler(config_entry)


class HassAiOptionsFlowHandler(config_entries.OptionsFlow):
    """Hass AI options flow handler."""

    

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        scan_interval = self.config_entry.options.get("scan_interval", 7)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("scan_interval", default=scan_interval): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }),
        )
