# GUIDA STEP-BY-STEP per Rilascio v1.9.46

## PASSO 1: Esegui i comandi Git
Apri PowerShell/CMD nella cartella `c:\dev\hass_ai` ed esegui:

```bash
git add -A
git commit -m "Fix area detection errors and enhance enum entity support in v1.9.46"
git push origin main
git tag v1.9.46
git push origin v1.9.46
```

## PASSO 2: Verifica su GitHub
1. Vai su https://github.com/dadaloop82/hass_ai
2. Controlla che ci sia il nuovo commit
3. Controlla che ci sia il tag v1.9.46 nella sezione "Releases"

## PASSO 3: Attendi HACS (5-15 minuti)
1. HACS controlla periodicamente i repository
2. La versione v1.9.46 dovrebbe apparire automaticamente
3. Se non appare entro 30 minuti, riavvia Home Assistant

## PASSO 4: Aggiorna tramite HACS
1. Vai in HACS > Integrations
2. Cerca "HASS AI"
3. Dovrebbe mostrare "Update available" con v1.9.46
4. Clicca "Update"

## PASSO 5: Riavvia Home Assistant
1. Vai in Settings > System > Restart
2. Attendi il riavvio completo
3. Verifica che sia attiva la v1.9.46

## PASSO 6: Testa le Correzioni
1. Vai nel pannello HASS AI
2. Esegui una scansione
3. Controlla i logs - NON dovrebbero più esserci errori:
   - ❌ `'HomeAssistant' object has no attribute 'helpers'`
   - ❌ `Cannot read properties of undefined (reading 'token_stats')`
4. Verifica che le aree vengano rilevate correttamente

## FILE MODIFICATI in questa versione:
- ✅ `intelligence.py` - Area detection fix + enum support
- ✅ `panel.js` - Token stats error fix  
- ✅ `manifest.json` - Version bump to 1.9.46
- ✅ `RELEASE_NOTES_v1.9.46.md` - Documentazione
- ✅ `RELEASE_SUMMARY_v1.9.46.md` - Riassunto modifiche

## COSA ASPETTARSI:
1. **Nessun errore** nei logs di Home Assistant
2. **Area corretta** per ogni entità durante la scansione
3. **Supporto enum** per entità come backup_manager_state
4. **Logs dettagliati** che mostrano il processo di area detection

Se hai problemi con i comandi git o non vedi l'aggiornamento, fammelo sapere! 🚀
