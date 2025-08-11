# HASS AI - Artificial Intelligence for Home Assistant

**HASS AI** transforms your Home Assistant into a truly intelligent environment by providing a powerful, interactive tool to manage how the system understands and prioritizes your devices and entities. It functions as an advanced intelligence layer, allowing you to teach your Home Assistant which entities are most important, which properties to focus on, and which to ignore.

## 🚀 Key Features

- **Automatic AI Analysis**: Intelligent entity evaluation based on type, name, attributes, and historical data
- **Interactive Interface**: Dedicated panel with intuitive controls to manage entity importance  
- **Complete Transparency**: Clear explanations of why each entity received a specific score
- **User Control**: Complete override of AI evaluations to adapt them to your needs
- **Persistence**: All customizations are automatically saved
- **Multilingual Support**: Interface available in Italian and English

## 🏠 How It Works

The system uses Home Assistant's local AI (via conversation agent) to:

1. **Analyze** all system entities
2. **Evaluate** their importance on a 0-5 scale:
   - 0 = Ignore (diagnostic/unnecessary)
   - 1 = Very Low (rarely useful)
   - 2 = Low (occasionally useful) 
   - 3 = Medium (commonly useful)
   - 4 = High (frequently important)
   - 5 = Critical (essential for automations)
3. **Provide** detailed reasons for each evaluation
4. **Allow** complete user customizations

## 📦 Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click "Explore and Download Repositories"
4. Search for "HASS AI"
5. Click "Download"
6. Restart Home Assistant
7. Go to Settings → Devices and Services → Add Integration
8. Search for "HASS AI" and configure it

### Manual Installation

1. Download this repository
2. Copy the `custom_components/hass_ai` folder to your `custom_components` folder
3. Restart Home Assistant
4. Add the integration as described above

## ⚙️ Configuration

### Initial Setup

During configuration you can set:

- **AI Provider**: Currently supports only the integrated conversation agent
- **Scan Interval**: How often to run automatic scans (1-30 days)

### Requirements

- Home Assistant 2023.4.0 or higher
- Configured conversation agent (Google Gemini, OpenAI, etc.)

## 🎯 Usage

### 1. Control Panel

After installation, you'll find a new "HASS AI" panel in the sidebar:

- **Start Scan**: Analyze all system entities
- **Interactive Table**: View and modify entity weights
- **Analysis Log**: See details of AI evaluations

### 2. Available Services

The integration exposes several services usable in automations:

```yaml
# Scan all entities
service: hass_ai.scan_entities
data:
  entity_filter: "sensor."  # Optional: filter by type
  batch_size: 10           # Optional: entities per batch

# Get importance of a single entity
service: hass_ai.get_entity_importance  
data:
  entity_id: "light.living_room"

# Reset all overrides
service: hass_ai.reset_overrides
data:
  confirm: true
```

### 3. Example Automations

```yaml
# Automation for custom periodic scanning
automation:
  - alias: "HASS AI - Weekly Sensor Scan"
    trigger:
      - platform: time
        at: "02:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: hass_ai.scan_entities
        data:
          entity_filter: "sensor."
          batch_size: 15

# Use AI weights in your automations
automation:
  - alias: "Turn Off Unimportant Lights"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion_living_room
        to: "off"
        for: "00:10:00"
    action:
      - service: light.turn_off
        target:
          entity_id: >
            {% set lights = states.light | selectattr('state', 'eq', 'on') | list %}
            {% set unimportant_lights = [] %}
            {% for light in lights %}
              {% if state_attr('hass_ai.' + light.entity_id, 'weight') | int < 3 %}
                {% set unimportant_lights = unimportant_lights + [light.entity_id] %}
              {% endif %}
            {% endfor %}
            {{ unimportant_lights }}
```

## 🔧 API and Integration

### Template Helper

You can use HASS AI data in your templates:

```yaml
# Sensor that counts active critical entities
sensor:
  - platform: template
    sensors:
      critical_entities_active:
        friendly_name: "Critical Entities Active"
        value_template: >
          {% set critical_count = 0 %}
          {% for state in states %}
            {% if state_attr('hass_ai.' + state.entity_id, 'weight') | int >= 4 %}
              {% if state.state not in ['unknown', 'unavailable'] %}
                {% set critical_count = critical_count + 1 %}
              {% endif %}
            {% endif %}
          {% endfor %}
          {{ critical_count }}
```

### Programmatic Access

Data is available via WebSocket API:

```javascript
// Load existing overrides
hass.callWS({type: "hass_ai/load_overrides"})

// Start scan with real-time callbacks
hass.connection.subscribeMessage(
  (message) => console.log(message),
  {type: "hass_ai/scan_entities"}
)

// Save custom overrides
hass.callWS({
  type: "hass_ai/save_overrides", 
  overrides: {
    "light.living_room": {
      enabled: true,
      overall_weight: 5
    }
  }
})
```
