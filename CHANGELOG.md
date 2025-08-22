# Changelog

All notable changes to this project will be documented in this file.

## [1.9.53] - 2025-08-22

### 🔧 **Critical Bug Fixes & User Experience Improvements**
- **FIXED: Area Display Issues**: Resolved "(fallback)" label appearing even for correctly detected areas
- **FIXED: Auto-Threshold Generation**: Prevented incorrect update-related thresholds for configuration entities
- **ENHANCED: Complete AI Logging Integration**: Comprehensive logging system with organized daily structure

#### Technical Improvements
- **Enhanced Result Structure**: Area information properly included in AI analysis results and fallback results
- **Smart Entity Filtering**: Improved logic to distinguish between real update entities and configuration switches (`auto_update_enabled`, `_enabled`, `_config`, `_setting`)
- **Robust Area Detection**: New `_get_entity_area()` function for accurate area information from Home Assistant registries
- **WebSocket API Enhancements**: Enhanced log access with date filtering and available dates support
- **Performance Tracking**: Detailed statistics on token usage, batch processing, and analysis completion

#### User Experience
- ✅ Clean area display: `📍 Soggiorno` instead of `📍 Soggiorno (fallback)`
- ✅ Accurate automatic thresholds only for relevant entities (excludes configuration switches)
- ✅ Complete AI interaction visibility through structured daily logging
- ✅ Seamless update with no configuration changes required

#### File Structure
```
logs/
├── README.md                     # Comprehensive documentation
└── YYYY-MM-DD/                  # Daily organized directories
    ├── prompts.json             # AI prompts with full context
    ├── responses.json           # AI responses with results
    ├── errors.json              # Error logs with context
    └── info.json                # Analysis tracking & statistics
```

## [1.9.52] - 2025-08-22

### 🔍 **Comprehensive AI Logging System**
- **NEW: Complete AI Interaction Logging**: Comprehensive logging system tracks all AI interactions with organized structure
- **Daily Directory Organization**: Logs organized by date in `/logs/YYYY-MM-DD/` directories for easy navigation
- **Separate File Types**: Different JSON files for different log types (prompts.json, responses.json, errors.json, info.json)
- **WebSocket API Integration**: Enhanced WebSocket API with date filtering and available dates retrieval
- **Real-Time Analysis Tracking**: Detailed logging of analysis start, batch processing, completion with statistics
- **Token Usage Monitoring**: Complete tracking of token consumption, character counts, and performance metrics

#### Technical Improvements
- **AILogger Class**: Robust logging class with daily directory management and type-separated file handling
- **Enhanced WebSocket Commands**: Updated `handle_get_ai_logs` with optional date parameter and `available_dates` support
- **Intelligence Integration**: Complete integration with AI analysis pipeline for comprehensive tracking
- **Structured Log Format**: Standardized JSON format with timestamps, messages, and structured data
- **Error Handling**: Robust error logging with context information and fallback mechanisms
- **Performance Tracking**: Detailed statistics on batch processing, token usage, and analysis completion

#### File Structure
```
logs/
├── README.md                     # Documentation of logging system
└── YYYY-MM-DD/                  # Daily directories
    ├── prompts.json             # AI prompts with context
    ├── responses.json           # AI responses with results
    ├── errors.json              # Error logs with context
    └── info.json                # General information logs
```

## [1.9.39] - 2025-01-16

### 🎯 **Real-Time Filtered Alert Monitoring**
- **NEW: Dynamic Alert Filtering**: Alert monitoring now respects frontend filter settings in real-time
- **Weight-Based Alert Filtering**: Only entities with weight ≥ minimum weight threshold are monitored for alerts
- **Category-Based Alert Filtering**: Alert monitoring considers category filter selection (ALL, ALERTS, etc.)
- **Real-Time Synchronization**: Alert counts update instantly when user changes filters
- **Enhanced Debug Panel**: Visual debugging section shows only currently filtered ALERTS entities
- **Backend Integration**: New WebSocket handler `handle_update_filtered_alerts` for seamless frontend-backend sync

#### Technical Improvements
- **Smart Entity Validation**: Enhanced `is_valid_alert_entity()` function with domain-specific logic
- **Automatic Filter Updates**: `_saveMinWeightFilter()` and `_saveCategoryFilter()` trigger alert updates
- **Filtered Entity Display**: Debug section shows exactly which entities are being monitored
- **User Experience**: Clear feedback on why no entities are monitored (filter settings)

## [1.9.38] - 2025-01-04

### 🔔 **Intelligent Alert Monitoring System**
- **NEW: Advanced Alert Engine**: Comprehensive monitoring system for critical entities with AI-powered notifications
- **Weight-Based Monitoring**: Dynamic intervals from 30 seconds (weight 5) to 30 minutes (weight 1)
- **AI-Generated Messages**: Context-aware alert notifications using Home Assistant conversation agents
- **Flexible Notification Options**: Choice between notification services or input_text entities
- **Three-Tier Alert System**: WARNING, ALERT, and CRITICAL levels with automatic threshold detection
- **Intelligent Throttling**: Prevents notification spam while ensuring critical alerts are delivered
- **Real-Time Dashboard**: Visual monitoring interface with color-coded status indicators

#### Alert System Features
- **Automatic Categorization**: Monitors entities with ALERTS category automatically
- **Custom Thresholds**: AI analyzes entity patterns to set optimal alert thresholds
- **Multilingual Support**: Alert messages generated in user's preferred language (Italian/English)
- **Input Text Integration**: Alternative to notification services for dashboard display
- **Configuration UI**: Easy setup interface for notification preferences and entity management

