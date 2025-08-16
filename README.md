# HASS AI - Advanced Entity Analysis and Automation Assistant

**Version 1.9.38** | *Enhanced AI-Powered Entity Management for Home Assistant*

HASS AI is a sophisticated Home Assistant custom component that leverages artificial intelligence to analyze, categorize, and optimize entity management across your smart home ecosystem.

## ✨ Key Features

### 🔍 **Multi-Mode AI Analysis**
- **Importance Analysis**: Evaluate entity relevance for automations and control
- **Alert Detection**: Identify problems, offline devices, and critical alerts
- **Enhancement Opportunities**: Discover entities that can benefit from AI services

### 🚨 **Intelligent Alert Monitoring System** ⭐ **NEW!**
- **Three-Level Thresholds**: WARNING, ALERT, CRITICAL with configurable values
- **Weight-Based Monitoring**: High-priority entities checked every 30 seconds, low-priority every 30 minutes
- **AI-Generated Notifications**: Smart, contextual alert messages created by AI
- **Cumulative Alerts**: Groups multiple alerts into concise, actionable notifications
- **Flexible Notification Services**: Choose from any available Home Assistant notification service
- **Automatic Throttling**: Prevents notification spam with intelligent timing
- **Real-Time Status Dashboard**: Visual monitoring of all alert entities

### 🔧 **Smart Alert Configuration**
- **Auto-Detection**: Automatically identifies alert thresholds based on entity type and current values
- **Manual Override**: Customize thresholds for any monitored entity
- **Entity Type Recognition**: Supports sensors, binary sensors, switches, and more
- **Threshold Examples**: Battery < 10% (CRITICAL), Temperature > 30°C (ALERT), Motion detected (WARNING)
- **Visual Status Indicators**: Color-coded badges show current alert levels

### ⚡ **Enhanced Entity Services**
- **Vision Analysis**: AI interpretation for camera feeds
- **Audio Processing**: Content analysis for media players
- **Advanced Analytics**: Predictive insights for sensors
- **Weather Enhancement**: Extended forecasting capabilities

### 📊 **Real-Time Monitoring**
- **Live Token Tracking**: Monitor AI usage and costs in real-time
- **Progress Indicators**: Visual feedback during analysis
- **Batch Processing**: Efficient handling of large entity sets
- **Performance Metrics**: Detailed usage statistics

### 🔗 **Intelligent Correlations**
- **Entity Relationships**: Discover connections between devices
- **Automation Suggestions**: AI-powered recommendations
- **Pattern Recognition**: Identify usage patterns and dependencies
- **Smart Grouping**: Automatic entity categorization

## 🎯 Analysis Categories

### 📈 **DATA** - Sensor Entities
Information providers that feed data to your system:
- Temperature sensors, humidity monitors
- Energy meters, motion detectors  
- Environmental sensors, status indicators

### 🎛️ **CONTROL** - Interactive Entities
Devices you actively control and automate:
- Lights, switches, climate systems
- Media players, covers, locks
- Smart appliances, security devices

### 🚨 **ALERTS** - Problem Detection
Entities requiring immediate attention:
- Offline devices, connectivity issues
- Low battery warnings (< 20%)
- System errors and malfunctions
- Security alerts and alarms

### ⚡ **ENHANCED** - AI Opportunities
Entities that can benefit from additional AI services:
- Cameras → Vision analysis and object detection
- Media players → Audio content recognition
- Sensors → Predictive analytics and forecasting
- Weather → Enhanced insights and recommendations

## 🚀 Getting Started

### Installation
1. Download and place in `custom_components/hass_ai/`
2. Restart Home Assistant
3. Configure via Settings → Integrations → Add Integration → HASS AI

### Basic Usage
1. **Choose Analysis Type**: Select from Importance, Alerts, or Enhanced
2. **Run Analysis**: Click "Start Analysis" to begin AI evaluation
3. **Review Results**: Browse categorized entities with AI insights
4. **Customize Settings**: Adjust weights and alert thresholds
5. **Find Correlations**: Discover entity relationships and dependencies

