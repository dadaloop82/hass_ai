import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_API_KEY

from .const import DOMAIN, AI_PROVIDER_OPENAI, AI_PROVIDERS

class HassAiOptionsFlowHandler(config_entries.OptionsFlow):
    """Hass AI options flow."""

    def __init__(self, config_entry):
        """Initialize HASS AI options flow."""
        self.config_entry = config_entry
        self.data = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["screening", "reconfigure"],
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle a flow to reconfigure."""
        errors = {}

        if user_input is not None:
            # This will update the main config entry
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input
            )
            return self.async_create_entry(title="", data={})

        # Get current data from the config entry
        current_provider = self.config_entry.data.get("ai_provider", AI_PROVIDER_OPENAI)
        current_api_key = self.config_entry.data.get(CONF_API_KEY, "")

        data_schema = vol.Schema({
            vol.Required("ai_provider", default=current_provider): vol.In(AI_PROVIDERS),
            vol.Required(CONF_API_KEY, default=current_api_key): str,
        })

        return self.async_show_form(
            step_id="reconfigure", data_schema=data_schema, errors=errors
        )

    async def async_step_screening(self, user_input=None):
        """Handle the entity screening flow."""
        if user_input is not None:
            # Store the selected entities in the options
            selected_entities = [key for key, value in user_input.items() if value]
            
            # Get the coordinator
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]

            # Start the analysis
            self.hass.async_create_task(
                coordinator.start_analysis(selected_entities)
            )

            # Update the options for this config entry
            return self.async_create_entry(title="", data={"selected_entities": selected_entities})

        # Get all entities from Home Assistant
        all_entities = self.hass.states.async_all()
        
        # Create a schema with a checkbox for each entity
        data_schema_fields = {
            vol.Required(entity.entity_id, default=False): bool
            for entity in all_entities
        }
        
        return self.async_show_form(
            step_id="screening",
            data_schema=vol.Schema(data_schema_fields),
            description_placeholders={
                "entities_count": len(all_entities)
            }
        )
