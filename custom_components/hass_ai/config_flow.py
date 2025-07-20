import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_API_KEY

DOMAIN = "hass_ai"

class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Qui potresti aggiungere una verifica dell'API key (opzionale)
            return self.async_create_entry(title="HASS AI", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_API_KEY): str
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

@callback
def async_get_options_flow(config_entry):
    return HassAiOptionsFlowHandler(config_entry)
