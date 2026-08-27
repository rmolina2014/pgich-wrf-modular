# Configuracion WRF para San Juan (Argentina)

## 1. Dominio

| Parametro | Valor |
|---|---|
| Centro | 31.5°S, 68.5°O |
| Proyeccion | Mercator |
| Resolucion | 15 km |
| Puntos horizontales | 80 × 60 (e_we × e_sn) |
| Niveles verticales | 35 (e_vert) |
| Time step | 90 s |
| Cobertura aprox. | 1200 × 900 km |
| Abarca: | San Juan, Mendoza, La Rioja, San Luis, Cordoba |

```
                  80 × 60 grid cells @ 15 km
    ┌─────────────────────────────────────────────────┐
    │  ~29°S, ~73°O                          ~29°S, ~64°O  │
    │                                                   │
    │     San Juan (centro) ~31.5°S, 68.5°O             │
    │     Estaciones EcoWitt dentro del dominio          │
    │                                                   │
    │  ~34°S, ~73°O                          ~34°S, ~64°O  │
    └─────────────────────────────────────────────────┘
```

## 2. Forzante (GFS)

| Parametro | Valor |
|---|---|
| Fuente | AWS Open Data (`noaa-gfs-bdp-pds`) |
| Resolucion espacial | 0.25° (~28 km) |
| Resolucion temporal | 3 h |
| Intervalo de anidacion | 10800 s (3 h) |
| Niveles | 34 (num_metgrid_levels) |
| Niveles de suelo | 4 (num_metgrid_soil_levels) |
| Top of atmosphere | 5000 Pa (p_top_requested) |

## 3. WPS

### geogrid

| Parametro | Valor |
|---|---|
| Datos geograficos | `WPS_GEOG_LOW_RES` |
| Path | `/wrf/WPS_GEOG/WPS_GEOG_LOW_RES/` |

### ungrib

| Parametro | Valor |
|---|---|
| Formato salida | WPS |
| Prefix | `FILE` |
| Vtable | GFS (Vtable.GFS) |

### metgrid

| Parametro | Valor |
|---|---|
| fg_name | `FILE` |
| io_form_metgrid | 2 (NetCDF) |

Output: `met_em.d01.2026-05-25_12:00:00.nc` (4 archivos, uno cada 3h)

### Descarga GFS

```bash
# Fuente: AWS Open Data
aws s3 sync s3://noaa-gfs-bdp-pds/gfs.20260525/12/atmos/ .
# O via wget:
# https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?...
```

## 4. WRF

### 4.1 Namelist completo

Archivo: `namelist.input` (ver `C:\tesis2026\namelist.input`)

### 4.2 &time_control

| Parametro | Valor | Descripcion |
|---|---|---|
| run_hours | 12 | Duracion de la simulacion |
| start_* | 2026-05-25 12:00z | Inicio (boundary conditions desde 12z) |
| end_* | 2026-05-26 00:00z | Fin |
| history_interval | 60 | Salida cada 60 min |
| frames_per_outfile | 1 | 1 archivo por hora |
| auxinput11_interval_m | 30 | Lectura OBS_DOMAIN101 cada 30 min |
| auxinput11_inname | `OBS_DOMAIN101` | Archivo de observaciones |

### 4.3 &domains

| Parametro | Valor | Descripcion |
|---|---|---|
| time_step | 90 s | 6×dx (regla: 6 × 15 km = 90) |
| e_we / e_sn | 80 / 60 | Puntos de grilla |
| e_vert | 35 | Niveles verticales |
| dx / dy | 15000 m | Tamanio de celda |
| p_top_requested | 5000 Pa | Tope del modelo (~35 km) |
| num_metgrid_levels | 34 | Niveles del forzante GFS |
| num_metgrid_soil_levels | 4 | Niveles de suelo |

### 4.4 &physics

