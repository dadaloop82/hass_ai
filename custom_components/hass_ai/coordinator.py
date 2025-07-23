from __future__ import annotations

import logging
import json

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, AI_PROVIDER_OPENAI, AI_PROVIDER_GEMINI

# Conditional imports for AI providers
try:
    import openai
except ImportError:
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

_LOGGER = logging.getLogger(__name__)

class HassAiCoordinator(DataUpdateCoordinator):
    """HASS AI Coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self.config_entry = entry
        self.client = None

        if self.ai_provider == AI_PROVIDER_OPENAI and openai is not None:
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        elif self.ai_provider == AI_PROVIDER_GEMINI and genai is not None:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel('gemini-pro')

    @property
    def api_key(self) -> str | None:
        """Return the API key."""
        return self.config_entry.data.get("api_key")

    @property
    def ai_provider(self) -> str | None:
        """Return the AI provider."""
        return self.config_entry.data.get("ai_provider")

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        return {"status": "idle"}

    async def start_analysis(self, entities: list[str]):
        """Start the AI analysis of the selected entities."""
        if not self.client:
            _LOGGER.error("AI provider client is not initialized.")
            return

        _LOGGER.info(f"Starting analysis for {len(entities)} entities with {self.ai_provider}.")

        entity_states = [self.hass.states.get(entity_id) for entity_id in entities]
        prompt_data = []
        for state in entity_states:
            if state:
                prompt_data.append({
                    "entity_id": state.entity_id,
                    "state": state.state,
                    "attributes": dict(state.attributes)
                })

        prompt = self._build_prompt(prompt_data)

        try:
            if self.ai_provider == AI_PROVIDER_OPENAI:
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a home automation expert."},
                        {"role": "user", "content": prompt}
                    ]
                )
                result = response.choices[0].message.content
            elif self.ai_provider == AI_PROVIDER_GEMINI:
                response = await self.client.generate_content_async(prompt)
                result = response.text
            
            _LOGGER.info(f"AI Response: {result}")
            # Here we would parse the response and store it.

        except Exception as e:
            _LOGGER.error(f"Error calling AI provider: {e}")

    def _build_prompt(self, entities_data: list[dict]) -> str:
        """Build the prompt for the AI."""
        return (
            "As an expert in home automation, your task is to analyze the following list of Home Assistant entities "
            "and their attributes. Your goal is to identify which entities and which of their specific attributes are "
            "most important for creating smart home automations. \n\n"
            "For each entity, provide a JSON object with the entity_id and a list of its most relevant attributes. "
            "Exclude entities that are not useful for automation (e.g., diagnostic sensors, sun position, etc.).\n\n"
            "Example response format:\n"
            "{\n"
            '  "important_entities": [\n'
            '    {\n'
            '      "entity_id": "light.living_room_lights",\n'
            '      "important_attributes": ["state", "brightness", "color_temp"]\n'
            '    },\n'
            '    {\n'
            '      "entity_id": "climate.thermostat",\n'
            '      "important_attributes": ["state", "current_temperature", "target_temperature", "hvac_action"]\n'
            '    }\n'
            '  ]\n'
            "}\n\n"
            f"Here is the list of entities:\n{json.dumps(entities_data, indent=2)}"
        )