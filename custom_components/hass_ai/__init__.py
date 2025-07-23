"""The HASS AI integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, State
from homeassistant.helpers import entity_registry as er, storage

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = []
STORAGE_VERSION = 1
INTELLIGENCE_STORAGE_KEY = f"{DOMAIN}_intelligence"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HASS AI from a config entry."""
    # Ensure the domain data dict exists
    hass.data.setdefault(DOMAIN, {})
    
    intelligence_store = storage.Store(hass, STORAGE_VERSION, INTELLIGENCE_STORAGE_KEY)
    hass.data[DOMAIN][entry.entry_id] = {
        "intelligence_store": intelligence_store
    }

    # Start initial analysis in the background
    hass.async_create_task(_analyze_and_store_entities(hass, intelligence_store))

    async def handle_prompt(call: ServiceCall) -> None:
        """Handle the intelligent prompt service call."""
        user_prompt = call.data.get("text", "")
        if not user_prompt:
            _LOGGER.warning("Prompt service called with no text.")
            return

        intelligence_data = await intelligence_store.async_load() or {}
        important_entities = {
            entity_id: data
            for entity_id, data in intelligence_data.items()
            if data.get("weight", 1) >= 3
        }

        context_prompt = (
            f"Based on the following entities and their importance, please process the request. "
            f"Entities list (most important first): {important_entities}. "
            f"User request: {user_prompt}"
        )

        _LOGGER.debug(f"Sending to conversation agent: {context_prompt}")

        await hass.services.async_call(
            "conversation", "process", {"text": context_prompt}, blocking=True
        )
    
    async def handle_analyze(call: ServiceCall) -> None:
        """Service handler to (re)-analyze all entities."""
        await _analyze_and_store_entities(hass, intelligence_store)

    hass.services.async_register(DOMAIN, "prompt", handle_prompt)
    hass.services.async_register(DOMAIN, "analyze_entities", handle_analyze)

    return True


"""The HASS AI integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Define the platforms that this integration will support
PLATFORMS: list[str] = ["number", "switch"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HASS AI from a config entry."""
    # Store the config entry so it can be accessed by the platforms
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry

    # Forward the setup to the number and switch platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload the platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok



def _get_entity_importance(state: State) -> dict:
    """Calculate the importance of an entity based on its properties."""
    domain = state.domain
    attributes = state.attributes
    entity_id = state.entity_id
    weight = 1
    reasons = []

    domain_weights = {
        "alarm_control_panel": 5, "lock": 5, "climate": 4, "light": 3,
        "switch": 3, "binary_sensor": 3, "sensor": 2, "media_player": 2
    }
    weight = domain_weights.get(domain, 1)
    if weight > 1: reasons.append(f"Domain '{domain}'")

    device_class = attributes.get("device_class")
    if device_class:
        device_class_weights = {
            "motion": 2, "door": 2, "window": 2, "smoke": 2, "safety": 2, "lock": 2,
            "power": 1, "temperature": 1, "humidity": 1, "energy": 1
        }
        bonus = device_class_weights.get(device_class, 0)
        if bonus > 0:
            weight += bonus
            reasons.append(f"Class '{device_class}'")

    name = attributes.get("friendly_name", "").lower()
    entity_id_lower = entity_id.lower()
    keywords = {
        "main": 2, "master": 2, "living": 1, "kitchen": 1, "front_door": 2, "alarm": 2
    }
    for key, bonus in keywords.items():
        if key in name or key in entity_id_lower:
            weight += bonus
            reasons.append(f"Keyword '{key}'")

    weight = max(1, min(5, weight))
    return {"weight": weight, "reason": ", ".join(reasons) or "Default"}


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, "prompt")
    hass.services.async_remove(DOMAIN, "analyze_entities")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
