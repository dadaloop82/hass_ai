from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN


class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hass AI config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the configuration flow."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        # This step is just an introduction
        if user_input is not None:
            return await self.async_step_configure()

        return self.async_show_form(
            step_id="user",
        )

    async def async_step_configure(self, user_input=None):
        """Handle the configuration step."""
        data_schema = vol.Schema({
            vol.Required(
                "scan_interval",
                default=7,
                selector={"number": {"min": 1, "max": 30, "unit_of_measurement": "days"}}
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        })

        if user_input is not None:
            return self.async_create_entry(title="HASS AI", data=user_input)

        return self.async_show_form(
            step_id="configure",
            data_schema=data_schema,
        )