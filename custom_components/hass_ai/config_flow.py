from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hass AI config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        # Check if an entry already exists
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            return self.async_create_entry(title="HASS AI", data={})

        return self.async_show_form(step_id="user")