# HASS AI Alert Monitoring System Documentation

## Overview

The HASS AI Alert Monitoring System provides intelligent, automated monitoring of critical entities in your Home Assistant setup with AI-generated notifications.

## Key Features

### 🚨 Intelligent Alert Detection
- **Automatic Threshold Detection**: AI analyzes entity types and current values to suggest appropriate alert levels
- **Multi-Level Monitoring**: WARNING, ALERT, and CRITICAL levels with different response times
- **Entity Type Awareness**: Smart defaults for sensors, binary sensors, switches, and lights

### 🔔 Smart Notifications
- **AI-Generated Messages**: Context-aware notifications created by your AI assistant
- **Cumulative Alerts**: Multiple alerts grouped into single, actionable messages
- **Configurable Services**: Works with any Home Assistant notification service
- **Throttling Protection**: Prevents notification spam with intelligent timing

### ⚡ Weight-Based Monitoring
- **Priority-Based Checking**: Higher weight entities monitored more frequently
- **Efficient Resource Usage**: Optimized checking intervals based on entity importance
- **Real-Time Updates**: Immediate status updates in the dashboard

## Alert Configuration

### Entity Categories Monitored
Only entities with the **ALERTS** category are automatically monitored. These are identified during AI analysis.

### Alert Levels

#### WARNING ⚠️
- **Purpose**: Early warning for developing issues
- **Throttling**: 60 minutes between notifications
- **Examples**: 
  - Battery level < 20%
  - Temperature > 25°C
  - Door open > 1 hour

#### ALERT 🚨  
- **Purpose**: Issues requiring attention
- **Throttling**: 30 minutes between notifications
- **Examples**:
  - Battery level < 10%
  - Temperature > 30°C
  - Motion detected in secure area

#### CRITICAL 🔥
- **Purpose**: Urgent issues needing immediate action
- **Throttling**: 10 minutes between notifications
- **Examples**:
  - Battery level < 5%
  - Temperature > 35°C
  - Smoke/gas detected

### Monitoring Intervals

The system calculates monitoring intervals based on entity weight:

| Weight | Check Interval | Use Case |
|--------|---------------|----------|
| 5 | 30 seconds | Critical safety devices |
| 4 | ~7 minutes | Important automation devices |
| 3 | ~15 minutes | Standard monitoring devices |
| 2 | ~22 minutes | Secondary devices |
| 1 | 30 minutes | Low-priority devices |

## Threshold Configuration

### Automatic Detection
The system automatically detects appropriate thresholds based on:

1. **Entity Domain**: sensor, binary_sensor, switch, light
2. **Entity Type**: Detected from entity name patterns
3. **Current Value**: Uses current state as baseline for numeric sensors

### Supported Entity Types

#### Sensors
- **Temperature**: Default thresholds 25°C/30°C/35°C (WARNING/ALERT/CRITICAL)
- **Humidity**: Default thresholds 70%/80%/90%
- **Battery**: Default thresholds 20%/10%/5%
- **CO2**: Default thresholds 1000/1500/2000 ppm
- **Pressure**: Default thresholds 980/960/940 hPa

#### Binary Sensors
- **Doors/Windows**: Alert when open (security concern)
- **Motion**: Alert when detected (security zones)
- **Smoke/Gas**: Always critical when detected

#### Switches/Lights
- **Security Systems**: Alert when disabled when should be enabled
- **Emergency Lighting**: Alert when off during emergencies

### Manual Configuration
Users can customize thresholds through the web interface:

1. Open HASS AI panel
2. Click "🔔 Configure Alert Notifications"
3. Review detected alert entities
4. Modify thresholds as needed

## Notification Configuration

### Service Selection
Choose from any available Home Assistant notification service:
- `notify.notify` (default)
- `notify.mobile_app_*` (mobile devices)
- `notify.telegram`
- `notify.discord`
- Custom notification integrations

### Message Generation
The AI creates contextual messages including:
- **Alert Summary**: Number and severity of alerts
- **Entity Details**: Which devices triggered alerts
- **Current Values**: Actual readings that exceeded thresholds
- **Suggested Actions**: What to do about the alerts

### Example AI-Generated Messages

#### Italian
```
🔥 2 CRITICAL e 1 ALERT rilevati!
• Temperatura soggiorno: 35°C (CRITICAL)
• Batteria sensore movimento: 3% (CRITICAL)
• Finestra bagno aperta: 2h (ALERT)
Controlla immediatamente la tua casa.
```

#### English
```
🔥 2 CRITICAL and 1 ALERT detected!
• Living room temperature: 35°C (CRITICAL)
• Motion sensor battery: 3% (CRITICAL)
• Bathroom window open: 2h (ALERT)
Check your home immediately.
```

## Integration with HASS AI

### Workflow
1. **AI Analysis**: Run entity analysis to identify ALERTS category entities
2. **Automatic Setup**: Alert monitor configures thresholds for detected entities
3. **Continuous Monitoring**: Background monitoring starts automatically
4. **Smart Notifications**: AI generates and sends alerts as needed

### Status Dashboard
The alert configuration panel shows:
- **Monitoring Status**: Whether system is active
- **Monitored Entities**: Count of entities being watched
- **Active Alerts**: Current alerts requiring attention
- **Entity Details**: Individual entity status and thresholds

## Best Practices

### Entity Selection
- Focus on safety-critical devices (smoke, gas, security)
- Include battery-powered devices for maintenance alerts
- Monitor environmental sensors in critical areas
- Include door/window sensors for security

### Threshold Tuning
- Start with default thresholds and adjust based on experience
- Consider seasonal variations for temperature sensors
- Set battery thresholds based on device criticality
- Account for normal usage patterns

### Notification Management
- Choose notification services appropriate for alert urgency
- Test notification delivery before relying on alerts
- Consider multiple notification methods for critical alerts
- Review and adjust throttling if needed

## Troubleshooting

### No Alerts Detected
- Ensure entities have ALERTS category from AI analysis
- Check that thresholds are properly configured
- Verify entity states are readable

### Missing Notifications
- Verify notification service is properly configured
- Check Home Assistant logs for errors
- Ensure AI conversation agent is available for message generation

### Too Many Notifications
- Adjust entity weights to reduce monitoring frequency
- Increase alert thresholds if too sensitive
- Review throttling settings

## API Reference

### WebSocket Commands

#### Get Alert Status
```javascript
{
  "type": "hass_ai/get_alert_status"
}
```

#### Configure Alert Service
```javascript
{
  "type": "hass_ai/configure_alert_service",
  "notification_service": "notify.mobile_app_phone",
  "entity_thresholds": {
    "sensor.temperature": {
      "WARNING": 26,
      "ALERT": 31,
      "CRITICAL": 36
    }
  }
}
```

### Storage Keys
- `hass_ai_alert_config`: Alert configuration and monitored entities
- `hass_ai_correlations`: Entity correlations (used for smart grouping)

## Version History

### v1.9.38
- Initial release of intelligent alert monitoring system
- AI-generated notification messages
- Weight-based monitoring intervals
- Configurable notification services
- Real-time status dashboard
