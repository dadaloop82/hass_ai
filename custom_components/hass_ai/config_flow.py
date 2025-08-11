from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .const import DOMAIN, AI_PROVIDERS, AI_PROVIDER_OPENAI, AI_PROVIDER_GEMINI

class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hass AI config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the configuration flow."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            # Store the provider and move to API key step
            self._ai_provider = user_input.get("ai_provider", AI_PROVIDER_OPENAI)
            self._scan_interval = user_input.get("scan_interval", 7)
            return await self.async_step_api_key()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("ai_provider", default=AI_PROVIDER_OPENAI): vol.In(AI_PROVIDERS),
                vol.Optional("scan_interval", default=7): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }),
        )

    async def async_step_api_key(self, user_input=None):
        """Handle API key configuration for external AI providers."""
        errors = {}
        
        if user_input is not None:
            api_key = user_input.get("api_key", "").strip()
            
            if not api_key:
                errors["api_key"] = "required"
            else:
                # Create the entry with API key
                return self.async_create_entry(
                    title="HASS AI", 
                    data={
                        "ai_provider": self._ai_provider,
                        "api_key": api_key,
                        "scan_interval": self._scan_interval
                    }
                )

        # Determine description based on provider
        if self._ai_provider == AI_PROVIDER_OPENAI:
            description = "Enter your OpenAI API key. You can get it from https://platform.openai.com/api-keys"
        elif self._ai_provider == AI_PROVIDER_GEMINI:
            description = "Enter your Google AI Studio API key. You can get it from https://aistudio.google.com/app/apikey"
        else:
            description = "Enter your API key for the selected AI provider."

        return self.async_show_form(
            step_id="api_key",
            data_schema=vol.Schema({
                vol.Required("api_key"): str,
            }),
            description_placeholders={
                "provider": self._ai_provider,
                "description": description
            },
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return HassAiOptionsFlowHandler(config_entry)


class HassAiOptionsFlowHandler(config_entries.OptionsFlow):
    """Hass AI options flow handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            ai_provider = user_input.get("ai_provider", AI_PROVIDER_OPENAI)
            
            # Check if same provider without API key change
            if (ai_provider == self.config_entry.data.get("ai_provider") and 
                user_input.get("change_api_key") is not True):
                return self.async_create_entry(title="", data=user_input)
            else:
                # Store the provider and move to API key step
                self._new_options = user_input
                self._ai_provider = ai_provider
                return await self.async_step_api_key()

        scan_interval = self.config_entry.options.get("scan_interval", 7)
        ai_provider = self.config_entry.data.get("ai_provider", AI_PROVIDER_OPENAI)
        
        schema = {
            vol.Required("scan_interval", default=scan_interval): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            vol.Required("ai_provider", default=ai_provider): vol.In(AI_PROVIDERS),
            vol.Optional("change_api_key", default=False): bool,
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )

    async def async_step_api_key(self, user_input=None):
        """Handle API key configuration for external AI providers."""
        errors = {}
        
        if user_input is not None:
            api_key = user_input.get("api_key", "").strip()
            
            if not api_key:
                errors["api_key"] = "required"
            else:
                # Update config entry data with new API key
                new_data = {**self.config_entry.data}
                new_data["ai_provider"] = self._ai_provider
                new_data["api_key"] = api_key
                
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
                
                return self.async_create_entry(title="", data=self._new_options)

        # Determine description based on provider
        if self._ai_provider == AI_PROVIDER_OPENAI:
            description = "Enter your OpenAI API key. You can get it from https://platform.openai.com/api-keys"
        elif self._ai_provider == AI_PROVIDER_GEMINI:
            description = "Enter your Google AI Studio API key. You can get it from https://aistudio.google.com/app/apikey"
        else:
            description = "Enter your API key for the selected AI provider."

        return self.async_show_form(
            step_id="api_key",
            data_schema=vol.Schema({
                vol.Required("api_key"): str,
            }),
            description_placeholders={
                "provider": self._ai_provider,
                "description": description
            },
            errors=errors,
        )
