#!/usr/bin/env python3
"""
Test script per verificare che le correzioni alla categorizzazione funzionino correttamente.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components', 'hass_ai'))

from intelligence import _auto_categorize_entity, _create_fallback_result
from homeassistant.core import State
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE

def create_mock_state(entity_id: str, domain: str, state: str, attributes: dict = None):
    """Create a mock State object for testing."""
    if attributes is None:
        attributes = {}
    
    # Mock State object
    class MockState:
        def __init__(self, entity_id, domain, state, attributes):
            self.entity_id = entity_id
            self.domain = domain
            self.state = state
            self.attributes = attributes
    
    return MockState(entity_id, domain, state, attributes)

def test_auto_categorization():
    """Test che la categorizzazione automatica funzioni correttamente."""
    print("🧪 Testing auto-categorization...")
    
    test_cases = [
        # (entity_id, domain, state, attributes, expected_categories, expected_management)
        ("sensor.battery_level", "sensor", "85", {}, ["DATA", "ALERTS"], "USER"),
        ("sensor.temperature", "sensor", "22.5", {}, ["DATA", "ALERTS"], "USER"),
        ("light.living_room", "light", "on", {}, ["CONTROL"], "USER"),
        ("switch.kitchen", "switch", "off", {}, ["CONTROL"], "USER"),
        ("conversation.chatgpt", "conversation", "idle", {}, ["CONTROL"], "SERVICE"),
        ("update.home_assistant", "update", "off", {}, ["DATA", "ALERTS"], "SERVICE"),
        ("sensor.heart_rate", "sensor", "72", {}, ["DATA", "ALERTS"], "USER"),
        ("binary_sensor.motion", "binary_sensor", "off", {}, ["DATA"], "USER"),
        ("camera.front_door", "camera", "streaming", {}, ["DATA"], "SERVICE"),
        ("sun.sun", "sun", "above_horizon", {}, ["DATA"], "USER"),
        ("sensor.unavailable_sensor", "sensor", STATE_UNAVAILABLE, {}, ["ALERTS"], "SERVICE"),
    ]
    
    for entity_id, domain, state, attributes, expected_categories, expected_management in test_cases:
        mock_state = create_mock_state(entity_id, domain, state, attributes)
        categories, management_type = _auto_categorize_entity(mock_state)
        
        print(f"  📋 {entity_id}: {categories} | {management_type}")
        
        if categories != expected_categories:
            print(f"    ❌ ERRORE categorie! Atteso: {expected_categories}, Ottenuto: {categories}")
        elif management_type != expected_management:
            print(f"    ❌ ERRORE management! Atteso: {expected_management}, Ottenuto: {management_type}")
        else:
            print(f"    ✅ OK")

def test_fallback_result():
    """Test che _create_fallback_result usi categorie multiple."""
    print("\n🧪 Testing fallback result creation...")
    
    test_cases = [
        ("sensor.battery_phone", "sensor", "90", {}),
        ("light.bedroom", "light", "on", {}),
        ("conversation.assistant", "conversation", "idle", {}),
        ("update.system", "update", "off", {}),
    ]
    
    for entity_id, domain, state_value, attributes in test_cases:
        mock_state = create_mock_state(entity_id, domain, state_value, attributes)
        result = _create_fallback_result(entity_id, 1, "test_fallback", mock_state)
        
        print(f"  📋 {entity_id}: {result['category']} | {result['management_type']}")
        
        if isinstance(result['category'], list) and len(result['category']) > 0:
            if "UNKNOWN" in result['category']:
                print(f"    ❌ ERRORE: Trovato UNKNOWN nelle categorie!")
            else:
                print(f"    ✅ OK - Nessun UNKNOWN")
        else:
            print(f"    ❌ ERRORE: Categoria non è una lista valida!")

if __name__ == "__main__":
    print("🔧 Test per verificare le correzioni alla categorizzazione HASS AI")
    print("=" * 60)
    
    test_auto_categorization()
    test_fallback_result()
    
    print("\n✅ Test completati! Verifica che non ci siano errori sopra.")
