🤖 feat: Sistema di Logging AI Completo v1.9.43

## 📊 Nuove Funzionalità

### Sistema di Logging AI Comprehensivo
- ✅ **AILogger Class**: Logging completo di prompt, risposte ed errori AI
- ✅ **Log Giornalieri**: File separati per giorno in formato JSON leggibile
- ✅ **WebSocket API**: Endpoint `/hass_ai/get_ai_logs` per accesso ai log
- ✅ **Contesti Dettagliati**: Metadati completi per ogni interazione AI

### Integrazioni di Logging
- ✅ **Intelligence.py**: Logging completo in `_process_single_batch`
- ✅ **Threshold Generation**: Logging per generazione soglie automatiche
- ✅ **Error Handling**: Cattura completa errori JSON, token limit, timeout
- ✅ **Area Registry**: Logging per mappatura aree entità

### Debugging Avanzato
- ✅ **Prompt Tracking**: Dimensioni prompt, modalità compatta, batch info
- ✅ **Response Analysis**: Dimensioni risposte, parsing JSON, validazione
- ✅ **Error Classification**: Categorizzazione errori con context specifici
- ✅ **Performance Monitoring**: Token usage, batch processing times

## 🔧 Miglioramenti

### Gestione Entità
- ✅ **Filtro input_text**: Escluse entità HASS AI da categorizzazione alert
- ✅ **Area Detection**: Migliorata mappatura entità-aree via registries
- ✅ **Sensor Recognition**: Potenziato riconoscimento sensori per soglie

### AI Analysis
- ✅ **Prompt Enhancement**: Prompt più specifici per ridurre risposte generiche
- ✅ **Entity Filtering**: Filtri migliorati per escludere entità inappropriate
- ✅ **Threshold Logic**: Logica più robusta per generazione soglie automatiche

## 📁 Struttura Log

```
custom_components/hass_ai/logs/
├── ai_logs_YYYY-MM-DD.json     # Log interazioni giornaliere
├── ai_errors_YYYY-MM-DD.json   # Log errori giornalieri  
└── README.md                   # Documentazione logging
```

## 🔗 API WebSocket

```javascript
// Recupera log AI
websocket.send({
  "type": "hass_ai/get_ai_logs",
  "limit": 100,
  "level": "all" // "all", "error", "prompt", "response"
});
```

## 🐛 Fix Applicati

- ✅ **Token Limit**: Gestione migliorata errori limite token
- ✅ **JSON Parsing**: Logging errori parsing con raw response
- ✅ **Area Mapping**: Fix duplicati in display aree entità
- ✅ **Entity Validation**: Prevenzione categorizzazione errata input_text

## 📈 Benefici

1. **Debugging Completo**: Visibilità totale su interazioni AI
2. **Performance Tuning**: Identificazione bottleneck e ottimizzazioni
3. **Quality Assurance**: Monitoraggio qualità risposte AI
4. **Troubleshooting**: Diagnosi rapida problemi configurazione
5. **Development**: Supporto sviluppo future feature AI

## ⚙️ Configurazione

Il logging è automatico e non richiede configurazione. I log sono accessibili via:
- File system: `custom_components/hass_ai/logs/`
- WebSocket API: `hass_ai/get_ai_logs`
- Frontend: Integrazione futura pannello debug

---

**Compatibilità**: Home Assistant 2024.1+
**Dipendenze**: Nessuna aggiuntiva
**Breaking Changes**: Nessuno
