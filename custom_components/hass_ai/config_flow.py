from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .const import DOMAIN, AI_PROVIDERS, AI_PROVIDER_LOCAL

class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hass AI config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the configuration flow."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            # Store the provider and scan interval
            ai_provider = user_input.get("ai_provider", AI_PROVIDER_LOCAL)
            scan_interval = user_input.get("scan_interval", 7)
            
            # Only Local Agent is supported
            return self.async_create_entry(
                title="HASS AI", 
                data={
                    "ai_provider": ai_provider,
                    "scan_interval": scan_interval
                }
            )

        # Determine description based on language
        if self.hass.config.language == "it":
            description = (
                "⚠️ IMPORTANTE: Configura un agente LLM locale nel tuo Home Assistant\n\n"
                "L'Agente Locale richiede una LLM configurata (es. Ollama con Gemma/Llama) "
                "per analizzare le entità. Il semplice 'Assist' di Home Assistant non è sufficiente.\n\n"
                "Per configurare Ollama: vai in Impostazioni > Dispositivi e servizi > "
                "Aggiungi integrazione > Ollama, poi configura un agente conversazione."
            )
        else:
            description = (
                "⚠️ IMPORTANT: Configure a local LLM agent in your Home Assistant\n\n"
                "Local Agent requires a configured LLM (e.g., Ollama with Gemma/Llama) "
                "to analyze entities. Home Assistant's simple 'Assist' is not sufficient.\n\n"
                "To configure Ollama: go to Settings > Devices & Services > "
                "Add Integration > Ollama, then configure a conversation agent."
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("ai_provider", default=AI_PROVIDER_LOCAL): vol.In(AI_PROVIDERS),
                vol.Optional("scan_interval", default=7): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }),
            description_placeholders={
                "description": description
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return HassAiOptionsFlowHandler(config_entry)


class HassAiOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for HASS AI."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        ai_provider = self.config_entry.data.get("ai_provider", AI_PROVIDER_LOCAL)
        scan_interval = self.config_entry.options.get("scan_interval", 
                                                     self.config_entry.data.get("scan_interval", 7))

        # Determine description based on language
        if self.hass.config.language == "it":
            description = (
                "⚠️ IMPORTANTE: L'Agente Locale richiede una LLM configurata\n\n"
                "Assicurati di avere configurato Ollama o un'altra LLM nel tuo "
                "Home Assistant per il corretto funzionamento dell'analisi AI."
            )
        else:
            description = (
                "⚠️ IMPORTANT: Local Agent requires a configured LLM\n\n"
                "Make sure you have Ollama or another LLM configured in your "
                "Home Assistant for proper AI analysis functionality."
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("ai_provider", default=ai_provider): vol.In(AI_PROVIDERS),
                vol.Optional("scan_interval", default=scan_interval): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }),
            description_placeholders={
                "description": description
            },
        )
