import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import package

from .const import DOMAIN, AI_PROVIDER_OPENAI, AI_PROVIDER_GEMINI, AI_PROVIDERS
from .options_flow import HassAiOptionsFlowHandler

class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hass AI config flow."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return HassAiOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            if user_input["ai_provider"] == AI_PROVIDER_GEMINI:
                if not await package.async_install_package(self.hass, "google-generativeai"):
                    errors["base"] = "install_failed"
                    return self.async_show_form(
                        step_id="user", data_schema=self._get_schema(), errors=errors
                    )

            return self.async_create_entry(
                title=f"HASS AI ({user_input['ai_provider']})", data=user_input
            )

        return self.async_show_form(
            step_id="user", data_schema=self._get_schema(), errors=errors
        )

    def _get_schema(self):
        return vol.Schema({
            vol.Required("ai_provider", default=AI_PROVIDER_OPENAI): vol.In(AI_PROVIDERS),
            vol.Required(CONF_API_KEY): str,
        })
