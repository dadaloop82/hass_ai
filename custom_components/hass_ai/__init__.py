from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import frontend, websocket_api
from homeassistant.helpers import storage
import voluptuous as vol

from .const import DOMAIN
from .intelligence import get_entity_importance

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
INTELLIGENCE_DATA_KEY = f"{DOMAIN}_intelligence_data"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HASS AI from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Register the custom panel
    if DOMAIN not in hass.data.get("frontend_panels", {}):
        frontend.async_register_built_in_panel(
            hass, "hass-ai-panel", "HASS AI", "mdi:brain"
        )

    # Register the websocket API
    websocket_api.async_register_command(hass, handle_scan_entities)
    websocket_api.async_register_command(hass, handle_save_overrides)

    # Store the storage object for later use
    store = storage.Store(hass, STORAGE_VERSION, INTELLIGENCE_DATA_KEY)
    hass.data[DOMAIN][entry.entry_id] = {"store": store}

    return True

@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/scan_entities",
})
@websocket_api.async_response
async def handle_scan_entities(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to scan entities and send results back in real-time."""
    
    connection.send_message(websocket_api.result_message(msg["id"], {"status": "started"}))

    all_states = hass.states.async_all()
    for state in all_states:
        if state.domain == DOMAIN or state.entity_id.startswith(f"{DOMAIN}."):
            continue
        
        importance = get_entity_importance(state)
        result = {
            "entity_id": state.entity_id,
            "name": state.name,
            "weight": importance["weight"],
            "reason": importance["reason"],
        }
        # Send each result as it's processed
        connection.send_message(websocket_api.event_message(msg["id"], {"type": "entity_result", "result": result}))
        
    connection.send_message(websocket_api.event_message(msg["id"], {"type": "scan_complete"}))

@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/save_overrides",
    vol.Required("overrides"): dict,
})
@websocket_api.async_response
async def handle_save_overrides(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to save user-defined overrides."""
    # Find the active config entry to get the store object
    entry_id = next(iter(hass.data[DOMAIN]))
    store = hass.data[DOMAIN][entry_id]["store"]
    
    await store.async_save(msg["overrides"])
    
    connection.send_message(websocket_api.result_message(msg["id"], {"success": True}))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Clean up
    hass.data[DOMAIN].pop(entry.entry_id)
    frontend.async_remove_panel(hass, "hass-ai-panel")
    return True