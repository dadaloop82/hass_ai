"""Integrazione HASS AI - Selezione intelligente entità tramite Gemini."""

import logging
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

DOMAIN = "hass_ai"
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Setup base (non tramite config flow)."""
    _LOGGER.info("Inizializzazione HASS AI")

    # Registriamo un dizionario in hass.data per memorizzare dati/istanze
    hass.data.setdefault(DOMAIN, {})

    # Registrazione servizio manuale per avviare analisi entità
    async def handle_identify_important_entities(call):
        _LOGGER.info("Richiesta di analisi entità importante ricevuta (placeholder)")

        # Qui collegheremo il client Gemini e logica
        # Per ora è solo test
        hass.bus.fire(f"{DOMAIN}_entities_identified", {"important_entities": ["light.living_room", "climate.bedroom"]})

    hass.services.async_register(DOMAIN, "identify_important_entities", handle_identify_important_entities)

    return True

async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up hass_ai from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    api_key = entry.data.get(CONF_API_KEY)
    hass.data[DOMAIN]["api_key"] = api_key

    _LOGGER.info("HASS AI configurato con API key.")

    # TODO: inizializza il client Gemini con api_key qui

    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload a config entry."""
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    return True
