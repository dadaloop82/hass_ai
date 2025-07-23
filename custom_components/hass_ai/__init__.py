"""The HASS AI integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .coordinator import HassAiCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = []
STORAGE_VERSION = 1
INTELLIGENCE_STORAGE_KEY = f"{DOMAIN}_intelligence"


def _get_entity_importance(state: State) -> dict:
    """Calculate the importance of an entity based on its properties."""
    domain = state.domain
    attributes = state.attributes
    entity_id = state.entity_id

    weight = 1
    reasons = []

    # Base weight by domain
    domain_weights = {
        "alarm_control_panel": 5, "lock": 5, "climate": 4, "light": 3,
        "switch": 3, "binary_sensor": 3, "sensor": 2, "media_player": 2,
        "camera": 3, "vacuum": 3, "cover": 3
    }
    weight = domain_weights.get(domain, 1)
    if weight > 1:
        reasons.append(f"Domain '{domain}' has a base weight of {weight}.")

    # Analysis by device_class
    device_class = attributes.get("device_class")
    if device_class:
        device_class_weights = {
            "motion": 2, "door": 2, "window": 2, "smoke": 2, "gas": 2,
            "safety": 2, "lock": 2, "garage_door": 1, "power": 1,
            "temperature": 1, "humidity": 1, "pressure": 1, "energy": 1,
            "carbon_monoxide": 2, "carbon_dioxide": 1, "water": 2
        }
        bonus = device_class_weights.get(device_class, 0)
        if bonus > 0:
            weight += bonus
            reasons.append(f"Device class '{device_class}' adds a weight of {bonus}.")

    # Analysis by unit of measurement
    unit = attributes.get("unit_of_measurement")
    if unit:
        unit_weights = {
            "W": 1, "kW": 1, "kWh": 1, "lx": 1, "°C": 1, "°F": 1, "%": 0
        }
        bonus = unit_weights.get(unit, 0)
        if bonus > 0:
            weight += bonus
            reasons.append(f"Unit '{unit}' adds a weight of {bonus}.")

    # Keyword analysis in entity_id and friendly_name
    name = attributes.get("friendly_name", "").lower()
    entity_id_lower = entity_id.lower()
    keywords = {
        "main": 2, "master": 2, "living": 1, "kitchen": 1, "bedroom": 1,
        "front_door": 2, "alarm": 2, "allarme": 2, "ingresso": 2,
        "test": -2, "debug": -2, "example": -2
    }
    for key, bonus in keywords.items():
        if key in name or key in entity_id_lower:
            weight += bonus
            reasons.append(f"Keyword '{key}' changes weight by {bonus}.")

    # Final weight clamping
    weight = max(1, min(5, weight))
    
    if not reasons:
        reasons.append("Default weight assigned. No specific criteria matched.")

    return {"weight": weight, "reason": " ".join(reasons)}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HASS AI from a config entry."""
    coordinator = HassAiCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    store = Store(hass, STORAGE_VERSION, INTELLIGENCE_STORAGE_KEY)

    async def _analyze_entities_service(call: ServiceCall) -> None:
        """Service handler to analyze all entities."""
        _LOGGER.info("Starting entity analysis...")
        entity_registry = er.async_get(hass)
        intelligence_data = {}

        for entity_id, state in hass.states.async_all(include_hidden=False):
            entity_entry = entity_registry.async_get(entity_id)
            if entity_entry and entity_entry.disabled_by:
                continue  # Skip disabled entities

            importance = _get_entity_importance(state)
            intelligence_data[entity_id] = importance
            _LOGGER.debug(f"Analyzed {entity_id}: Weight {importance['weight']}, Reason: {importance['reason']}")
        
        await store.async_save(intelligence_data)
        _LOGGER.info(f"Entity analysis complete. {len(intelligence_data)} entities processed and saved.")

    hass.services.async_register(DOMAIN, "analyze_entities", _analyze_entities_service)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Unregister the service when the integration is unloaded
        hass.services.async_remove(DOMAIN, "analyze_entities")

    return unload_ok
