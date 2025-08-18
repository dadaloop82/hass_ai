# HASS AI v1.9.41 Release Notes

## 🔧 Bug Fixes & AI Improvements

### Enhanced AI Analysis Quality
- **Fixed generic AI reasons**: Replaced vague "utilità automazioni" responses with specific, detailed explanations
- **Improved AI prompts**: AI now provides concrete reasons like "controllo luci camera", "monitoraggio temperatura", "batteria dispositivo"
- **Better compact mode**: When hitting token limits, AI still provides meaningful specific reasons

### Smart Entity Filtering
- **Exclude invalid entities**: Entities with states `unavailable`, `unknown`, `error`, `null`, empty, or `None` are now automatically skipped from AI analysis
- **Performance optimization**: Reduces token usage and improves AI response quality by filtering out problematic entities
- **Better logging**: Clear logs show which entities were skipped and why

### Enhanced Alert Detection
- **Improved temperature sensors**: Better recognition of temperature sensors including variations like "temp", "temperatura"
- **Humidity sensor recognition**: Added comprehensive humidity sensor detection ("humidity", "umidità", "moisture") 
- **Smart average sensors**: Sensors like `sensor.temperatura_media_casa` and `sensor.umidita_media_casa` are now properly classified as ALERT entities
- **Multi-language support**: Improved Italian language pattern matching for sensor types

### Category Classification Improvements
- **Fixed invalid entity handling**: Invalid/unavailable entities no longer incorrectly classified as ALERTS
- **Enhanced pattern matching**: Better recognition of sensor types across different naming conventions
- **Comprehensive metrics**: Average/mean sensors for important metrics (temperature, humidity, energy, power) now properly categorized

## 🆕 New Features

### Smart Entity Recognition
- **Advanced pattern matching**: Recognizes sensors with "media", "average", "mean", "avg" combined with important metrics
- **Multi-language entity names**: Supports both English and Italian sensor naming patterns
- **Comprehensive filtering**: Automatic exclusion of entities that shouldn't be analyzed by AI

### Enhanced Logging
- **Detailed filtering logs**: Shows exactly which entities were skipped and why
- **Better AI analysis tracking**: Improved visibility into what's being sent to AI
- **Performance metrics**: Tracks original vs filtered entity counts

## 🔄 Technical Changes
- Enhanced prompt engineering for more specific AI responses
- Improved entity state validation before AI analysis
- Better fallback handling for invalid entities
- Optimized pattern matching for sensor categorization

## 📋 Summary
This release significantly improves AI analysis quality by providing specific, meaningful reasons instead of generic responses, while also optimizing performance by filtering out problematic entities. Temperature and humidity sensors, especially average/mean variants, are now properly recognized as ALERT entities.

Users will now see much more useful AI reasoning like:
- ✅ "monitoraggio temperatura soggiorno per comfort"
- ✅ "controllo umidità media casa per salute"
- ✅ "batteria sensore movimento per sicurezza"

Instead of generic:
- ❌ "utilità automazioni"
