import csv, json

with open(r'C:\tesis2026\tesis_wrf_pgich\historico\ecowitt_historico_20260705.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

times = sorted(set(r['fecha_hora'] for r in rows))

# Find all times with 4 stations having temp data
good_times = []
for t in times:
    subset = [r for r in rows if r['fecha_hora'] == t]
    temps = [r['temp_c'] for r in subset if r['temp_c']]
    if len(temps) == 4:
        good_times.append(t)

print(f"Times with all 4 stations: {len(good_times)}")
if good_times:
    print(f"  First: {good_times[0]}")
    print(f"  Last: {good_times[-1]}")
    # Pick closest to 21:00
    target = '2026-07-05 21:00:00'
    closest = min(good_times, key=lambda x: abs(ord(x[11]) - ord(target[11])))
    print(f"  Closest to 21:00: {closest}")

    # Use the last available time
    t = good_times[-1]
    subset = [r for r in rows if r['fecha_hora'] == t]
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
    print(f"\nUsing time: {t}")
    for o in obs_list:
        print(f"  {o['estacion']}: T={o['temp']}C, RH={o['humedad']}%, PSFC={o['presion_absoluta']}hPa")

    with open(r'C:\tesis2026\tesis_wrf_pgich\historico\obs_flat_20260705.json', 'w', encoding='utf-8') as f:
        json.dump(obs_list, f, indent=2, ensure_ascii=False)
