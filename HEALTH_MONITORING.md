# 🏥 HASS AI Health Monitoring v1.9.12

## 🎯 Nuova Categoria HEALTH

Il sistema ora supporta una nuova categoria **HEALTH** per identificare problemi e anomalie dei dispositivi:

### ✅ **Categorie Supportate:**
- 📊 **DATA** - Entità che forniscono informazioni (sensori, meteo)
- 🎛️ **CONTROL** - Entità controllabili (luci, interruttori, termostati) 
- 🏥 **HEALTH** - Stati/attributi che indicano problemi, avvisi, anomalie

### 🚨 **Esempi di HEALTH Data:**
```
🔋 sensor.phone_battery (15%) → HEALTH, peso 4 (batteria critica)
⚠️ binary_sensor.door_sensor (unavailable) → HEALTH, peso 5 (dispositivo offline)
🌡️ sensor.temperature (-10°C) → HEALTH, peso 3 (valore anomalo)
📶 sensor.wifi_signal (-90dBm) → HEALTH, peso 2 (segnale debole)
💡 light.kitchen (48h sempre accesa) → HEALTH, peso 3 (possibile problema)
🔌 switch.boiler (unknown) → HEALTH, peso 4 (stato sconosciuto)
```

### 🎛️ **Sistema di Filtraggio:**
- **Filtro Categoria**: Filtra per `ALL`, `DATA`, `CONTROL`, `HEALTH`
- **Peso Minimo**: Controlla l'importanza (0-5)
- **Ricerca**: Cerca per nome o entity_id

### 🎨 **UI Updates:**
- 🏥 **HEALTH** badge con icona `mdi:heart-pulse` e colore arancione
- 📊 **DATA** badge con icona `mdi:chart-line` e colore blu
- 🎛️ **CONTROL** badge con icona `mdi:tune` e colore verde

### 🧠 **AI Prompts Aggiornati:**
L'AI ora cerca specificamente:
- Stati `unavailable`, `unknown`
- Batterie basse (<20%)
- Temperature anomale
- Errori di connessione
- Dispositivi offline
- Segnali deboli

## 🚀 **Come Funziona:**
1. **Scansione**: L'AI analizza ogni entità e ne determina il tipo
2. **Classificazione**: Assegna categoria e peso di importanza
3. **Filtraggio**: Dashboard separata per ogni categoria
4. **Monitoraggio**: Focus sui problemi con categoria HEALTH

Perfetto per monitoraggio proattivo della salute dei dispositivi! 🎯
