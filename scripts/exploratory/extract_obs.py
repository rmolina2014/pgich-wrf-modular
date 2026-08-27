import csv, json

with open(r'C:\tesis2026\tesis_wrf_pgich\historico\ecowitt_historico_20260705.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

# Get all unique times
times = sorted(set(r['fecha_hora'] for r in rows))
print(f"Total rows: {len(rows)}, unique times: {len(times)}")

# Get a time with all 4 stations having temp data
for t in times:
    subset = [r for r in rows if r['fecha_hora'] == t]
    temps = [r['temp_c'] for r in subset if r['temp_c']]
    if len(temps) == 4:
        print(f"Good time: {t}")
        obs_list = []
        for r in subset:
            obs_list.append({
                "estacion": r["estacion"],
                "temp": float(r["temp_c"]) if r["temp_c"] else None,
                "humedad": float(r["humedad_pct"]) if r["humedad_pct"] else None,
                "presion_absoluta": float(r["presion_absoluta_hpa"]) if r["presion_absoluta_hpa"] else None,
                "viento": float(r["viento_kmh"]) if r["viento_kmh"] else None,
                "direcc": float(r["direcc_grados"]) if r["direcc_grados"] else None,
            })
        print(json.dumps(obs_list, indent=2))
        # Save
        with open(r'C:\tesis2026\tesis_wrf_pgich\historico\obs_flat_20260705.json', 'w', encoding='utf-8') as f:
            json.dump(obs_list, f, indent=2, ensure_ascii=False)
        print("Saved to obs_flat_20260705.json")
        break
