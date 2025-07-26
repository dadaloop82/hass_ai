from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import frontend, websocket_api, http
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers import storage, event
import voluptuous as vol

from .const import DOMAIN
from .intelligence import get_entity_importance

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
INTELLIGENCE_DATA_KEY = f"{DOMAIN}_intelligence_data"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HASS AI from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Register a static path for the panel to be served from
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            f"/api/{DOMAIN}/static",
            hass.config.path("custom_components", DOMAIN, "www"),
            cache_headers=False
        )
    ])

    # Register the panel
    frontend.async_register_panel(
        hass,
        "hass-ai-panel",
        "hass_ai",
        "HASS AI",
        "mdi:brain",
        require_admin=True,
        embed_iframe=False,
        url_path="hass-ai-panel",
        module_url=f"/api/{DOMAIN}/static/panel.js",
    )

    # Register the websocket API
    websocket_api.async_register_command(hass, handle_scan_entities)
    websocket_api.async_register_command(hass, handle_save_overrides)
    websocket_api.async_register_command(hass, handle_load_overrides)

    # Store the storage object for later use
    store = storage.Store(hass, STORAGE_VERSION, INTELLIGENCE_DATA_KEY)
    hass.data[DOMAIN][entry.entry_id] = {"store": store}

    # Get scan interval from config entry
    scan_interval_days = entry.data.get("scan_interval", 7) # Default to 7 days
    scan_interval = timedelta(days=scan_interval_days)

    # Schedule periodic scan
    async def periodic_scan(now):
        _LOGGER.debug("Performing periodic HASS AI scan")
        # This will trigger the scan logic, but won't send to frontend unless a client is connected
        # For now, we'll just call the intelligence gathering part
        # In a real scenario, you might want to trigger a background task or service call
        # that then updates the stored data.
        # For demonstration, we'll just log that a scan would occur.
        pass # The actual scan logic is handled by handle_scan_entities via websocket

    entry.async_on_unload(event.async_track_time_interval(hass, periodic_scan, scan_interval))

    return True

@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/load_overrides",
})
@websocket_api.async_response
async def handle_load_overrides(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to load user-defined overrides."""
    entry_id = next(iter(hass.data[DOMAIN]))
    store = hass.data[DOMAIN][entry_id]["store"]
    overrides = await store.async_load() or {}
    connection.send_message(websocket_api.result_message(msg["id"], overrides))

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
            "overall_weight": importance["overall_weight"],
            "overall_reason": importance["overall_reason"],
            "attribute_details": importance["attribute_details"],
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