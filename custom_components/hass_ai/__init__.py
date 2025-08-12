from __future__ import annotations
import asyncio
import logging
import time
from datetime import timedelta, datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import frontend, websocket_api, http, conversation
from homeassistant.components.conversation import async_get_agent
from homeassistant.components.http import StaticPathConfig
from homeassistant.helpers import storage, event
from homeassistant.util import dt
import voluptuous as vol

from .const import DOMAIN, CONF_CONVERSATION_AGENT
from .intelligence import get_entities_importance_batched
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
INTELLIGENCE_DATA_KEY = f"{DOMAIN}_intelligence_data"
AI_RESULTS_KEY = f"{DOMAIN}_ai_results"
CORRELATIONS_KEY = f"{DOMAIN}_correlations"
PANEL_URL_PATH = "hass-ai-panel"

# Cache busting timestamp
CACHE_BUSTER = int(time.time())  # v1.9.1 - Fresh timestamp


async def _save_ai_results(hass: HomeAssistant, results) -> None:
    """Save AI analysis results to storage."""
    try:
        # Get the first config entry for this integration
        entry_id = next(iter(hass.data[DOMAIN]))
        
        # Create a separate store for AI results
        ai_results_store = storage.Store(hass, STORAGE_VERSION, AI_RESULTS_KEY)
        
        # Handle both formats: list of results or already formatted data
        if isinstance(results, list):
            # Old format - convert to new format
            results_data = {
                "last_scan_timestamp": dt.utcnow().isoformat(),
                "total_entities": len(results),
                "results": {result["entity_id"]: result for result in results}
            }
        else:
            # New format - use as is
            results_data = results
        
        await ai_results_store.async_save(results_data)
        _LOGGER.info(f"💾 Saved AI analysis results for {results_data['total_entities']} entities")
        
    except Exception as e:
        _LOGGER.error(f"Error saving AI results: {e}")


async def _save_correlations(hass: HomeAssistant, correlations) -> None:
    """Save correlation analysis results to storage."""
    try:
        correlations_store = storage.Store(hass, STORAGE_VERSION, CORRELATIONS_KEY)
        
        correlations_data = {
            "last_correlation_timestamp": dt.utcnow().isoformat(),
            "total_entities": len(correlations),
            "correlations": correlations
        }
        
        await correlations_store.async_save(correlations_data)
        _LOGGER.info(f"💾 Saved correlations for {correlations_data['total_entities']} entities")
        
    except Exception as e:
        _LOGGER.error(f"Error saving correlations: {e}")


async def _load_correlations(hass: HomeAssistant) -> dict:
    """Load correlation analysis results from storage."""
    try:
        correlations_store = storage.Store(hass, STORAGE_VERSION, CORRELATIONS_KEY)
        correlations_data = await correlations_store.async_load()
        
        if correlations_data:
            _LOGGER.info(f"📂 Loaded correlations for {correlations_data.get('total_entities', 0)} entities from {correlations_data.get('last_correlation_timestamp', 'unknown time')}")
            return correlations_data.get("correlations", {})
        else:
            _LOGGER.info("📂 No previous correlations found")
            return {}
            
    except Exception as e:
        _LOGGER.error(f"Error loading correlations: {e}")
        return {}


