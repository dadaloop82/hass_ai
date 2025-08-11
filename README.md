# HASS AI - Intelligenza Artificiale per Home Assistant

**HASS AI** trasforma il tuo Home Assistant in un ambiente veramente intelligente fornendo uno strumento potente e interattivo per gestire come il sistema comprende e priorizza i tuoi dispositivi ed entità. Funziona come un livello di intelligenza avanzato, permettendoti di insegnare al tuo Home Assistant quali entità sono più importanti, su quali proprietà concentrarsi e quali ignorare.

## 🚀 Caratteristiche Principali

- **Analisi AI Automatica**: Valutazione intelligente delle entità basata su tipo, nome, attributi e dati storici
- **Interfaccia Interattiva**: Panel dedicato con controlli intuitivi per gestire l'importanza delle entità  
- **Trasparenza Completa**: Spiegazioni chiare del perché ogni entità ha ricevuto un determinato punteggio
- **Controllo Utente**: Override completo delle valutazioni AI per adattarle alle tue esigenze
- **Persistenza**: Tutte le personalizzazioni vengono salvate automaticamente
- **Supporto Multilingua**: Interfaccia disponibile in italiano e inglese

## 🏠 Come Funziona

Il sistema utilizza l'AI locale di Home Assistant (tramite conversation agent) per:

1. **Analizzare** tutte le entità del sistema
2. **Valutare** la loro importanza su una scala 0-5:
   - 0 = Ignora (diagnostico/non necessario)
   - 1 = Molto Basso (raramente utile)
   - 2 = Basso (occasionalmente utile) 
   - 3 = Medio (comunemente utile)
   - 4 = Alto (frequentemente importante)
   - 5 = Critico (essenziale per automazioni)
3. **Fornire** ragioni dettagliate per ogni valutazione
4. **Permettere** personalizzazioni complete dall'utente

## 📦 Installazione

### Via HACS (Raccomandato)

1. Apri HACS in Home Assistant
2. Vai su "Integrazioni"
3. Clicca su "Esplora e scarica repository"
4. Cerca "HASS AI"
5. Clicca "Scarica"
6. Riavvia Home Assistant
7. Vai su Impostazioni → Dispositivi e Servizi → Aggiungi Integrazione
8. Cerca "HASS AI" e configurala

### Installazione Manuale

1. Scarica questo repository
2. Copia la cartella `custom_components/hass_ai` nella tua cartella `custom_components`
3. Riavvia Home Assistant
4. Aggiungi l'integrazione come sopra

## ⚙️ Configurazione

### Configurazione Iniziale

Durante la configurazione potrai impostare:

- **Provider AI**: Attualmente supporta solo il conversation agent integrato
- **Intervallo Scansione**: Ogni quanti giorni eseguire scansioni automatiche (1-30 giorni)

### Requisiti

- Home Assistant 2023.4.0 o superiore
- Conversation agent configurato (Google Gemini, OpenAI, ecc.)

## 🎯 Utilizzo

### 1. Pannello di Controllo

Dopo l'installazione, troverai un nuovo pannello "HASS AI" nella barra laterale:

- **Avvia Scansione**: Analizza tutte le entità del sistema
- **Tabella Interattiva**: Visualizza e modifica i pesi delle entità
- **Log di Analisi**: Vedi i dettagli delle valutazioni AI

### 2. Servizi Disponibili

L'integrazione espone diversi servizi utilizzabili nelle automazioni:

```yaml
# Scansiona tutte le entità
service: hass_ai.scan_entities
data:
  entity_filter: "sensor."  # Opzionale: filtra per tipo
  batch_size: 10           # Opzionale: entità per batch

# Ottieni importanza di una singola entità
service: hass_ai.get_entity_importance  
data:
  entity_id: "light.living_room"

# Reset di tutti gli override
service: hass_ai.reset_overrides
data:
  confirm: true
```

### 3. Automazioni di Esempio

```yaml
# Automazione per scansione periodica personalizzata
automation:
  - alias: "HASS AI - Scansione Sensori Settimanale"
    trigger:
      - platform: time
        at: "02:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: hass_ai.scan_entities
        data:
          entity_filter: "sensor."
          batch_size: 15

# Usa i pesi AI nelle tue automazioni
automation:
  - alias: "Spegni Luci Non Importanti"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion_living_room
        to: "off"
        for: "00:10:00"
    action:
      - service: light.turn_off
        target:
          entity_id: >
            {% set lights = states.light | selectattr('state', 'eq', 'on') | list %}
            {% set unimportant_lights = [] %}
            {% for light in lights %}
              {% if state_attr('hass_ai.' + light.entity_id, 'weight') | int < 3 %}
                {% set unimportant_lights = unimportant_lights + [light.entity_id] %}
              {% endif %}
            {% endfor %}
            {{ unimportant_lights }}
```

## 🔧 API e Integrazione

### Template Helper

Puoi usare i dati HASS AI nei tuoi template:

```yaml
# Sensor che conta entità critiche attive
sensor:
  - platform: template
    sensors:
      critical_entities_active:
        friendly_name: "Entità Critiche Attive"
        value_template: >
          {% set critical_count = 0 %}
          {% for state in states %}
            {% if state_attr('hass_ai.' + state.entity_id, 'weight') | int >= 4 %}
              {% if state.state not in ['unknown', 'unavailable'] %}
                {% set critical_count = critical_count + 1 %}
              {% endif %}
            {% endif %}
          {% endfor %}
          {{ critical_count }}
```

### Accesso Programmatico

I dati sono disponibili tramite WebSocket API:

```javascript
// Carica override esistenti
hass.callWS({type: "hass_ai/load_overrides"})

// Avvia scansione con callback in tempo reale
hass.connection.subscribeMessage(
  (message) => console.log(message),
  {type: "hass_ai/scan_entities"}
)

// Salva override personalizzati
hass.callWS({
  type: "hass_ai/save_overrides", 
  overrides: {
    "light.living_room": {
      enabled: true,
      overall_weight: 5
    }
  }
})
```