#### Technical Enhancements
- New `AlertMonitor` class with comprehensive monitoring logic
- WebSocket API extensions for alert status and configuration
- Enhanced panel.js with alert configuration interface
- Persistent storage for alert configurations and monitored entities
- Full localization support for all alert system components

## [1.9.37] - 2025-08-16

### 🔧 **Entity Categorization Fixes** 
- **Fixed UNKNOWN entities issue**: All entities now receive proper multiple categories instead of being marked as "unknown"
- **Multi-category support enhanced**: Entities can now properly have multiple categories (e.g., `["DATA", "ALERTS"]`)
- **Improved fallback system**: When AI response fails, entities get proper domain-based categorization
- **Battery sensors fixed**: Now correctly assigned `["DATA", "ALERTS"]` instead of single category
- **Conversation agents fixed**: Properly categorized as `["CONTROL"]` with `SERVICE` management

#### Technical Improvements
- Fixed `_create_fallback_result()` to use all categories instead of just the first one
- Removed invalid `"UNKNOWN"` category - now defaults to `["DATA"]`
- Enhanced conversation agent fallback response with proper JSON structure
- Fixed correlation analysis to handle multiple categories correctly

#### Categories Now Working Properly
- **Battery sensors**: `["DATA", "ALERTS"]` with `USER` management
- **Temperature sensors**: `["DATA", "ALERTS"]` with `USER` management  
- **Lights/Switches**: `["CONTROL"]` with `USER` management
- **Conversation agents**: `["CONTROL"]` with `SERVICE` management
- **Update entities**: `["DATA", "ALERTS", "SERVICE"]` with `SERVICE` management
- **Health sensors**: `["DATA", "ALERTS"]` with `USER` management

## [1.9.2] - 2025-08-12

### 🎨 UI Improvements & Localization Fixes
- **Fixed AI Response Language**: Added explicit language instruction to ensure AI responds in user's language
- **Smaller Reason Text**: Reduced AI motivation text size to 0.85em for better readability
- **Better Progress Tracking**: Fixed entity count calculation that showed incorrect progress (e.g., "46 of 42")
- **Simplified Error Messages**: Changed confusing "Reduced group from 1 to 1" to clearer "Response error, retrying"
- **Taller Results Container**: Increased height from 50vh to 75vh with 60vh minimum for better space utilization

#### Technical Fixes
- Fixed total entity calculation in progress tracking
- Enhanced batch retry message clarity
- Improved CSS for reason text styling
- Better container height management during scans

#### User Experience
- AI responses now properly localized in Italian when using Italian interface
- Cleaner progress messages without confusing technical details
- More readable text sizing throughout the interface
- Better use of vertical space for results display

---

## [1.9.1] - 2025-08-12

### 🔧 Critical Bug Fixes
- **Fixed WebSocket Schema Error**: Added 'language' parameter to scan_entities WebSocket command schema
- **Resolved Cache Issues**: Implemented timestamp-based cache busting for all static resources
- **Eliminated 'Extra Keys Not Allowed' Error**: Proper WebSocket parameter validation
- **Enhanced Cache Management**: Automatic versioning prevents browser cache conflicts

#### Technical Improvements
- Updated cache busting timestamp mechanism
- Enhanced WebSocket command parameter handling
- Improved error messaging and debugging
- Better frontend resource loading reliability

#### What's Fixed
- No more `"extra keys not allowed. Got {'type': 'hass_ai/scan_entities', 'language': 'it', 'id': 37}"` errors
- Panel.js loads correctly with new version after HA restart
- All v1.9.0 features now work as intended
- Reliable localization parameter passing

---

## [1.9.0] - 2025-08-12

### 🌟 Major UI Overhaul - Complete Localization & User Experience

#### ✨ New Features
- **Complete Italian/English Localization**: Automatic language detection via `this.hass.language`
- **Simplified Progress Messages**: Clear, user-friendly progress indicators instead of technical batch numbers
- **Automatic Token Limit Handling**: No more popup alerts - seamless background management
- **Auto-Save Results**: Automatic saving during scans - no data loss
- **Flash Effects**: Visual feedback for newly analyzed entities
- **Detailed Attribute Analysis**: Comprehensive entity attribute breakdown with importance weights
- **Management Type Classification**: AI-powered distinction between user-managed vs service-managed entities

#### 🔧 Technical Improvements
- **Cache Busting**: Timestamp-based versioning for all static resources
- **WebSocket Schema Fix**: Added 'language' parameter to scan_entities command
- **Localized AI Prompts**: Context-aware prompts in Italian and English
- **Enhanced Error Handling**: Better fallback mechanisms and user feedback
- **Modern Notification System**: Replaced alert() popups with elegant toast notifications

#### 🌍 Localization Features
- Dynamic language switching based on Home Assistant locale
- Localized entity importance descriptions
- Translated UI components and messages
- Context-aware AI analysis prompts

#### 🎨 User Interface
- Clean, modern design with improved accessibility
- Intuitive progress tracking
- Real-time visual feedback
- Responsive layout improvements

#### 🛠️ Developer Experience
- Comprehensive documentation updates
- Enhanced debugging capabilities
- Better code organization
- Improved error reporting

### 🐛 Bug Fixes
- Fixed WebSocket 'extra keys not allowed' error
- Resolved cache issues preventing UI updates
- Improved entity filtering logic
- Enhanced error recovery mechanisms

### 📚 Documentation
- Added comprehensive localization guide
- Updated feature documentation
- Enhanced developer guidelines
- Complete API reference updates

---

## [1.8.0] - Previous Release
- Enhanced AI conversation integration
- Improved entity analysis algorithms
- Better performance optimizations

## [1.7.0] - Previous Release  
- Local conversation agent support
- Enhanced entity filtering
- Performance improvements
