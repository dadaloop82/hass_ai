from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN


class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hass AI config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        data_schema = vol.Schema({
            vol.Required("scan_interval", default=7): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        })

        if user_input is not None:
            return self.async_create_entry(title="HASS AI", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            description_placeholders={
                "description_start": "config::step::user::description_start",
                "description_end": "config::step::user::description_end",
            }
        )