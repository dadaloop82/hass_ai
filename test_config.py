"""Test configuration for HASS AI integration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.hass_ai.const import DOMAIN


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.states = Mock()
    hass.states.async_all = Mock(return_value=[])
    hass.http = Mock()
    hass.http.async_register_static_paths = AsyncMock()
    hass.config = Mock()
    hass.config.path = Mock(return_value="/config/custom_components/hass_ai/www")
    return hass


@pytest.fixture  
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {"scan_interval": 7}
    entry.options = {}
    entry.async_on_unload = Mock()
    return entry


class TestHassAIConfig:
    """Test HASS AI configuration."""
    
    def test_domain_constant(self):
        """Test that domain constant is correct."""
        assert DOMAIN == "hass_ai"
    
    def test_importance_levels(self):
        """Test importance level constants."""
        from custom_components.hass_ai.const import (
            IMPORTANCE_IGNORE, IMPORTANCE_CRITICAL
        )
        assert IMPORTANCE_IGNORE == 0
        assert IMPORTANCE_CRITICAL == 5


class TestIntelligenceModule:
    """Test intelligence analysis functions."""
    
    @pytest.mark.asyncio
    async def test_empty_states_list(self, mock_hass):
        """Test handling of empty states list."""
        from custom_components.hass_ai.intelligence import get_entities_importance_batched
        
        result = await get_entities_importance_batched(mock_hass, [])
        assert result == []
    
    def test_domain_fallback_mapping(self):
        """Test domain-based importance mapping."""
        from custom_components.hass_ai.intelligence import ENTITY_IMPORTANCE_MAP
        
        assert ENTITY_IMPORTANCE_MAP["alarm_control_panel"] == 5  # Critical
        assert ENTITY_IMPORTANCE_MAP["light"] == 3  # Medium
        assert ENTITY_IMPORTANCE_MAP["sun"] == 1  # Low


class TestConfigFlow:
    """Test configuration flow."""
    
    def test_config_flow_schema(self):
        """Test that config flow has proper schema."""
        from custom_components.hass_ai.config_flow import HassAiConfigFlow
        
        flow = HassAiConfigFlow()
        assert flow.VERSION == 1
        assert flow.domain == DOMAIN


# Mock data for testing
MOCK_ENTITY_STATES = [
    {
        "entity_id": "light.living_room", 
        "domain": "light",
        "name": "Living Room Light",
        "state": "on",
        "attributes": {"friendly_name": "Living Room Light"}
    },
    {
        "entity_id": "sensor.temperature",
        "domain": "sensor", 
        "name": "Temperature Sensor",
        "state": "22.5",
        "attributes": {"friendly_name": "Temperature", "unit_of_measurement": "°C"}
    },
    {
        "entity_id": "alarm_control_panel.home",
        "domain": "alarm_control_panel",
        "name": "Home Security",
        "state": "armed_away", 
        "attributes": {"friendly_name": "Home Security System"}
    }
]


if __name__ == "__main__":
    print("HASS AI Test Configuration")
    print("========================")
    print(f"Domain: {DOMAIN}")
    print("Tests can be run with: python -m pytest")
    print("Mock data available for integration testing")
