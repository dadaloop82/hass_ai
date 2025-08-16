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
from .alert_monitor import AlertMonitor

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
INTELLIGENCE_DATA_KEY = f"{DOMAIN}_intelligence_data"
AI_RESULTS_KEY = f"{DOMAIN}_ai_results"
CORRELATIONS_KEY = f"{DOMAIN}_correlations"
PANEL_URL_PATH = "hass-ai-panel"

# Cache busting timestamp
CACHE_BUSTER = int(time.time())  # v1.9.37.1 - Multi-category frontend support

# Global operation tracking
_active_operations = {}  # Dict to track active operations by hass instance ID


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
    websocket_api.async_register_command(hass, handle_save_alert_threshold)
    websocket_api.async_register_command(hass, handle_load_alert_thresholds)
    websocket_api.async_register_command(hass, handle_get_alert_status)
    websocket_api.async_register_command(hass, handle_configure_alert_service)
    websocket_api.async_register_command(hass, handle_update_filtered_alerts)
    websocket_api.async_register_command(hass, handle_clear_storage)
    websocket_api.async_register_command(hass, handle_stop_operation)

    # Store the storage object for later use
    store = storage.Store(hass, STORAGE_VERSION, INTELLIGENCE_DATA_KEY)
    
    # Initialize alert monitor
    alert_monitor = AlertMonitor(hass)
    await alert_monitor.async_setup()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "store": store,
        "config": entry.data,
        "options": entry.options,
        "alert_monitor": alert_monitor
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
        # Periodic scanning can be implemented in future versions if needed
        pass

    entry.async_on_unload(event.async_track_time_interval(hass, periodic_scan, scan_interval))

    # Setup services
    await async_setup_services(hass)

    _LOGGER.info(f"HASS AI integration loaded successfully with scan interval: {scan_interval_days} days")
    
    _LOGGER.info("🏠 HASS AI v1.9.37 - Fixed Entity Categorization + Multi-Category Support")
    _LOGGER.info("🔧 Fixed UNKNOWN entities issue, all entities now get proper multiple categories")
    
    return True


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/load_ai_results",
})
@websocket_api.async_response
async def handle_load_ai_results(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to load saved AI analysis results."""
    try:
        _LOGGER.info(f"Loading AI results from storage key: {AI_RESULTS_KEY}")
        ai_results_store = storage.Store(hass, STORAGE_VERSION, AI_RESULTS_KEY)
        results_data = await ai_results_store.async_load()
        
        if results_data:
            _LOGGER.info(f"Loaded AI results: {len(results_data.get('results', {}))} entities")
            # Send the full data including metadata
            connection.send_message(websocket_api.result_message(msg["id"], results_data))
        else:
            _LOGGER.info("No AI results found in storage")
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
    vol.Optional("analysis_type", default="importance"): str,
})
@websocket_api.async_response
async def handle_scan_entities(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to scan entities and send results back in real-time."""
    try:
        # Register this operation as active
        hass_id = id(hass)
        _active_operations[hass_id] = {
            "type": "entity_scan",
            "cancelled": False,
            "connection": connection,
            "msg_id": msg["id"]
        }
        
        connection.send_message(websocket_api.result_message(msg["id"], {"status": "started"}))

        # Get language from message
        language = msg.get("language", "en")
        new_entities_only = msg.get("new_entities_only", False)
        existing_entities = set(msg.get("existing_entities", []))
        analysis_type = msg.get("analysis_type", "importance")
        
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
        
        # Create cancellation check function
        def is_cancelled():
            cancelled = hass_id in _active_operations and _active_operations[hass_id].get("cancelled", False)
            if cancelled:
                _LOGGER.info(f"🛑 Cancellation detected for hass_id {hass_id}")
            return cancelled
        
        # Get importance for all entities in batches
        importance_results = await get_entities_importance_batched(
            hass, filtered_states, 3, ai_provider, api_key, connection, msg["id"], conversation_agent, language, analysis_type, is_cancelled
        )

        # Send each result as it's processed
        for result in importance_results:
            # Check if operation was cancelled
            hass_id = id(hass)
            if hass_id in _active_operations and _active_operations[hass_id].get("cancelled"):
                _LOGGER.info("Entity scan was cancelled by user")
                break
                
            connection.send_message(websocket_api.event_message(msg["id"], {"type": "entity_result", "result": result}))
        
        # Save AI analysis results automatically
        await _save_ai_results(hass, importance_results)
            
        connection.send_message(websocket_api.event_message(msg["id"], {"type": "scan_complete"}))
        _LOGGER.info(f"{scan_type.capitalize()} scan completed successfully for {len(importance_results)} entities")
        
    except asyncio.CancelledError:
        _LOGGER.info("Entity scan was cancelled")
        connection.send_message(websocket_api.event_message(msg["id"], {"type": "scan_cancelled"}))
    except Exception as e:
        _LOGGER.error(f"Error during entity scan: {e}")
        connection.send_message(websocket_api.error_message(msg["id"], "scan_failed", str(e)))
    finally:
        # Clean up active operation
        hass_id = id(hass)
        if hass_id in _active_operations:
            del _active_operations[hass_id]


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
        
        # Update alert monitor with new entities
        entry_id = next(iter(hass.data[DOMAIN]))
        alert_monitor = hass.data[DOMAIN][entry_id].get("alert_monitor")
        if alert_monitor:
            await alert_monitor.update_monitored_entities(msg["results"])
        
        connection.send_message(websocket_api.result_message(msg["id"], {"success": True}))
        
    except Exception as e:
        _LOGGER.error(f"Error saving AI results: {e}")
        connection.send_message(websocket_api.error_message(msg["id"], "save_failed", str(e)))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        # Unload services
        await async_unload_services(hass)
        
        # Unload alert monitor
        entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
        alert_monitor = entry_data.get("alert_monitor")
        if alert_monitor:
            await alert_monitor.async_unload()
        
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
        vol.Required("category"): vol.Any(str, [str]),  # Accept both string and array
    })],
    vol.Optional("language", default="en"): str,
})
@websocket_api.async_response
async def handle_find_correlations(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to find correlations between entities using AI with progress tracking."""
    try:
        # Register this operation as active
        hass_id = id(hass)
        _active_operations[hass_id] = {
            "type": "correlation_analysis",
            "cancelled": False,
            "connection": connection,
            "msg_id": msg["id"]
        }
        
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
            # Check if operation was cancelled
            hass_id = id(hass)
            if hass_id in _active_operations and _active_operations[hass_id].get("cancelled"):
                _LOGGER.info("Correlation analysis was cancelled by user")
                break
                
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
        
    except asyncio.CancelledError:
        _LOGGER.info("Correlation analysis was cancelled")
        connection.send_message(websocket_api.event_message(msg["id"], {"type": "correlation_cancelled"}))
    except Exception as e:
        _LOGGER.error(f"Error in correlation analysis: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "correlation_error", str(e)
        ))
    finally:
        # Clean up active operation
        hass_id = id(hass)
        if hass_id in _active_operations:
            del _active_operations[hass_id]


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


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/save_alert_threshold",
    vol.Required("entity_id"): str,
    vol.Required("threshold"): str,
})
@websocket_api.async_response
async def handle_save_alert_threshold(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to save an alert threshold for an entity."""
    try:
        entity_id = msg["entity_id"]
        threshold = msg["threshold"]
        
        # Validate threshold level
        if threshold not in ["MEDIUM", "SEVERE", "CRITICAL"]:
            raise ValueError(f"Invalid threshold level: {threshold}")
        
        # Save to storage
        from .intelligence import _save_entity_alert_threshold
        success = _save_entity_alert_threshold(entity_id, threshold, hass)
        
        if success:
            connection.send_message(websocket_api.result_message(msg["id"], {"success": True}))
        else:
            connection.send_message(websocket_api.error_message(
                msg["id"], "save_error", "Failed to save alert threshold"
            ))
        
    except Exception as e:
        _LOGGER.error(f"Error saving alert threshold: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "save_error", str(e)
        ))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/load_alert_thresholds",
})
@websocket_api.async_response
async def handle_load_alert_thresholds(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to load alert thresholds."""
    try:
        thresholds = hass.data.get("hass_ai_alert_thresholds", {})
        
        connection.send_message(websocket_api.result_message(msg["id"], {
            "thresholds": thresholds
        }))
        
    except Exception as e:
        _LOGGER.error(f"Error loading alert thresholds: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "load_error", str(e)
        ))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/clear_storage",
})
@websocket_api.async_response
async def handle_clear_storage(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle the command to clear all stored data."""
    try:
        _LOGGER.info("Clearing all HASS AI stored data")
        
        # Log the storage keys being used
        _LOGGER.info(f"Storage keys: AI_RESULTS_KEY={AI_RESULTS_KEY}, CORRELATIONS_KEY={CORRELATIONS_KEY}, INTELLIGENCE_DATA_KEY={INTELLIGENCE_DATA_KEY}")
        
        # Clear all stored data in hass.data
        keys_to_clear = [
            AI_RESULTS_KEY,
            INTELLIGENCE_DATA_KEY,
            CORRELATIONS_KEY,
            "hass_ai_alert_thresholds"
        ]
        
        for key in keys_to_clear:
            if key in hass.data:
                _LOGGER.info(f"Clearing hass.data key: {key}")
                hass.data[key] = {}
                
        # Clear the correct storage stores using the same keys as saving functions
        _LOGGER.info(f"Clearing AI results store with key: {AI_RESULTS_KEY}")
        ai_results_store = storage.Store(hass, STORAGE_VERSION, AI_RESULTS_KEY)
        await ai_results_store.async_save({})
        
        _LOGGER.info(f"Clearing intelligence store with key: {INTELLIGENCE_DATA_KEY}")
        intelligence_store = storage.Store(hass, STORAGE_VERSION, INTELLIGENCE_DATA_KEY)
        await intelligence_store.async_save({})
        
        _LOGGER.info(f"Clearing correlations store with key: {CORRELATIONS_KEY}")
        correlations_store = storage.Store(hass, STORAGE_VERSION, CORRELATIONS_KEY)
        await correlations_store.async_save({})
        
        # Alert thresholds store (uses different naming convention)
        _LOGGER.info("Clearing alert thresholds store")
        alert_thresholds_store = storage.Store(hass, STORAGE_VERSION, "hass_ai_alert_thresholds")
        await alert_thresholds_store.async_save({})
        
        # Clear overrides store (uses INTELLIGENCE_DATA_KEY from config entry)
        try:
            entry_id = next(iter(hass.data[DOMAIN]))
            entry_store = hass.data[DOMAIN][entry_id]["store"]
            _LOGGER.info(f"Clearing overrides store from entry: {entry_id}")
            await entry_store.async_save({})
            _LOGGER.info("Cleared overrides store from config entry")
        except Exception as e:
            _LOGGER.warning(f"Could not clear entry store: {e}")
        
        _LOGGER.info("Successfully cleared all HASS AI data")
        connection.send_message(websocket_api.result_message(msg["id"], {
            "success": True,
            "message": "All data cleared successfully"
        }))
        
    except Exception as e:
        _LOGGER.error(f"Error clearing storage: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "clear_error", str(e)
        ))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/stop_operation"
})
@websocket_api.async_response
async def handle_stop_operation(hass: HomeAssistant, connection, msg):
    """Handle stop operation command."""
    try:
        hass_id = id(hass)
        
        if hass_id in _active_operations:
            # Mark the active operation as cancelled
            operation_info = _active_operations[hass_id]
            operation_info["cancelled"] = True
            
            _LOGGER.info(f"🛑 Marking operation as cancelled: {operation_info.get('type', 'unknown')}")
            
            # If there's a task handle, cancel it (but keep the operation info for checking)
            if "task" in operation_info:
                operation_info["task"].cancel()
                _LOGGER.info("🛑 Cancelled task handle")
            
            # Don't delete the operation yet - let the function check the cancelled flag first
            
            connection.send_message(websocket_api.result_message(msg["id"], {
                "success": True,
                "message": "Operation stopped successfully"
            }))
        else:
            connection.send_message(websocket_api.result_message(msg["id"], {
                "success": False,
                "message": "No active operation to stop"
            }))
            
    except Exception as e:
        _LOGGER.error(f"Error stopping operation: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "stop_error", str(e)
        ))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/update_filtered_alerts",
    vol.Required("min_weight"): int,
    vol.Required("category_filter"): str,
})
@websocket_api.async_response
async def handle_update_filtered_alerts(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle updating monitored entities based on filtered entities from frontend."""
    try:
        min_weight = msg["min_weight"]
        category_filter = msg["category_filter"]
        
        # Load current AI results
        ai_results = await _load_ai_results(hass)
        
        if not ai_results:
            connection.send_message(websocket_api.result_message(msg["id"], {
                "success": False,
                "message": "No AI results available"
            }))
            return
        
        # Filter entities based on criteria
        filtered_entities = []
        
        for entity_id, data in ai_results.items():
            if isinstance(data, dict):
                # Apply weight filter
                overall_weight = data.get("overall_weight", 0)
                if overall_weight < min_weight:
                    continue
                
                # Apply category filter
                category = data.get("category", "").upper()
                if category_filter != "ALL" and category != category_filter:
                    continue
                
                # Only include ALERTS category entities for monitoring
                if category == "ALERTS":
                    filtered_entities.append({
                        "entity_id": entity_id,
                        "category": category,
                        "overall_weight": overall_weight,
                        "analysis": data.get("analysis", ""),
                        "threshold": data.get("threshold", "NORMAL")
                    })
        
        # Update alert monitor with filtered entities
        entry_id = next(iter(hass.data[DOMAIN]))
        alert_monitor = hass.data[DOMAIN][entry_id].get("alert_monitor")
        
        if alert_monitor:
            # Create a results dict in the format expected by update_monitored_entities
            results_dict = {entity["entity_id"]: entity for entity in filtered_entities}
            await alert_monitor.update_monitored_entities(results_dict)
            
            _LOGGER.info(f"🔔 Updated alert monitoring with {len(filtered_entities)} filtered entities (weight ≥ {min_weight}, category: {category_filter})")
        
        connection.send_message(websocket_api.result_message(msg["id"], {
            "success": True,
            "filtered_count": len(filtered_entities),
            "message": f"Updated monitoring with {len(filtered_entities)} entities"
        }))
        
    except Exception as e:
        _LOGGER.error(f"Error updating filtered alerts: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "update_error", str(e)
        ))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/get_alert_status",
})
@websocket_api.async_response
async def handle_get_alert_status(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle getting alert monitoring status."""
    try:
        # Get alert monitor from first entry
        entry_id = next(iter(hass.data[DOMAIN]))
        alert_monitor = hass.data[DOMAIN][entry_id].get("alert_monitor")
        
        if alert_monitor:
            status = await alert_monitor.get_alert_status()
            connection.send_message(websocket_api.result_message(msg["id"], status))
        else:
            connection.send_message(websocket_api.result_message(msg["id"], {
                "monitoring_enabled": False,
                "error": "Alert monitor not initialized"
            }))
            
    except Exception as e:
        _LOGGER.error(f"Error getting alert status: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "status_error", str(e)
        ))


