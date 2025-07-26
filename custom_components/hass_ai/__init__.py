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
from .intelligence import get_entity_importance

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
                "js_url": f"/api/{DOMAIN}/static/panel.js",
            }
        },
        require_admin=True,
    )

    # Register the websocket API
    websocket_api.async_register_command(hass, handle_scan_entities)
    websocket_api.async_register_command(hass, handle_save_overrides)
    websocket_api.async_register_command(hass, handle_load_overrides)
    websocket_api.async_register_command(hass, handle_check_agent)

    # Store the storage object for later use
    store = storage.Store(hass, STORAGE_VERSION, INTELLIGENCE_DATA_KEY)
    hass.data[DOMAIN][entry.entry_id] = {"store": store}

    # Get scan interval from config entry
    scan_interval_days = entry.data.get("scan_interval", 7)
    scan_interval = timedelta(days=scan_interval_days)

    # Schedule periodic scan
    async def periodic_scan(now):
        _LOGGER.debug("Performing periodic HASS AI scan")
        pass  # Implement scan logic if needed

    entry.async_on_unload(event.async_track_time_interval(hass, periodic_scan, scan_interval))

    return True

@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/check_agent",
})
@websocket_api.async_response
async def handle_check_agent(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Check if the current conversation agent is a supported LLM."""
    try:
        agent = await async_get_agent(hass)
        if not agent:
            connection.send_message(websocket_api.result_message(msg["id"], {
                "is_default_agent": True,
                "agent_id": "none",
                "is_supported_llm": False,
            }))
            return

        agent_id = getattr(agent, "id", "unknown")
        is_default_agent = agent_id == "homeassistant"

        # Normalizza ID per confronti robusti
        agent_id_clean = agent_id.lower().replace("-", "_").replace(" ", "")
        supported_llms = ["google_gemini", "chatgpt", "openai", "local_llm"]
        is_supported_llm = any(llm in agent_id_clean for llm in supported_llms)

        connection.send_message(websocket_api.result_message(msg["id"], {
            "is_default_agent": is_default_agent,
            "agent_id": agent_id,
            "is_supported_llm": is_supported_llm,
        }))
    except Exception as e:
        _LOGGER.warning(f"[hass_ai] Agent check failed: {e}")
        connection.send_message(
            websocket_api.error_message(msg["id"], "agent_error", str(e))
        )

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

        importance = await get_entity_importance(hass, state)
        result = {
            "entity_id": state.entity_id,
            "name": state.name,
            "overall_weight": importance["overall_weight"],
            "overall_reason": importance["overall_reason"],
            "prompt": importance.get("prompt"),
            "response_text": importance.get("response_text"),
        }
        connection.send_message(websocket_api.event_message(msg["id"], {
            "type": "entity_result",
            "result": result
        }))

    connection.send_message(websocket_api.event_message(msg["id"], {
        "type": "scan_complete"
    }))

@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/save_overrides",
    vol.Required("overrides"): dict,
})
@websocket_api.async_response
async def handle_save_overrides(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to save user-defined overrides."""
    entry_id = next(iter(hass.data[DOMAIN]))
    store = hass.data[DOMAIN][entry_id]["store"]

    await store.async_save(msg["overrides"])

    connection.send_message(websocket_api.result_message(msg["id"], {"success": True}))

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True