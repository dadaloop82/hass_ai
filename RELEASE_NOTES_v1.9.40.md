# HASS AI v1.9.40 Release Notes

## 🔧 Bug Fixes

### Alert Monitor Fixes
- **Fixed storage access error**: Resolved `'HomeAssistant' object has no attribute 'helpers'` error in alert monitor configuration loading/saving
- **Improved conversation agent handling**: Better error handling for `async_get_agent` calls, preventing "object NoneType can't be used in 'await' expression" errors
- **Enhanced threshold generation**: Fixed "Unknown error" issue in automatic alert identification

### Technical Improvements
- Fixed storage import in `alert_monitor.py` by using proper `homeassistant.helpers.storage` import
- Added fallback logic for conversation agent retrieval when no agent is configured
- Improved error logging and exception handling in WebSocket handlers

## 🆕 New Features

### Enhanced Alert Monitoring
- **Detailed Alert Report**: New WebSocket endpoint `hass_ai/get_detailed_alert_report` for comprehensive alert entity analysis
- **Expanded Entity Information**: Detailed reporting includes:
  - Current state and unit of measurement
  - Device class and entity type
  - Threshold configurations
  - Alert level status
  - Entity validity checks
  - Complete state attributes

### Developer Features
- New `get_detailed_alert_report()` method in AlertMonitor class
- Enhanced debugging capabilities for alert entities
- Better visibility into alert system status

## 🔄 Changes
- Version bumped from 1.9.39.16 to 1.9.40
- Improved error messages and logging consistency
- Better WebSocket error handling

## 📋 Summary
This release focuses on fixing critical bugs in the alert monitoring system that were preventing proper functionality, especially around storage access and conversation agent handling. The new detailed reporting feature provides better insight into alert entity status for debugging and monitoring purposes.

## 🔧 For Developers
- Alert monitor now properly imports storage helpers
- Conversation agent handling is more robust with fallback mechanisms
- New detailed reporting endpoint available for frontend integration
