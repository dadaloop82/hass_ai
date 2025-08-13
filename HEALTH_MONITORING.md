# 🏥 HASS AI Health Monitoring System

The HASS AI Health Monitoring System provides proactive device health monitoring by automatically detecting problems, anomalies, and critical conditions across your Home Assistant entities.

## 🎯 Overview

Version 1.9.12 introduces intelligent health monitoring that integrates seamlessly with the existing entity analysis system. The AI now categorizes entities into three distinct types, with a dedicated HEALTH category for identifying device problems and system anomalies.

## 📊 Three Entity Categories

### 📊 **DATA** - Information Providers
- **Purpose**: Entities that provide information and measurements
- **Examples**: Sensors, weather stations, system monitors, energy meters
- **Icon**: `mdi:chart-line` (blue)
- **Use Case**: Automation triggers, monitoring, data visualization

### 🎛️ **CONTROL** - User-Controllable Devices  
- **Purpose**: Entities that users can directly control
- **Examples**: Lights, switches, thermostats, covers, fans
- **Icon**: `mdi:tune` (green)
- **Use Case**: Direct user interaction, automation actions

### 🏥 **HEALTH** - Problem Indicators
- **Purpose**: States and attributes indicating device problems or anomalies
- **Examples**: Offline devices, low batteries, connection errors, anomalous readings
- **Icon**: `mdi:heart-pulse` (orange)
- **Use Case**: Proactive monitoring, maintenance alerts, system health

## 🚨 Health Detection Examples

The AI automatically identifies health issues including:

### 🔋 **Battery Issues**
```
sensor.phone_battery (15%) → HEALTH, weight 4 (critical battery level)
sensor.smoke_detector_battery (5%) → HEALTH, weight 5 (critical safety device)
```

### ⚠️ **Device Availability**
```
binary_sensor.door_sensor (unavailable) → HEALTH, weight 5 (offline device)
light.kitchen (unknown) → HEALTH, weight 4 (unknown state)
```

### 🌡️ **Sensor Anomalies**
```
sensor.outdoor_temperature (-40°C) → HEALTH, weight 3 (anomalous reading)
sensor.humidity (150%) → HEALTH, weight 3 (impossible value)
```

### � **Connectivity Problems**
```
sensor.wifi_signal (-95dBm) → HEALTH, weight 2 (very weak signal)
device_tracker.phone (not_home for 30 days) → HEALTH, weight 3 (possible issue)
```

## 🎛️ User Interface Features

### **Category Filtering**
- Filter entities by category: `ALL`, `DATA`, `CONTROL`, `HEALTH`
- Persistent filter preferences saved automatically
- Quick access to health problems with HEALTH-only view

### **Visual Indicators**
- Color-coded category badges for instant recognition
- Orange HEALTH badges with heart-pulse icons
- Weight-based sorting for priority management

### **Advanced Search**
- Multi-criteria filtering: category + weight + search terms
- Real-time filtering with immediate results
- Saved filter preferences across sessions

## 🧠 AI Intelligence Features

### **Smart Pattern Recognition**
The AI specifically looks for:
- States: `unavailable`, `unknown`, `timeout`, `error`
- Battery levels below 20%
- Temperature readings outside normal ranges
- Signal strength below acceptable thresholds
- Devices not reporting for extended periods

### **Contextual Weighting**
Health issues are weighted based on criticality:
- **Weight 5**: Critical safety devices offline (smoke detectors, alarms)
- **Weight 4**: Important devices with severe issues (low battery, offline)
- **Weight 3**: Moderate issues requiring attention (weak signals, anomalies)
- **Weight 2**: Minor issues or early warnings

### **Multilingual Support**
Health monitoring works in both Italian and English with localized:
- Category names and descriptions
- Health issue detection
- User interface elements

## 🔧 Technical Implementation

### **Integration with Existing System**
- Health monitoring is integrated into the standard entity scanning process
- No additional configuration required
- Works with all supported AI providers (Google AI, OpenAI, Ollama, etc.)

### **Enhanced AI Prompts**
Prompts specifically instruct the AI to:
```
"For HEALTH: look for 'unavailable', 'unknown' states, low battery (<20%), 
anomalous temperatures, connection errors, offline devices, weak signals"
```

### **JSON Response Format**
```json
{
  "entity_id": "sensor.phone_battery",
  "rating": 4,
  "reason": "Battery level at 15% requires attention",
  "category": "HEALTH",
  "management_type": "USER"
}
```

## 🚀 Getting Started

1. **Update to v1.9.12**: Ensure you have the latest version installed
2. **Run Entity Scan**: Start a new scan to categorize your entities
3. **Filter by HEALTH**: Use the category filter to view only health issues
4. **Monitor & Act**: Address identified problems proactively

The health monitoring system transforms reactive troubleshooting into proactive device management, helping you maintain a healthy and reliable smart home environment.

## 💡 Future Enhancements

Planned improvements include:
- Automated health alerts and notifications
- Historical health trending and analytics
- Integration with Home Assistant's alert system
- Custom health threshold configuration
- Health report generation and scheduling
