# HASS AI v1.9.44 - Release Notes

## 🎯 Comprehensive AI Logging and Debugging System

Questa versione introduce un sistema completo di logging e debugging per tutte le interazioni AI, risolvendo i problemi di trasparenza e debuggabilità richiesti dall'utente.

## ✨ Nuove Funzionalità

### 🔍 Sistema di Logging AI Completo
- **AILogger Class**: Nuova classe dedicata per il logging strutturato delle interazioni AI
- **Log Giornalieri**: Separazione automatica dei log per giorno (`ai_logs_YYYY-MM-DD.json`)
- **Endpoint WebSocket**: Nuovo endpoint `hass_ai/get_ai_logs` per accedere ai log dal frontend
- **Tracciamento Completo**: Logging di prompt, risposte ed errori con contesto dettagliato

### 📊 Tipi di Log Implementati
1. **Prompt Logs**: Tutti i prompt inviati all'AI con metadati completi
2. **Response Logs**: Tutte le risposte AI con dimensioni e contesto
3. **Error Logs**: Errori dettagliati per debugging (token limits, JSON parsing, timeouts)

### 🌍 Miglioramenti Area Detection
- **Integrazione Area Registry**: Accesso corretto alle aree di Home Assistant
- **Mappatura Entità-Area**: Visualizzazione corretta delle aree invece di duplicati
- **Fallback Intelligente**: Gestione robusta quando le informazioni area non sono disponibili

## 🐛 Correzioni di Bug

### 🚫 Filtraggio Entità Migliorato
- **Esclusione input_text**: Le entità `input_text.hass_ai_*` non vengono più categorizzate come alert
- **Validazione Domini**: Controlli migliorati per evitare categorizzazioni inappropriate
- **Categorizzazione SERVICE**: Nuova categoria per entità di servizio del sistema

### 🎯 Generazione Soglie Potenziata
- **Riconoscimento Sensori**: Migliorata l'identificazione di sensori che necessitano soglie
- **Prompt AI Specifici**: Prompt più dettagliati per risultati più accurati
- **Gestione Errori**: Logging completo degli errori di generazione soglie

## 🚀 Miglioramenti Tecnici

### 📝 Logging Strutturato
```json
{
  "timestamp": "2025-08-22T17:05:48.424949",
  "type": "prompt|response|error",
  "content": "...",
  "context": {
    "entity_id": "sensor.example",
    "batch_number": 1,
    "analysis_type": "importance|threshold_generation"
  }
}
```

### 🔒 Privacy e Sicurezza
- **Directory ai_logs/**: Esclusa da Git per proteggere informazioni sensibili
- **Organizzazione Giornaliera**: File separati per ogni giorno per gestione semplificata
- **Accesso Controllato**: Solo attraverso WebSocket autenticato

### 🧪 Sistema di Test
- **test_ai_logging.py**: Script completo per testare il sistema di logging
- **Log di Esempio**: Generazione automatica di log per verificare funzionalità
- **Validazione Completa**: Test di tutti i tipi di log e scenari di errore

## 📊 Utilizzo del Sistema di Logging

### Accesso via WebSocket
```javascript
// Ottenere gli ultimi 100 log
hass.callWS({
  type: "hass_ai/get_ai_logs",
  limit: 100,
  level: "all"  // "prompt", "response", "error", "all"
})
```

### Struttura Directory
```
ai_logs/
├── README.md                    # Documentazione sistema logging
├── ai_logs_2025-08-22.json    # Log del 22 agosto 2025
├── ai_logs_2025-08-23.json    # Log del 23 agosto 2025
└── ...
```

## 🔄 Aggiornamenti da Versioni Precedenti

### Database/Storage
- Nessuna migrazione richiesta
- Tutti i dati esistenti rimangono compatibili
- I log inizieranno ad accumularsi automaticamente

### Configurazione
- Nessun cambiamento alla configurazione esistente
- Sistema di logging attivo automaticamente
- Directory `ai_logs/` creata automaticamente

## 🏷️ Versioning

- **Versione**: 1.9.44
- **Compatibilità**: Home Assistant 2023.3+
- **Breaking Changes**: Nessuno
- **Deprecazioni**: Nessuna

## 👥 Contributi e Feedback

Questa versione risponde direttamente alle richieste dell'utente per:
- ✅ Sistema di logging completo per prompt e risposte AI
- ✅ Gestione errori dettagliata per debugging
- ✅ Miglioramento detection aree e categorizzazione entità
- ✅ Esclusione entità inappropriate dagli alert
- ✅ Organizzazione log per giorno con privacy protection

Il sistema è ora completamente trasparente e debuggabile per ottimizzare le performance AI.
