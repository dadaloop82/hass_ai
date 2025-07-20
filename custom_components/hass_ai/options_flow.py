import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY

DOMAIN = "hass_ai"

class HassAiOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_API_KEY, default=self.config_entry.options.get(CONF_API_KEY, self.config_entry.data.get(CONF_API_KEY))): str
        })

        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)
