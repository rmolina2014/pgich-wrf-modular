# Plan: Ciclo completo en Windows vía Docker

Fecha: 2026-08-05

## 1. Contexto / estado actual

| Componente | Estado |
|---|---|
| Docker Desktop | Instalado pero NO corriendo (la API no responde) |
| Contenedor `teachme` | Existe en WSL (distro `docker-desktop` = Running), inaccesible sin Docker |
| Python (Windows) | 3.12.3 |
| Libs presentes | numpy, pandas, matplotlib, cfgrib, eccodes, requests, python-dotenv |
| Libs faltantes | xarray, netCDF4, scipy, metpy, openpyxl |
| Pipeline de obs | Funciona en Windows (limpieza → Little_R → OBS_DOMAIN101) |
| WRF/WPS | Solo en el contenedor (imposible correr WRF nativo en Windows) |
| Validación | Usa xarray → depende de correr dentro del contenedor |

Conclusión: para que el ciclo funcione en esta máquina, es obligatorio Docker
(WRF y WPS no corren en Windows nativo). La validación se mantiene dentro del
contenedor.

## 2. Paso 1 — Arrancar Docker Desktop

- Iniciar `C:\Program Files\Docker\Docker\Docker Desktop.exe`
- Esperar a que el daemon (motor Linux) esté listo (30-60 s aprox.)
- Verificar que la API responde:

```bash
docker ps
```

- Confirma que aparece el contenedor `teachme`.

## 3. Paso 2 — Verificar contenedor `teachme`

- Confirmar que tiene WRF 4.6.1 + WPS 4.6.0 compilados.
- Verificar directorios clave:

```bash
docker exec teachme bash -c "ls /wrf/WRF/test/em_real/real.exe /wrf/WRF/test/em_real/wrf.exe"
docker exec teachme bash -c "ls /wrf/WPS/ | head -20"
```

- Verificar datos estáticos y Vtable:

```bash
docker exec teachme bash -c "ls /wrf/WPS_GEOG/WPS_GEOG_LOW_RES/"
docker exec teachme bash -c "ls -la /wrf/WPS/Vtable*"
```

- Si el contenedor no existe, recrearlo desde `davegill/wrf-coop:fourteenthtry`
  (ver `CONFIG_WRF_SAN_JUAN.md`).
- Si hay `wrfout_d01_2026-07-05_*` previos, decidir si se reusan o se re-corren.

## 4. Paso 3 — Reconstruir ciclo 2026-07-05

En orden, usando el flujo ya validado:

1. **Observaciones (OBS_DOMAIN101)**
   ```bash
   python tesis_wrf_pgich/src/calidad/historico_a_obsnud.py \
     --fecha 2026-07-05 \
     --csv tesis_wrf_pgich/historico/ecowitt_historico_20260705.csv \
     --output-dir tesis_wrf_pgich/data/processed \
     --wrf
   ```

2. **GFS (0.25° desde NOMADS, subregión)**
   ```bash
   python descargar_gfs.py --date 2026-07-05 --source nomads
   ```

3. **WPS** (dentro del contenedor)
   ```bash
   docker exec teachme bash -c "cd /wrf/WPS && ./geogrid.exe && ./ungrib.exe && ./metgrid.exe"
   ```

4. **real.exe** (dentro del contenedor)
   ```bash
   docker exec teachme bash -c "cd /wrf/WRF/test/em_real && ./real.exe"
   ```

5. **wrf.exe nudged** (`obs_nudge_opt=1`, coef 0.001) → 13 `wrfout`
   ```bash
   docker exec teachme bash -c "cd /wrf/WRF/test/em_real && mpirun -np 4 ./wrf.exe"
   ```

6. **wrf.exe control** (`obs_nudge_opt=0`) → 13 `wrfout`

7. **Validación dentro del contenedor** → gráficas + `metricas_resumen.txt`
   ```bash
   docker exec teachme bash -c "cd /tmp && python3 valida_wrf.py ..."
   ```

## 5. Paso 4 — Probar `pipeline_wrf.py`

- Correr el orquestador en modo `--validate-only` para confirmar que toma
  `nudged/` y `control/` del contenedor y produce las métricas.

```bash
python pipeline_wrf.py --date 2026-07-05 --hour 21:00 --case sens_coef001 --validate-only
```

- Si se quiere automatizar, agregar fechas adicionales para la Fase 4.

## 6. Paso 5 — Documentar

- Actualizar `REPRODUCIR_CICLO.md` con la ruta concreta usada en este equipo
  Windows (comando por comando), para que la corrida sea reproducible.

## 7. Nota de riesgo

WSL2/Docker Desktop en Windows se desconecta con frecuencia (reportado en
sesiones previas). Durante la corrida de `wrf.exe` hay que asegurarse de NO
suspender la máquina ni cerrar Docker Desktop.