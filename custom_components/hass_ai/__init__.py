from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import frontend, websocket_api, http, conversation
from homeassistant.components.conversation import async_get_agent
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers import storage, event
import voluptuous as vol

from .const import DOMAIN
from .intelligence import get_entities_importance_batched
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
INTELLIGENCE_DATA_KEY = f"{DOMAIN}_intelligence_data"
PANEL_URL_PATH = "hass-ai-panel"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HASS AI from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Register the static path for the panel
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            f"/api/{DOMAIN}/static",
            hass.config.path("custom_components", DOMAIN, "www"),
            cache_headers=False
        )
    ])

    # Register the custom panel
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="HASS AI",
        sidebar_icon="mdi:brain",
        frontend_url_path=PANEL_URL_PATH,
        config={
            "_panel_custom": {
                "name": "hass-ai-panel",
                "embed_iframe": False,
                "trust_external": False,
                "module_url": f"/api/{DOMAIN}/static/panel.js",
                "extra_module_url": [
                    "https://unpkg.com/@material/mwc-select@0.25.3/mwc-select.js?module",
                    "https://unpkg.com/@material/mwc-list@0.25.3/mwc-list-item.js?module",
                    "https://unpkg.com/@material/mwc-button@0.25.3/mwc-button.js?module"
                ],
            },
            "type": "module",
        },
        require_admin=True,
    )

    # Register the websocket API
    websocket_api.async_register_command(hass, handle_scan_entities)
    websocket_api.async_register_command(hass, handle_save_overrides)
    websocket_api.async_register_command(hass, handle_load_overrides)

    # Store the storage object for later use
    store = storage.Store(hass, STORAGE_VERSION, INTELLIGENCE_DATA_KEY)
    hass.data[DOMAIN][entry.entry_id] = {
        "store": store,
        "config": entry.data,
        "options": entry.options
    }

    # Get scan interval from config entry (from data or options)
    scan_interval_days = (
        entry.options.get("scan_interval") or 
        entry.data.get("scan_interval", 7)
    )
    scan_interval = timedelta(days=scan_interval_days)

    # Schedule periodic scan
    async def periodic_scan(now):
        _LOGGER.debug("Performing periodic HASS AI scan")
        # TODO: Implement automatic background scanning if needed
        pass

    entry.async_on_unload(event.async_track_time_interval(hass, periodic_scan, scan_interval))

    # Setup services
    await async_setup_services(hass)

    _LOGGER.info(f"HASS AI integration loaded successfully with scan interval: {scan_interval_days} days")
    return True


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/load_overrides",
})
@websocket_api.async_response
async def handle_load_overrides(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to load user-defined overrides."""
    try:
        entry_id = next(iter(hass.data[DOMAIN]))
        store = hass.data[DOMAIN][entry_id]["store"]
        overrides = await store.async_load() or {}
        connection.send_message(websocket_api.result_message(msg["id"], overrides))
    except Exception as e:
        _LOGGER.error(f"Error loading overrides: {e}")
        connection.send_message(websocket_api.error_message(msg["id"], "load_failed", str(e)))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/scan_entities",
})
@websocket_api.async_response
async def handle_scan_entities(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to scan entities and send results back in real-time."""
    try:
        connection.send_message(websocket_api.result_message(msg["id"], {"status": "started"}))

        all_states = hass.states.async_all()
        
        # Filter out hass_ai entities and system entities
        filtered_states = [
            state for state in all_states 
            if not (
                state.domain == DOMAIN or 
                state.entity_id.startswith(f"{DOMAIN}.") or
                state.domain in ["persistent_notification", "system_log"]
            )
        ]

        _LOGGER.info(f"Starting scan of {len(filtered_states)} entities")

        # Get importance for all entities in batches
        importance_results = await get_entities_importance_batched(hass, filtered_states)

        # Send each result as it's processed
        for result in importance_results:
            connection.send_message(websocket_api.event_message(msg["id"], {"type": "entity_result", "result": result}))
            
        connection.send_message(websocket_api.event_message(msg["id"], {"type": "scan_complete"}))
        _LOGGER.info(f"Scan completed successfully for {len(importance_results)} entities")
        
    except Exception as e:
        _LOGGER.error(f"Error during entity scan: {e}")
        connection.send_message(websocket_api.error_message(msg["id"], "scan_failed", str(e)))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/save_overrides",
    vol.Required("overrides"): dict,
})
@websocket_api.async_response
async def handle_save_overrides(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to save user-defined overrides."""
    try:
        entry_id = next(iter(hass.data[DOMAIN]))
        store = hass.data[DOMAIN][entry_id]["store"]

        await store.async_save(msg["overrides"])
        _LOGGER.debug(f"Saved {len(msg['overrides'])} overrides")

        connection.send_message(websocket_api.result_message(msg["id"], {"success": True}))
        
    except Exception as e:
        _LOGGER.error(f"Error saving overrides: {e}")
        connection.send_message(websocket_api.error_message(msg["id"], "save_failed", str(e)))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        # Unload services
        await async_unload_services(hass)
        
        # Remove panel
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("HASS AI integration unloaded successfully")
        return True
    except Exception as e:
        _LOGGER.error(f"Error unloading HASS AI: {e}")
        return False