@websocket_api.websocket_command({
    vol.Required("type"): "hass_ai/configure_alert_service",
    vol.Optional("notification_service"): str,
    vol.Optional("use_input_text"): bool,
    vol.Optional("input_text_entity"): str,
    vol.Optional("entity_thresholds"): dict,
})
@websocket_api.async_response
async def handle_configure_alert_service(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Handle configuring alert notification service."""
    try:
        # Get alert monitor from first entry
        entry_id = next(iter(hass.data[DOMAIN]))
        alert_monitor = hass.data[DOMAIN][entry_id].get("alert_monitor")
        
        if alert_monitor:
            # Update notification method
            if "notification_service" in msg:
                alert_monitor.notification_service = msg["notification_service"]
                
            if "use_input_text" in msg:
                alert_monitor.use_input_text = msg["use_input_text"]
                
            if "input_text_entity" in msg:
                alert_monitor.input_text_entity = msg["input_text_entity"]
            
            # Ensure input_text entity if using that mode
            if alert_monitor.use_input_text:
                await alert_monitor._ensure_input_text_entity()
            
            # Update entity thresholds if provided
            entity_thresholds = msg.get("entity_thresholds", {})
            for entity_id, thresholds in entity_thresholds.items():
                if entity_id in alert_monitor.monitored_entities:
                    alert_monitor.monitored_entities[entity_id]["thresholds"] = thresholds
                    
            # Save configuration
            await alert_monitor._save_configuration()
            
            connection.send_message(websocket_api.result_message(msg["id"], {
                "success": True,
                "message": "Alert configuration updated"
            }))
        else:
            connection.send_message(websocket_api.error_message(
                msg["id"], "config_error", "Alert monitor not initialized"
            ))
            
    except Exception as e:
        _LOGGER.error(f"Error configuring alert service: {e}")
        connection.send_message(websocket_api.error_message(
            msg["id"], "config_error", str(e)
        ))