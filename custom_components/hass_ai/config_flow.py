from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .const import DOMAIN, AI_PROVIDERS, AI_PROVIDER_LOCAL, CONF_AI_PROVIDER, CONF_CONVERSATION_AGENT, CONF_SCAN_INTERVAL

class HassAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hass AI config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the configuration flow."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            # Store data and move to agent selection
            self._ai_provider = user_input.get(CONF_AI_PROVIDER, AI_PROVIDER_LOCAL)
            self._scan_interval = user_input.get(CONF_SCAN_INTERVAL, 7)
            
            # Move to conversation agent selection
            return await self.async_step_agent()

        # Determine description based on language
        if self.hass.config.language == "it":
            description = (
                "⚠️ IMPORTANTE: Configura un agente LLM locale nel tuo Home Assistant\n\n"
                "L'Agente Locale richiede una LLM configurata (es. Ollama con Gemma/Llama, "
                "OpenAI, Google AI) per analizzare le entità. Il semplice 'Assist' di Home Assistant non è sufficiente.\n\n"
                "Nel prossimo step potrai scegliere quale agente conversazione usare."
            )
        else:
            description = (
                "⚠️ IMPORTANT: Configure a local LLM agent in your Home Assistant\n\n"
                "Local Agent requires a configured LLM (e.g., Ollama with Gemma/Llama, "
                "OpenAI, Google AI) to analyze entities. Home Assistant's simple 'Assist' is not sufficient.\n\n"
                "In the next step you can choose which conversation agent to use."
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_AI_PROVIDER, default=AI_PROVIDER_LOCAL): vol.In(AI_PROVIDERS),
                vol.Optional(CONF_SCAN_INTERVAL, default=7): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }),
            description_placeholders={
                "description": description
            },
        )

    async def async_step_agent(self, user_input=None):
        """Handle conversation agent selection."""
        if user_input is not None:
            # Create the entry with selected agent
            return self.async_create_entry(
                title="HASS AI", 
                data={
                    CONF_AI_PROVIDER: self._ai_provider,
                    CONF_SCAN_INTERVAL: self._scan_interval,
                    CONF_CONVERSATION_AGENT: user_input.get(CONF_CONVERSATION_AGENT)
                }
            )

        # Get available conversation agents
        conversation_agents = {}
        conversation_agents["auto"] = "Auto-detect (recommended)"
        
        for entity_id in self.hass.states.async_entity_ids("conversation"):
            state = self.hass.states.get(entity_id)
            if state:
                friendly_name = state.attributes.get("friendly_name", entity_id)
                conversation_agents[entity_id] = friendly_name

        # Determine description based on language
        if self.hass.config.language == "it":
            description = (
                f"🤖 Seleziona l'agente conversazione da usare per l'analisi AI\n\n"
                f"Agenti disponibili: {len(conversation_agents)}\n\n"
                f"💡 'Auto-detect' userà automaticamente il primo agente LLM trovato "
                f"(salta 'Home Assistant' di default)\n\n"
                f"⚠️ Assicurati che l'agente selezionato sia una vera LLM e non il semplice assistente di HA"
            )
        else:
            description = (
                f"🤖 Select the conversation agent to use for AI analysis\n\n"
                f"Available agents: {len(conversation_agents)}\n\n"
                f"💡 'Auto-detect' will automatically use the first LLM agent found "
                f"(skips default 'Home Assistant')\n\n"
                f"⚠️ Make sure the selected agent is a real LLM and not HA's simple assistant"
            )

        return self.async_show_form(
            step_id="agent",
            data_schema=vol.Schema({
                vol.Required(CONF_CONVERSATION_AGENT, default="auto"): vol.In(conversation_agents),
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