## 🔔 Alert Monitoring System

### Overview
The intelligent alert monitoring system continuously watches entities with the ALERTS category and sends notifications when thresholds are exceeded.

### Configuration Steps
1. **Run AI Analysis**: First scan your entities to identify alert-worthy devices
2. **Open Alert Configuration**: Click "🔔 Configure Alert Notifications" button
3. **Choose Notification Service**: Select from available Home Assistant notification services
4. **Review Alert Entities**: See which entities are monitored and their current status
5. **Customize Thresholds**: Adjust WARNING/ALERT/CRITICAL levels as needed

### Alert Levels
- **WARNING** ⚠️: Monitor situation (e.g., battery < 20%, temperature > 25°C)
- **ALERT** 🚨: Requires attention (e.g., battery < 10%, temperature > 30°C) 
- **CRITICAL** 🔥: Immediate action required (e.g., battery < 5%, temperature > 35°C)

### Monitoring Frequency
- **Weight 5 entities**: Checked every 30 seconds (critical devices)
- **Weight 4 entities**: Checked every ~7 minutes
- **Weight 3 entities**: Checked every ~15 minutes  
- **Weight 2 entities**: Checked every ~22 minutes
- **Weight 1 entities**: Checked every 30 minutes (low priority)

### AI-Generated Notifications
When alerts are detected, the system:
1. **Groups Related Alerts**: Combines multiple alerts into one notification
2. **Generates Smart Message**: AI creates contextual, actionable notifications
3. **Prevents Spam**: Throttles notifications based on alert level
4. **Provides Actions**: Includes suggested next steps

### Example Alert Message
```
🔥 2 CRITICAL and 1 ALERT detected!
• Living room temperature: 35°C (CRITICAL)
• Motion sensor battery: 3% (CRITICAL)
• Bathroom window open: 2h (ALERT)
Check your home immediately.
```

### Supported Entity Types
- **Sensors**: Temperature, humidity, battery, CO2, pressure
- **Binary Sensors**: Doors, windows, motion, smoke, gas detection
- **Switches**: Security systems, emergency controls
- **Lights**: Emergency lighting systems

## 🔧 Advanced Features

### Token Management
- Real-time usage tracking with cost estimation
- Optimized prompts to minimize token consumption
- Batch processing with dynamic size adjustment
- Support for multiple AI providers (OpenAI, Google AI, Local)

### Enhancement Detection
The system automatically identifies entities that could benefit from AI-powered enhancements:

- **Vision-Enabled Cameras**: Snapshot analysis, object detection, scene description
- **Audio-Capable Media**: Content recognition, mood detection, source identification  
- **Analytics-Ready Sensors**: Trend analysis, predictive modeling, anomaly detection
- **Weather Intelligence**: Extended forecasts, condition analysis, impact assessment

### Correlation Discovery
AI-powered relationship mapping between entities:
- **Functional Correlations**: Devices that work together
- **Spatial Correlations**: Entities in the same location
- **Temporal Correlations**: Time-based usage patterns
- **Logical Correlations**: Cause-and-effect relationships

## 🌐 Multi-Language Support

Full interface localization available in:
- **English** - Complete feature set
- **Italian** - Native Italian interface and descriptions
- Easy extension to additional languages

## 📈 Performance & Optimization

- **Ultra-Compact Prompts**: 85% reduction in token usage
- **Intelligent Batching**: Dynamic sizing based on response limits
- **Persistent Storage**: Results cached for quick access
- **Progressive Enhancement**: Features activate based on available services

## 🔒 Privacy & Security

- **Local Processing Option**: Use local AI models when available
- **Secure API Integration**: Encrypted communication with AI providers
- **Data Minimization**: Only essential entity information is processed
- **User Control**: Full customization of analysis scope and depth

## 📊 Analysis Types Explained

### Importance Analysis
Evaluates how critical each entity is for your home automation:
- Scores entities 0-5 based on automation relevance
- Considers entity type, usage patterns, and dependencies
- Helps prioritize which entities to focus on for automations

