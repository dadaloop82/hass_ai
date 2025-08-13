# 🔍 HASS AI Entity Enhancement System

## 🎯 Overview

The Entity Enhancement System automatically detects entities that can benefit from AI interpretation services and provides smart integration suggestions or automatic enhancement.

## 🏗️ Architecture

### **Enhancement Detection Engine**
```python
# intelligence.py - Enhanced entity detection
ENHANCEMENT_PATTERNS = {
    "vision": {
        "domains": ["camera"],
        "attributes": ["entity_picture", "stream_source"],
        "services": ["openai_vision", "google_vision", "frigate"],
        "output_type": "description_sensor"
    },
    "audio": {
        "domains": ["media_player"],
        "attributes": ["media_title", "media_artist", "source"],
        "services": ["shazam", "whisper", "spotify_analysis"],
        "output_type": "audio_analysis_sensor"
    },
    "analytics": {
        "domains": ["sensor"],
        "patterns": ["power_", "energy_", "consumption_"],
        "services": ["local_ml", "time_series", "forecast"],
        "output_type": "analytics_sensor"
    }
}
```

### **Service Discovery & Integration**
```python
class EnhancementManager:
    def detect_available_services(self):
        """Detect installed enhancement services"""
        available = {}
        
        # Check for OpenAI Vision
        if self.hass.services.has_service("openai_conversation", "process"):
            available["vision"] = "openai_vision"
            
        # Check for Frigate
        if self.hass.services.has_service("frigate", "get_snapshot"):
            available["vision"] = "frigate"
            
        # Check for custom integrations
        for domain in self.hass.services.async_services():
            if "vision" in domain or "ml" in domain:
                available["custom"] = domain
                
        return available
    
    async def suggest_enhancements(self, entity_id: str):
        """Suggest enhancement services for entity"""
        domain = entity_id.split(".")[0]
        available_services = self.detect_available_services()
        
        suggestions = []
        for enhancement_type, config in ENHANCEMENT_PATTERNS.items():
            if domain in config["domains"]:
                for service in config["services"]:
                    if service in available_services:
                        suggestions.append({
                            "type": enhancement_type,
                            "service": service,
                            "description": f"Add {enhancement_type} analysis for {entity_id}",
                            "auto_setup": True
                        })
                    else:
                        suggestions.append({
                            "type": enhancement_type,  
                            "service": service,
                            "description": f"Install {service} for {enhancement_type} analysis",
                            "auto_setup": False,
                            "install_guide": f"https://github.com/example/{service}"
                        })
        
        return suggestions
```

## 🎨 Frontend Enhancement UI

### **Enhanced Entity Badge**
```javascript
// New ENHANCED category with special indicators
getCategoryInfo = (category, hasEnhancements) => {
  switch (category) {
    case 'ENHANCED':
      return { 
        icon: 'mdi:brain', 
        color: '#9C27B0', 
        label: isItalian ? 'Potenziabile' : 'Enhanced',
        badge: hasEnhancements ? '✨' : '⚡'
      };
  }
};
```

### **Enhancement Panel**
```html
<!-- Enhancement suggestions panel -->
<div class="enhancement-panel">
  <h3>🔍 Available Enhancements</h3>
  
  <div class="enhancement-item">
    <ha-icon icon="mdi:camera-iris"></ha-icon>
    <div class="enhancement-info">
      <h4>Camera Scene Analysis</h4>
      <p>Add AI vision to describe camera scenes</p>
      <div class="service-status">
        OpenAI Vision: ✅ Available | Frigate: ❌ Not installed
      </div>
    </div>
    <ha-button @click=${this._setupEnhancement}>Setup</ha-button>
  </div>
  
  <div class="enhancement-item">
    <ha-icon icon="mdi:waveform"></ha-icon>
    <div class="enhancement-info">
      <h4>Audio Recognition</h4>
      <p>Identify music and analyze audio content</p>
      <div class="service-status">
        Shazam: ❌ Install needed | Whisper: ⚡ Auto-installable
      </div>
    </div>
    <ha-button @click=${this._suggestInstall}>Suggest Install</ha-button>
  </div>
</div>
```

## 🚀 Auto-Enhancement Examples

### **Camera Vision Enhancement**
```yaml
# Auto-created by HASS AI
- sensor:
    name: "Living Room Camera Scene"
    unique_id: "camera_living_room_enhanced"
    state: >
      {% set snapshot = states.camera.living_room.attributes.entity_picture %}
      {{ state_attr('sensor.openai_vision_response', 'description') | default('No analysis yet') }}
    attributes:
      objects_detected: >
        {{ state_attr('sensor.openai_vision_response', 'objects') }}
      confidence: >
        {{ state_attr('sensor.openai_vision_response', 'confidence') }}
      last_analysis: >
        {{ states('sensor.openai_vision_response') }}

- automation:
    alias: "Auto-analyze Living Room Camera"
    trigger:
      - platform: state
        entity_id: camera.living_room
        attribute: entity_picture
    action:
      - service: openai_conversation.process
        data:
          message: "Describe what you see in this camera image. List any objects, people, or activities."
          image_path: "{{ trigger.to_state.attributes.entity_picture }}"
        target:
          entity_id: sensor.openai_vision_response
```

### **Media Player Enhancement**
```yaml
# Auto-created enhancement for media analysis
- sensor:
    name: "Current Music Analysis"
    unique_id: "media_player_enhanced"
    state: >
      {% if states('media_player.spotify') not in ['off', 'unavailable'] %}
        {{ state_attr('media_player.spotify', 'media_title') }} by {{ state_attr('media_player.spotify', 'media_artist') }}
      {% else %}
        No music playing
      {% endif %}
    attributes:
      genre: >
        {{ state_attr('sensor.spotify_analysis', 'genre') | default('Unknown') }}
      mood: >
        {{ state_attr('sensor.spotify_analysis', 'mood') | default('Unknown') }}
      energy_level: >
        {{ state_attr('sensor.spotify_analysis', 'energy') | default(0) }}
```

## 🔧 Implementation Strategy

### **Phase 1: Detection & Suggestion**
1. Add ENHANCED category to entity classification
2. Create enhancement detection logic
3. Build suggestion UI in frontend
4. Add service discovery functionality

### **Phase 2: Auto-Enhancement**
1. Auto-create helper sensors for enhanced entities
2. Generate automation templates
3. Service integration helpers
4. Configuration validation

### **Phase 3: Marketplace Integration**
1. Integration with HACS for service installation
2. Pre-built enhancement packages
3. Community enhancement sharing
4. Service compatibility matrix

## 💡 Benefits

- **Automatic Discovery**: Find enhanceable entities automatically
- **Smart Suggestions**: Only suggest services that make sense
- **Progressive Enhancement**: Work without services, better with them
- **User-Friendly**: Guide users through installation and setup
- **Extensible**: Easy to add new enhancement types

This system transforms basic entities into intelligent, self-describing components while gracefully handling missing services and guiding users toward powerful AI integrations.