| Parametro | Valor | Esquema real (suite CONUS) |
|---|---|---|
| physics_suite | `CONUS` | Suite predefinida (alpha=1) |
| mp_physics | -1 (hereda) | Thompson |
| cu_physics | -1 (hereda) | Grell-Freitas |
| ra_lw_physics | -1 (hereda) | RRTMG |
| ra_sw_physics | -1 (hereda) | RRTMG |
| bl_pbl_physics | -1 (hereda) | MYNN |
| sf_sfclay_physics | -1 (hereda) | MYNN |
| sf_surface_physics | -1 (hereda) | Noah LSM |
| radt | 15 min | Llamado de radiacion |
| bldt | 0 | Llamado de PBL (cada paso) |
| icloud | 1 | Feedback nubes-radiacion |
| num_land_cat | 21 | Categorias de suelo (MODIS) |
| sf_urban_physics | 0 | Sin urban canyon |

Nota: `= -1` significa "heredar de la suite" (CONUS define los valores).

### 4.5 &fdda — Obs Nudging (clave para la tesis)

| Parametro | Valor recomendado | Rango testeado | Descripcion |
|---|---|---|---|
| `obs_nudge_opt` | 1 | 0 o 1 | Activa nudging |
| `obs_nudge_wind` | 1 | — | Nudging de viento |
| `obs_nudge_temp` | 1 | — | Nudging de temperatura |
| `obs_nudge_mois` | 1 | — | Nudging de humedad |
| `obs_coef_wind` | **0.001** | 0.0001 - 0.005 | Coeficiente nudging viento |
| `obs_coef_temp` | **0.001** | 0.0001 - 0.005 | Coeficiente nudging temp |
| `obs_coef_mois` | **0.001** | 0.0001 - 0.005 | Coeficiente nudging humedad |
| `obs_twindo` | **1.0 - 2.0 h** | 0.5, 1.0, 2.0 | Ventana temporal |
| `obs_rinxy` | 50.0 km | — | Radio de influencia |
| `obs_sfcfacr` | 2.0 | — | Factor correlacion superficial |
| `obs_sfcfact` | 1.0 | — | Factor escala superficial |
| `obs_ionf` | 1 | — | Frecuencia de lectura |
| `obs_npfi` | 30 | — | Pasos entre lecturas |
| `obs_ipf_in4dob` | .true. | — | Interpolar en 4D |
| `max_obs` | 10000 | — | Max observaciones |
| `fdda_end` | **720** min | — | Final del nudging (12h) |

**Resultados de sensibilidad** (caso 2026-05-25 21z):

| Coeficiente | T2 RMSE | RH RMSE | Wind RMSE |
|---|---|---|---|
| Control (sin nudging) | 6.25 | 23.37 | 3.64 |
| 0.0001 | 5.84 | 21.11 | 3.64 |
| 0.0005 (original) | 4.94 | 14.84 | 3.36 |
| **0.001** | **4.55** | **11.82** | **3.23** |
| 0.005 | 4.61 | 11.43 | 3.19 |

### 4.6 &dynamics

| Parametro | Valor | Descripcion |
|---|---|---|
| hybrid_opt | 2 | Coordenada vertical hibrida |
| diff_opt | 2 | Esquema de difusion |
| km_opt | 4 | Coeficiente de mezcla |
| damp_opt | 3 | Rayleigh damping |
| zdamp | 5000 m | Altura del damping |
| dampcoef | 0.2 | Coeficiente de damping |
| base_temp | 290 K | Temperatura base |
| non_hydrostatic | .true. | No hidrostatico |
| gwd_opt | 1 | Gravity wave drag |

### 4.7 &bdy_control

| Parametro | Valor |
|---|---|
| spec_bdy_width | 5 |
| specified | .true. |

## 5. Observaciones para nudging

### 5.1 Estaciones EcoWitt

| Estacion | Lat | Lon | Elev (m) | MAC |
|---|---|---|---|---|
| INTA_SANMARTIN | -31.1234 | -67.5432 | 650 | 30:83:98:A6:B3:AA |
| INTA_POCITO | -31.5678 | -67.8901 | 580 | 30:83:98:A7:43:1B |
| VALLE_FERTIL | -31.9012 | -67.2345 | 1120 | 30:83:98:A7:1E:10 |
| LOS_PIONEROS | -32.1234 | -67.1234 | 890 | 30:83:98:A7:09:CD |
| CUESTA_Viento | -32.3456 | -66.5678 | 1850 | 30:83:98:A5:52:40 |
| ULLUM_EMBALSE | -31.7890 | -66.9012 | 1150 | 30:83:98:A5:CB:17 |
| PUNTA_NEGRA | -31.4567 | -66.3456 | 1420 | 30:83:98:A6:BB:72 |
| CARACOLES | -31.6789 | -66.7890 | 1580 | 30:83:98:A7:47:39 |
| ECOHUMUS | -31.5000 | -67.0000 | 700 | BC:FF:4D:F7:DF:DA |