### Alert Detection
Specifically designed to find problems and issues:
- Identifies offline or unreachable devices
- Detects low battery levels (< 20%)
- Finds entities with error states or malfunctions
- Prioritizes by severity level (Medium/Severe/Critical)

### Enhancement Opportunities
Discovers entities that could benefit from AI services:
- No AI tokens consumed (pure pattern matching)
- Suggests specific AI enhancements for each entity type
- Provides confidence scores for enhancement potential
- Links to relevant AI services and integrations

## 🎛️ User Interface Features

### Analysis Type Selector
Choose between three analysis modes:
- **📊 Importance**: Rate entities by automation value
- **🚨 Alerts**: Find problems and issues
- **⚡ Enhanced**: Discover AI enhancement opportunities

### Smart Filtering
- **Category Filter**: DATA, CONTROL, ALERTS, ENHANCED
- **Weight Filter**: Show only entities above minimum importance
- **Search**: Find specific entities by name or ID
- **Real-time Updates**: Live filtering as you type

### Entity Management
- **Toggle Enable/Disable**: Control which entities are active
- **Adjust Weights**: Override AI ratings with your preferences
- **Alert Thresholds**: Customize notification levels for ALERTS
- **Correlation View**: See relationships between entities

### Progress Tracking
- **Real-time Updates**: Live progress during analysis
- **Token Monitoring**: Track AI usage and estimated costs
- **Batch Information**: See processing details and statistics
- **Error Handling**: Graceful handling of rate limits and errors

## 🔧 Configuration Options

### AI Provider Setup
Support for multiple AI providers:
- **OpenAI**: GPT-3.5/GPT-4 with API key
- **Google AI**: Gemini models with API key  
- **Local Models**: Ollama or other local conversation agents
- **Auto-Detection**: Automatically uses available agents

### Analysis Settings
- **Batch Size**: Adjust for optimal performance (1-50 entities)
- **Language**: Full localization (English/Italian)
- **Token Limits**: Automatic optimization for rate limits
- **Storage**: Persistent results and user customizations

### Alert Configuration
- **Default Thresholds**: System-wide alert level defaults
- **Per-Entity Settings**: Customize alert levels individually
- **Notification Integration**: Connect with Home Assistant notifications
- **Severity Icons**: Visual indicators for alert levels

## 🚀 Use Cases

### Home Automation Optimization
- Identify which entities are most valuable for automations
- Discover hidden relationships between devices
- Optimize entity organization and reduce noise

### Proactive Monitoring
- Catch device problems before they cause issues  
- Monitor battery levels across all wireless devices
- Track connectivity and performance metrics

### AI Integration Planning
- Find entities that could benefit from vision analysis
- Identify audio devices ready for content recognition
- Discover sensors suitable for predictive analytics

### System Health Management
- Maintain awareness of device status across your network
- Prioritize maintenance based on criticality levels
- Automate responses to different alert severities

---

*Transform your Home Assistant setup with intelligent entity management and AI-powered insights. From basic importance analysis to advanced enhancement detection, HASS AI helps you build a smarter, more efficient home automation system.*

## 📄 Documentation

- **[Installation Guide](INSTALLATION.md)** - Detailed setup instructions
- **[Features Overview](FEATURES.md)** - Complete feature documentation  
- **[Developer Guide](DEVELOPER.md)** - Technical implementation details
- **[API Reference](API_KEYS.md)** - AI provider configuration
- **[Enhancement System](ENTITY_ENHANCEMENT.md)** - AI service integration guide

## 🆕 What's New in v1.9.15

- **ALERTS Category**: Renamed from HEALTH for clearer purpose
- **Alert Thresholds**: Three-level customizable alert system
- **Enhanced Analysis**: AI-powered entity enhancement detection
- **Real-time Token Tracking**: Live monitoring of AI usage
- **Improved UI**: Better organization and visual indicators
- **Performance Optimization**: 85% reduction in token usage
