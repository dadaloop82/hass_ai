# Changelog

All notable changes to this project will be documented in this file.

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