### 5.2 Pipeline de observaciones

```
EcoWitt API (real_time)
  → JSON crudo (data/raw/ecowitt_todos_*.json)
    → limpiador_pgich.py → CSV validado
      → generador_littler.py → Little_R (formato WRFDA)
        → littler_a_obsnud.py → OBS_DOMAIN101 (formato 105)
          → docker cp → contenedor:/wrf/WRF/test/em_real/
```

### 5.3 Formato OBS_DOMAIN101 (formato 105)

```
Linea 1: Fecha (14 chars):          YYYYMMDDHHMMSS
Linea 2: Lat, Lon (2×f9.4):        -31.1234  -67.5432
Linea 3: ID, Name (2×a40):         INTA_SANMARTIN  SURFACE
Linea 4: Platf, Source, Elev, ...:  SYNOP  INTA_SANMARTIN  650  F  F  1
Linea 5: 9 pares (val, qc):        temp u v rh psfc ...
```

Variables en cada observacion: SLP, ref_pres, height, temperature, u_wind, v_wind, RH, surface_pressure, precip.

Earth-relative U/V con QC=129.

## 6. Ejecucion

### 6.1 Pre-procesamiento

```bash
# 1. WPS
cd /wrf/WPS
./geogrid.exe
./ungrib.exe
./metgrid.exe

# 2. real.exe
cd /wrf/WRF/test/em_real
ln -sf /wrf/WPS/met_em* .
./real.exe
```

### 6.2 WRF con obs nudging

```bash
cd /wrf/WRF/test/em_real

# Corrida nudged
cp namelist.nudged.input namelist.input
mpirun -np 4 ./wrf.exe

# Corrida control
cp namelist.control.input namelist.input
rm -f rsl.*
mpirun -np 4 ./wrf.exe
```

### 6.3 Validacion

```bash
python3 valida_wrf.py \
    --nudged-dir /wrf/WRF/test/em_real/nudged \
    --control-dir /wrf/WRF/test/em_real/control \
    --output-dir /tmp/output \
    --valid-time 2026-05-25_21:00:00 \
    --obs-json /tmp/observations.json \
    --estaciones-json /tmp/estaciones.json
```

## 7. Output

| Archivo | Descripcion | Tamano |
|---|---|---|
| `wrfout_d01_YYYY-MM-DD_HH:00:00` | Estado del modelo (cada hora) | ~17 MB c/u |
| `rsl.out.0000` | Log de salida | ~100 KB |
| `rsl.error.0000` | Log de errores | ~50 KB |

13 archivos wrfout por corrida (12h de simulacion).

## 8. Contenedor Docker

```bash
# Imagen base
docker pull davegill/wrf-coop:fourteenthtry

# Crear contenedor
docker run -d --name teachme --shm-size=2g \
  -v C:/Users/rober/wrf_data:/wrf/data \
  davegill/wrf-coop:fourteenthtry \
  sleep infinity

# Acceder
docker exec -it teachme bash

# Ejecutar WRF
docker exec teachme bash -c "cd /wrf/WRF/test/em_real && mpirun -np 4 ./wrf.exe"
```

## 9. Referencias

- WRF v4.6.1: https://github.com/wrf-model/WRF
- WPS v4.6.0: https://github.com/wrf-model/WPS
- GFS AWS: https://registry.opendata.aws/noaa-gfs-bdp-pds/
- EcoWitt API: https://doc.ecowitt.net/
- Datos estaticos low-res: https://www2.mmm.ucar.edu/wrf/src/wps_files/WPS_GEOG_LOW_RES.tar.gz
