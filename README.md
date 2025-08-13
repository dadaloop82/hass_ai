# HASS AI - Artificial Intelligence for Home Assistant

**HASS AI** transforms your Home Assistant into a truly intelligent environment by providing a powerful, interactive tool to manage how the system understands and prioritizes your devices and entities. It functions as an advanced intelligence layer, allowing you to teach your Home Assistant which entities are most important, which properties to focus on, and which to ignore.

## 🚀 Key Features

- **Automatic AI Analysis**: Intelligent entity evaluation based on type, name, attributes, and historical data
- **Three Entity Categories**: Smart classification into DATA, CONTROL, and HEALTH types
- **Health Monitoring**: Proactive detection of device problems, anomalies, and alerts
- **Interactive Interface**: Dedicated panel with intuitive controls and advanced filtering
- **Complete Transparency**: Clear explanations of why each entity received a specific score
- **User Control**: Complete override of AI evaluations to adapt them to your needs
- **Advanced Filtering**: Filter by category, importance weight, and search terms
- **Persistence**: All customizations and correlations automatically saved
- **Multilingual Support**: Interface available in Italian and English

## 🏠 How It Works

The system integrates with **any** Home Assistant conversation agent to provide intelligent analysis:

### 🤖 **Universal AI Support**
- **Google AI (Gemini)** - Advanced reasoning and detailed analysis
- **OpenAI (ChatGPT)** - High-quality natural language processing  
- **Ollama** - Local LLM models for complete privacy
- **Other Providers** - Any conversation agent configured in Home Assistant

### 📊 **Intelligent Analysis Process**
1. **Auto-Detection**: Automatically finds and uses your preferred conversation agent
2. **Analyze** all system entities using your chosen AI
3. **Categorize** entities into three types:
   - 📊 **DATA** - Information providers (sensors, weather, system status)
   - 🎛️ **CONTROL** - User-controllable devices (lights, switches, thermostats)  
   - 🏥 **HEALTH** - Problem indicators (offline devices, low battery, anomalies)
4. **Evaluate** their importance on a 0-5 scale:
   - 0 = Ignore (diagnostic/unnecessary)
   - 1 = Very Low (rarely useful)
   - 2 = Low (occasionally useful) 
   - 3 = Medium (commonly useful)
   - 4 = High (frequently important)
   - 5 = Critical (essential for automations)
5. **Provide** detailed reasons for each evaluation
6. **Allow** complete user customizations and advanced filtering

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

HASS AI uses a **two-step configuration wizard**:

#### 🎯 **Step 1: AI Provider Selection**  
Choose your preferred conversation agent:
- **Auto-Detection** - Let HASS AI find your configured agent automatically
- **Manual Selection** - Choose from all available conversation agents

#### ⚙️ **Step 2: Scan Settings**
Configure analysis parameters:
- **Scan Interval**: How often to run automatic scans (1-30 days)
- **Batch Size**: Number of entities to analyze per batch

### Requirements

- Home Assistant 2023.4.0 or higher
- **Any configured conversation agent**:
  - Google AI (Gemini) 
  - OpenAI (ChatGPT)
  - Ollama (Local LLMs)
  - Anthropic Claude
  - Or any other conversation integration

> 💡 **Note**: HASS AI works with **any** conversation agent - no specific provider required!

#### ⚡ **Token Limits & Performance**

Different conversation agents have different token limits. If you encounter token limit errors:

- **Reduce Batch Size**: Lower the entities per batch (5-8 recommended for most agents)
- **Increase Agent Limits**: Configure higher `max_tokens` in your conversation agent
- **Choose Different Agent**: Some agents like Ollama (local) have more flexible limits

HASS AI will automatically stop scanning and show helpful suggestions if limits are reached.

## 🎯 Usage

### 1. Control Panel

After installation, you'll find a new "HASS AI" panel in the sidebar:

- **Start Scan**: Analyze all system entities with AI categorization
- **Advanced Filtering**: Filter by category (ALL/DATA/CONTROL/HEALTH), importance weight, and search terms
- **Interactive Table**: View and modify entity weights with category badges
- **Health Monitoring**: Dedicated view for device problems and anomalies
- **Correlation Analysis**: Find related entities and their connections
- **Analysis Log**: See details of AI evaluations with explanations

### 2. Entity Categories

The system automatically categorizes entities into three types:

- 📊 **DATA**: Information sources like sensors, weather stations, system monitors
- 🎛️ **CONTROL**: User-controllable devices like lights, switches, thermostats
- 🏥 **HEALTH**: Problem indicators like offline devices, low batteries, connection errors

### 3. Health Monitoring Examples

The AI automatically detects health issues such as:
- 🔋 Battery levels below 20%
- ⚠️ Devices with 'unavailable' or 'unknown' states
- 🌡️ Temperature sensors with anomalous readings
- 📶 Poor WiFi signal strength
- 🔌 Connection timeouts and errors

### 4. Available Services

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

### 5. Example Automations

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

## 🔧 Troubleshooting

### 🚨 **Token Limit Exceeded**

If you see "Token limit exceeded" during scanning:

**Quick Fixes:**
- **Reduce Batch Size**: In HASS AI config, lower entities per batch to 5-8
- **Increase Agent Limits**: Add `max_tokens: 4000` (or higher) to your conversation agent config
- **Use Different Agent**: Try Ollama (local) for more flexible limits

**Example Ollama Config:**
```yaml
# configuration.yaml
conversation:
  - platform: ollama
    model: llama3.1
    max_tokens: 8000  # Increase token limit
    temperature: 0.7
```

### 🤖 **Conversation Agent Issues**

**Problem**: "No conversation agents found"
- Go to Settings → Voice Assistants → Add Agent
- Configure Google AI, OpenAI, or Ollama
- Restart Home Assistant and reconfigure HASS AI

**Problem**: "AI responses are poor quality"
- Try a different conversation agent (Gemini vs ChatGPT vs Ollama)
- Increase `temperature` in agent config for more creative responses
- Check that your agent has sufficient context window

### 📊 **Performance Optimization**

- **Large Systems (>500 entities)**: Use batch size 5-8
- **Small Systems (<100 entities)**: Use batch size 10-15
- **Slow Responses**: Check your conversation agent's response time
- **Memory Issues**: Restart Home Assistant after configuration changes

### 🔄 **Configuration Problems**

**Problem**: Integration won't load
- Check Home Assistant logs for errors
- Ensure conversation component is enabled
- Restart Home Assistant after adding conversation agents

**Problem**: Panel not showing
- Clear browser cache and refresh
- Check that frontend component is enabled
- Verify HASS AI panel is not hidden in sidebar settings
