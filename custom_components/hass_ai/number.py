from __future__ import annotations
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import storage

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HASS AI number entities."""
    store = storage.Store(hass, STORAGE_VERSION, f"{DOMAIN}_weights")
    
    # Analyze all entities and create number controls for them
    entities_to_add = []
    all_states = hass.states.async_all()
    
    for state in all_states:
        # We don't want to create controls for our own entities
        if state.domain == DOMAIN:
            continue
        entities_to_add.append(HassAiWeightNumber(hass, state, store))

    async_add_entities(entities_to_add)


class HassAiWeightNumber(NumberEntity):
    """Represents a weight control for a Home Assistant entity."""

    def __init__(self, hass: HomeAssistant, target_state: State, store: storage.Store):
        """Initialize the number entity."""
        self.hass = hass
        self._target_entity_id = target_state.entity_id
        self._store = store
        self._state = target_state

        self._attr_unique_id = f"{DOMAIN}_weight_{self._target_entity_id}"
        self._attr_name = f"HASS AI Weight: {target_state.name}"
        self._attr_icon = "mdi:scale-balance"
        
        self._attr_native_min_value = 1
        self._attr_native_max_value = 5
        self._attr_native_step = 1
        
        self._current_weight = None
        self._reason = ""

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        stored_data = await self._store.async_load()
        if stored_data and self._target_entity_id in stored_data:
            self._current_weight = stored_data[self._target_entity_id].get("weight")
            self._reason = stored_data[self._target_entity_id].get("reason")
        else:
            # If not stored, calculate initial weight
            initial_data = self._get_initial_importance()
            self._current_weight = initial_data["weight"]
            self._reason = initial_data["reason"]
            await self._save_state()

    @property
    def native_value(self) -> float | None:
        """Return the current weight."""
        return self._current_weight

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the reason for the weight."""
        return {"reason_for_weight": self._reason}

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._current_weight = int(value)
        self._reason = "Manually overridden by user"
        await self._save_state()
        self.async_write_ha_state()

    async def _save_state(self) -> None:
        """Save the current state to storage."""
        data = await self._store.async_load() or {}
        data[self._target_entity_id] = {
            "weight": self._current_weight,
            "reason": self._reason
        }
        await self._store.async_save(data)

    def _get_initial_importance(self) -> dict:
        """Calculate the initial importance of the entity."""
        # This is the same logic from our previous __init__.py
        domain = self._state.domain
        attributes = self._state.attributes
        entity_id = self._state.entity_id
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
