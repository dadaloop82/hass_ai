# Test token calculation for HASS AI prompts

# Ultra-compact prompt example (Italian)
prompt_italian = """Analizza 2 entità HA. Importanza 0-5:
0=Ignora, 1=Molto bassa, 2=Bassa, 3=Media, 4=Alta, 5=Critica
Categorie: DATA (sensori), CONTROL (controlli), HEALTH (problemi/offline/batteria<20%)
JSON: [{"entity_id":"...","rating":0-5,"reason":"breve","category":"DATA/CONTROL/HEALTH","management_type":"USER/SERVICE"}]
REASON IN INGLESE.

sensor.battery_level (sensor, 45%, Battery Level)
light.living_room (light, on, Living Room Light)"""

# Ultra-compact prompt example (English)
prompt_english = """Analyze 2 HA entities. Importance 0-5:
0=Ignore, 1=Very low, 2=Low, 3=Medium, 4=High, 5=Critical
Categories: DATA (sensors), CONTROL (controls), HEALTH (problems/offline/battery<20%)
JSON: [{"entity_id":"...","rating":0-5,"reason":"brief","category":"DATA/CONTROL/HEALTH","management_type":"USER/SERVICE"}]
REASON IN ENGLISH.

sensor.battery_level (sensor, 45%, Battery Level)
light.living_room (light, on, Living Room Light)"""

print(f"Italian prompt: {len(prompt_italian)} chars, ~{len(prompt_italian)//4} tokens")
print(f"English prompt: {len(prompt_english)} chars, ~{len(prompt_english)//4} tokens")

# Maximum with 2 entities should be under 500 chars
print(f"\nTarget: <500 chars per prompt")
print(f"Italian: {'✅ OK' if len(prompt_italian) < 500 else '❌ TOO LONG'}")
print(f"English: {'✅ OK' if len(prompt_english) < 500 else '❌ TOO LONG'}")