async def _load_ai_results(hass: HomeAssistant) -> dict:
    """Load AI analysis results from storage."""
    try:
        ai_results_store = storage.Store(hass, STORAGE_VERSION, AI_RESULTS_KEY)
        results_data = await ai_results_store.async_load()
        
        if results_data:
            _LOGGER.info(f"📂 Loaded AI results for {results_data.get('total_entities', 0)} entities from {results_data.get('last_scan_timestamp', 'unknown time')}")
            return results_data.get("results", {})
        else:
            _LOGGER.info("📂 No previous AI results found")
            return {}
            
    except Exception as e:
        _LOGGER.error(f"Error loading AI results: {e}")
        return {}

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
                "module_url": f"/api/{DOMAIN}/static/panel.js?v={CACHE_BUSTER}",
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
    websocket_api.async_register_command(hass, handle_load_ai_results)
    websocket_api.async_register_command(hass, handle_save_ai_results)
    websocket_api.async_register_command(hass, handle_find_correlations)
    websocket_api.async_register_command(hass, handle_save_correlations)
    websocket_api.async_register_command(hass, handle_load_correlations)

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
    
    _LOGGER.info("🏠 HASS AI v1.9.5 - Unknown Entities Styling + Incremental Scanning")
    _LOGGER.info("� Gray out unknown/unavailable entities, incremental scans for new entities")
    
    return True


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/load_ai_results",
})
@websocket_api.async_response
async def handle_load_ai_results(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to load saved AI analysis results."""
    try:
        ai_results_store = storage.Store(hass, STORAGE_VERSION, AI_RESULTS_KEY)
        results_data = await ai_results_store.async_load()
        
        if results_data:
            # Send the full data including metadata
            connection.send_message(websocket_api.result_message(msg["id"], results_data))
        else:
            # Send empty results
            connection.send_message(websocket_api.result_message(msg["id"], {
                "results": {},
                "last_scan_timestamp": None,
                "total_entities": 0
            }))
    except Exception as e:
        _LOGGER.error(f"Error loading AI results: {e}")
        connection.send_message(websocket_api.error_message(msg["id"], "load_failed", str(e)))


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
    vol.Optional("language", default="en"): str,
    vol.Optional("new_entities_only", default=False): bool,
    vol.Optional("existing_entities", default=[]): list,
})
@websocket_api.async_response
async def handle_scan_entities(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to scan entities and send results back in real-time."""
    try:
        connection.send_message(websocket_api.result_message(msg["id"], {"status": "started"}))

        # Get language from message
        language = msg.get("language", "en")
        new_entities_only = msg.get("new_entities_only", False)
        existing_entities = set(msg.get("existing_entities", []))
        
        # Get the first config entry for this integration
        config_entry = None
        for entry in hass.config_entries.async_entries(DOMAIN):
            config_entry = entry
            break
        
        # Get AI configuration
        ai_provider = "OpenAI"
        api_key = None
        if config_entry:
            ai_provider = config_entry.data.get("ai_provider", "OpenAI")
            api_key = config_entry.data.get("api_key")
            _LOGGER.info(f"Config loaded - Provider: {ai_provider}, API key length: {len(api_key) if api_key else 0}")
        else:
            _LOGGER.warning("No config entry found for HASS AI")

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
        
        # If scanning only new entities, filter out existing ones
        if new_entities_only:
            filtered_states = [
                state for state in filtered_states
                if state.entity_id not in existing_entities
            ]
            scan_type = "incremental"
        else:
            scan_type = "full"

        _LOGGER.info(f"Starting {scan_type} scan of {len(filtered_states)} entities using {ai_provider}")

        # Get conversation agent from config
        conversation_agent = entry.data.get(CONF_CONVERSATION_AGENT, "auto")
        
        # Get language from message, default to English
        language = msg.get("language", "en")
        _LOGGER.info(f"Using language: {language}")
        
        # Get importance for all entities in batches
        importance_results = await get_entities_importance_batched(
            hass, filtered_states, 10, ai_provider, api_key, connection, msg["id"], conversation_agent, language
        )

        # Send each result as it's processed
        for result in importance_results:
            connection.send_message(websocket_api.event_message(msg["id"], {"type": "entity_result", "result": result}))
        
        # Save AI analysis results automatically
        await _save_ai_results(hass, importance_results)
            
        connection.send_message(websocket_api.event_message(msg["id"], {"type": "scan_complete"}))
        _LOGGER.info(f"{scan_type.capitalize()} scan completed successfully for {len(importance_results)} entities")
        
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


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/save_ai_results",
    vol.Required("results"): dict,
    vol.Optional("timestamp"): str,
    vol.Optional("total_entities"): int,
})
@websocket_api.async_response
async def handle_save_ai_results(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to save AI analysis results."""
    try:
        results_data = {
            "results": msg["results"],
            "last_scan_timestamp": msg.get("timestamp"),
            "total_entities": msg.get("total_entities", len(msg["results"]))
        }
        
        await _save_ai_results(hass, results_data)
        connection.send_message(websocket_api.result_message(msg["id"], {"success": True}))
        
    except Exception as e:
        _LOGGER.error(f"Error saving AI results: {e}")
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


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/evaluate_single_entity",
    vol.Required("entity_id"): str,
    vol.Optional("language", default="en"): str,
})
@websocket_api.async_response
async def handle_evaluate_single_entity(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to evaluate a single entity."""
    try:
        entity_id = msg["entity_id"]
        language = msg.get("language", "en")
        
        # Get the entity state
        entity_state = hass.states.get(entity_id)
        if not entity_state:
            connection.send_message(websocket_api.error_message(msg["id"], "entity_not_found", f"Entity {entity_id} not found"))
            return
        
        # Get the first config entry for this integration
        config_entry = None
        for entry in hass.config_entries.async_entries(DOMAIN):
            config_entry = entry
            break
        
        if not config_entry:
            connection.send_message(websocket_api.error_message(msg["id"], "no_config", "No HASS AI configuration found"))
            return
        
        # Get AI configuration
        ai_provider = config_entry.data.get("ai_provider", "OpenAI")
        api_key = config_entry.data.get("api_key")
        conversation_agent = config_entry.data.get(CONF_CONVERSATION_AGENT, "auto")
        
        _LOGGER.info(f"Evaluating single entity: {entity_id}")
        
        # Use the same intelligence engine to evaluate single entity
        from .intelligence import get_entities_importance_batched
        
        importance_results = await get_entities_importance_batched(
            hass, [entity_state], 1, ai_provider, api_key, connection, msg["id"], conversation_agent, language
        )
        
        if importance_results:
            # Send the result
            result = importance_results[0]
            connection.send_message(websocket_api.event_message(msg["id"], {"type": "entity_result", "result": result}))
            
            # Save to AI results automatically
            await _save_ai_results(hass, importance_results)
            
            _LOGGER.info(f"Successfully evaluated entity: {entity_id}")
        else:
            connection.send_message(websocket_api.error_message(msg["id"], "evaluation_failed", f"Failed to evaluate {entity_id}"))
        
    except Exception as e:
        _LOGGER.error(f"Error evaluating single entity: {e}")
        connection.send_message(websocket_api.error_message(msg["id"], "evaluation_error", str(e)))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/find_correlations",
    vol.Required("entities"): [vol.Schema({
        vol.Required("entity_id"): str,
        vol.Required("ai_weight"): vol.Any(int, float),
        vol.Required("reason"): str,
        vol.Required("category"): str,
    })],
    vol.Optional("language", default="en"): str,
})
@websocket_api.async_response
async def handle_find_correlations(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to find correlations between entities using AI with progress tracking."""
    try:
        entities = msg["entities"]
        language = msg.get("language", "en")
        
        total_entities = len(entities)
        _LOGGER.info(f"Finding correlations for {total_entities} entities")
        
        # Initialize correlations dictionary to collect results
        all_correlations = {}
        
        # Send initial progress
        connection.send_message(websocket_api.event_message(
            msg["id"], 
            {
                "type": "correlation_progress", 
                "data": {
                    "message": "🚀 Iniziando analisi correlazioni..." if language.startswith('it') else "🚀 Starting correlation analysis...",
                    "current": 0,
                    "total": total_entities,
                    "percentage": 0
                }
            }
        ))
        
        # Import the correlation analysis function
        from .intelligence import find_entity_correlations
        
        # Process entities one by one to find correlations
        for index, entity in enumerate(entities, 1):
            entity_id = entity["entity_id"]
            
            try:
                # Send progress update
                connection.send_message(websocket_api.event_message(
                    msg["id"], 
                    {
                        "type": "correlation_progress", 
                        "data": {
                            "message": f"🔍 Analizzando {entity_id}..." if language.startswith('it') else f"🔍 Analyzing {entity_id}...",
                            "current": index,
                            "total": total_entities,
                            "percentage": round((index / total_entities) * 100),
                            "entity_id": entity_id
                        }
                    }
                ))
                
                # Find correlations for this entity against all others
                correlations = await find_entity_correlations(
                    hass, entity, entities, language
                )
                
                # Store correlations in our collection
                all_correlations[entity_id] = correlations
                
                # Send result for this entity
                connection.send_message(websocket_api.event_message(
                    msg["id"], 
                    {
                        "type": "correlation_result", 
                        "result": {
                            "entity_id": entity_id,
                            "correlations": correlations
                        }
                    }
                ))
                
                # Auto-save correlations as they come in (incremental save)
                await _save_correlations(hass, all_correlations)
                
                # Small delay to show progress
                await asyncio.sleep(0.5)
                
            except Exception as e:
                _LOGGER.error(f"Error finding correlations for {entity_id}: {e}")
                
                # Store empty correlations for this entity
                all_correlations[entity_id] = []
                
                # Send error result
                connection.send_message(websocket_api.event_message(
                    msg["id"], 
                    {
                        "type": "correlation_result", 
                        "result": {
                            "entity_id": entity_id,
                            "correlations": [],
                            "error": str(e)
                        }
                    }
                ))
        
        # Final save of all correlations
        await _save_correlations(hass, all_correlations)
        
        # Send completion message
        connection.send_message(websocket_api.event_message(
            msg["id"], {
                "type": "correlation_complete",
                "data": {
                    "message": "🎉 Analisi correlazioni completata!" if language.startswith('it') else "🎉 Correlation analysis completed!",
                    "total_processed": total_entities
                }
            }
        ))
        
        _LOGGER.info("Correlation analysis completed")
        
    except Exception as e:
        _LOGGER.error(f"Error in correlation analysis: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "correlation_error", str(e)
        ))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/save_correlations",
    vol.Required("correlations"): dict,
    vol.Optional("timestamp"): str,
    vol.Optional("total_entities"): int,
})
@websocket_api.async_response
async def handle_save_correlations(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to save correlation results."""
    try:
        correlations = msg["correlations"]
        
        await _save_correlations(hass, correlations)
        
        connection.send_message(websocket_api.result_message(msg["id"], {"success": True}))
        
    except Exception as e:
        _LOGGER.error(f"Error saving correlations: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "save_error", str(e)
        ))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/load_correlations",
})
@websocket_api.async_response
async def handle_load_correlations(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to load correlation results."""
    try:
        correlations = await _load_correlations(hass)
        
        connection.send_message(websocket_api.result_message(msg["id"], correlations))
        
    except Exception as e:
        _LOGGER.error(f"Error loading correlations: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "load_error", str(e)
        ))