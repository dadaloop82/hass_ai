"""Services for HASS AI integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN
from .intelligence import get_entities_importance_batched

_LOGGER = logging.getLogger(__name__)

# Service schemas
SCAN_ENTITIES_SCHEMA = vol.Schema({
    vol.Optional("entity_filter", default=""): cv.string,
    vol.Optional("batch_size", default=10): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
})

GET_ENTITY_IMPORTANCE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
})

RESET_OVERRIDES_SCHEMA = vol.Schema({
    vol.Required("confirm", default=False): cv.boolean,
})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for HASS AI."""
    
    async def scan_entities_service(call: ServiceCall) -> None:
        """Service to scan entities and analyze their importance."""
        entity_filter = call.data.get("entity_filter", "")
        batch_size = call.data.get("batch_size", 10)
        
        _LOGGER.info(f"Starting entity scan service with filter: '{entity_filter}' and batch size: {batch_size}")
        
        try:
            # Get the first config entry for this integration
            config_entry = None
            for entry in hass.config_entries.async_entries(DOMAIN):
                config_entry = entry
                break
            
            # Get AI configuration
            ai_provider = "OpenAI"
            api_key = None
            if config_entry:
                ai_provider = config_entry.data.get("ai_provider", "conversation")
                api_key = config_entry.data.get("api_key")
            
            all_states = hass.states.async_all()
            
            # Apply entity filter if provided
            if entity_filter:
                filtered_states = [
                    state for state in all_states 
                    if entity_filter in state.entity_id
                ]
            else:
                # Filter out system entities
                filtered_states = [
                    state for state in all_states 
                    if not (
                        state.domain == DOMAIN or 
                        state.entity_id.startswith(f"{DOMAIN}.") or
                        state.domain in ["persistent_notification", "system_log"]
                    )
                ]
            
            results = await get_entities_importance_batched(
                hass, filtered_states, batch_size, ai_provider, api_key
            )
            
            _LOGGER.info(f"Entity scan completed: {len(results)} entities analyzed using {ai_provider}")
            
            # Store results in hass.data for access by other components
            if DOMAIN not in hass.data:
                hass.data[DOMAIN] = {}
            hass.data[DOMAIN]["last_scan_results"] = results
            
        except Exception as e:
            _LOGGER.error(f"Error in scan_entities service: {e}")
            raise ServiceValidationError(f"Failed to scan entities: {e}")
    
    async def get_entity_importance_service(call: ServiceCall) -> None:
        """Service to get importance of a specific entity."""
        entity_id = call.data["entity_id"]
        
        try:
            state = hass.states.get(entity_id)
            if not state:
                raise ServiceValidationError(f"Entity {entity_id} not found")
            
            results = await get_entities_importance_batched(hass, [state], 1)
            
            if results:
                importance_data = results[0]
                _LOGGER.info(f"Entity {entity_id} importance: {importance_data}")
                
                # Store result
                if DOMAIN not in hass.data:
                    hass.data[DOMAIN] = {}
                if "entity_importance" not in hass.data[DOMAIN]:
                    hass.data[DOMAIN]["entity_importance"] = {}
                hass.data[DOMAIN]["entity_importance"][entity_id] = importance_data
            
        except Exception as e:
            _LOGGER.error(f"Error getting entity importance for {entity_id}: {e}")
            raise ServiceValidationError(f"Failed to get entity importance: {e}")
    
    async def reset_overrides_service(call: ServiceCall) -> None:
        """Service to reset all user overrides."""
        confirm = call.data.get("confirm", False)
        
        if not confirm:
            raise ServiceValidationError("Must set 'confirm: true' to reset overrides")
        
        try:
            # Get all config entries for this domain
            for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
                if isinstance(entry_data, dict) and "store" in entry_data:
                    store = entry_data["store"]
                    await store.async_save({})
                    _LOGGER.info(f"Reset overrides for entry {entry_id}")
            
        except Exception as e:
            _LOGGER.error(f"Error resetting overrides: {e}")
            raise ServiceValidationError(f"Failed to reset overrides: {e}")
    
    # Register services
    hass.services.async_register(
        DOMAIN, "scan_entities", scan_entities_service, schema=SCAN_ENTITIES_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "get_entity_importance", get_entity_importance_service, schema=GET_ENTITY_IMPORTANCE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "reset_overrides", reset_overrides_service, schema=RESET_OVERRIDES_SCHEMA
    )
    
    _LOGGER.info("HASS AI services registered successfully")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, "scan_entities")
    hass.services.async_remove(DOMAIN, "get_entity_importance") 
    hass.services.async_remove(DOMAIN, "reset_overrides")
    _LOGGER.info("HASS AI services unloaded")
