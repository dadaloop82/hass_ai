import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_API_KEY

from .const import DOMAIN, AI_PROVIDER_OPENAI, AI_PROVIDER_GEMINI, AI_PROVIDERS

class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hass AI config flow."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            # Here you could add API key validation against the selected provider
            # For now, we just store it.
            return self.async_create_entry(
                title=f"HASS AI ({user_input['ai_provider']})", data=user_input
            )

        # Schema for the user form
        data_schema = vol.Schema({
            vol.Required("ai_provider", default=AI_PROVIDER_OPENAI): vol.In(AI_PROVIDERS),
            vol.Required(CONF_API_KEY): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

@callback
def async_get_options_flow(config_entry):
    """Get the options flow for this handler."""
    return HassAiOptionsFlowHandler(config_entry)

class HassAiOptionsFlowHandler(config_entries.OptionsFlow):
    """Hass AI options flow."""

    def __init__(self, config_entry):
        """Initialize HASS AI options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        # This is where you would define the options form.
        # For now, we'll leave it empty as the next step is entity cataloging.
        # We will come back to this later.
        return self.async_create_entry(title="", data={})