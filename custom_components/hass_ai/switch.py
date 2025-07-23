from __future__ import annotations
import logging

from homeassistant.components.switch import SwitchEntity
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
    """Set up the HASS AI switch entities."""
    store = storage.Store(hass, STORAGE_VERSION, f"{DOMAIN}_enabled_entities")
    
    entities_to_add = []
    all_states = hass.states.async_all()
    
    for state in all_states:
        if state.domain == DOMAIN:
            continue
        entities_to_add.append(HassAiEnableSwitch(hass, state, store))

    async_add_entities(entities_to_add)


class HassAiEnableSwitch(SwitchEntity):
    """Represents an enable/disable switch for a Home Assistant entity."""

    def __init__(self, hass: HomeAssistant, target_state: State, store: storage.Store):
        """Initialize the switch entity."""
        self.hass = hass
        self._target_entity_id = target_state.entity_id
        self._store = store

        self._attr_unique_id = f"{DOMAIN}_enabled_{self._target_entity_id}"
        self._attr_name = f"HASS AI Enabled: {target_state.name}"
        self._attr_icon = "mdi:robot-love"
        
        self._is_on = True  # Default to enabled

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        stored_data = await self._store.async_load()
        if stored_data and self._target_entity_id in stored_data:
            self._is_on = stored_data[self._target_entity_id]
        else:
            # Save the default state if not already stored
            await self._save_state()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self._is_on = True
        await self._save_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self._is_on = False
        await self._save_state()
        self.async_write_ha_state()

    async def _save_state(self) -> None:
        """Save the current state to storage."""
        data = await self._store.async_load() or {}
        data[self._target_entity_id] = self._is_on
        await self._store.async_save(data)
