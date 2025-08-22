# MODIFICHE PER COMMIT v1.9.46

## FILES DA MODIFICARE SU GITHUB:

### 1. custom_components/hass_ai/manifest.json
```json
{
  "domain": "hass_ai", 
  "name": "HASS AI",
  "codeowners": ["@dadaloop82"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/dadaloop82/hass_ai",
  "homeassistant": "2024.1.0",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/dadaloop82/hass_ai/issues",
  "requirements": [],
  "version": "1.9.46"
}
```

### 2. COMMIT MESSAGE DA USARE:
```
Fix area detection errors and enhance enum entity support in v1.9.46

🐛 Bug Fixes:
- Fix 'HomeAssistant' object has no attribute 'helpers' error in area extraction
- Fix JavaScript 'Cannot read properties of undefined (reading 'token_stats')' error

🚀 Enhancements:
- Add support for enum entities with options attribute
- Enhance AI prompts to include all possible values for enum sensors
- Add comprehensive logging for entity context and area detection

🔧 Technical:
- Refactor registry access using proper homeassistant.helpers imports
- Add detailed debug logging for area resolution process
- Support both numeric and string values in AI threshold generation
```

## ALTERNATIVA: USA GITHUB WEB INTERFACE

1. Vai su https://github.com/dadaloop82/hass_ai
2. Modifica direttamente i file su GitHub
3. Fai commit con il messaggio sopra
4. Crea release v1.9.46

## OPPURE: SCARICA E RICARICA

1. Scarica il repository come ZIP
2. Sostituisci i file modificati
3. Ricarica tutto su GitHub
4. Crea tag v1.9.46
