# Experimento WRF + Obs Nudging nativo - caso 2026-08-12 00z (San Juan)

Ciclo completo WRF v4.6.1 (build **smpar/OpenMP**) + ObsNudging con observaciones
EcoWitt reales de 3 estaciones (INTA_POCITO, PUNTA_NEGRA, ECOHUMUS), corrido
**sin Docker y sin mpirun** (1 proceso) con WPS propio (dominio 80x60 @ 15 km).

- Archivo de obs: `tesis_wrf_pgich/historico/obs_flat_20260812.json` (652 registros, 5 min)
- GFS 0.25deg archivos completos (`gfs.t00z.pgrb2.0p25.f{000..012}`)
- Orquestador: `pipeline_wrf.py` -> real.exe + wrf.exe (nudged `obs_nudge_opt=1`) + wrf.exe (control `obs_nudge_opt=0`) + validacion

## Configuracion FDDA (namelist.input de la corrida nudged)

```
grid_fdda = 1,  obs_nudge_opt = 1,  fdda_start = 0.,  fdda_end = 1000.,
obs_rinxy = 50.0,  obs_rinfxy = 500.0,  obs_npfi = 30,  obs_ionf = 1,
max_obs = 10000
```

## Correcciones que hicieron funcionar el ciclo

1. **Formato de datos de superficie (FORMAT 105)**: el reader de WRF
   (`wrf_fddaobs_in.f90`, lineas 816-825) lee las obs de superficie con
   `1x,9(f11.3,1x,f11.3,1x)`; el orden de los 9 pares es
   `slp, ref_pres, height, temperature, u, v, rh, psfc, precip`.
   El conversor `littler_a_obsnud.py` escribe estos 9 pares (NO el formato 104
   de sondeos, que tiene 6 pares y producia SIGSEGV).
2. **Platform**: WRF espera `SYNOP` en los caracteres 7-11 del header. El
   conversor emite `f"{'SYNOP':>11s}" + 5 espacios` (plfo=4). Con plfo=99
   (platform desalineado) el reader avisaba "unknown ob of type SYNOP"
   (cosmetico, no bloquea la aplicacion del nudging).
3. **OpenMP**: al ser build `smpar`, `wrf.exe` debe correr con
   `export OMP_NUM_THREADS=1`. `pipeline_wrf.py` lo exporta en `ejecutar_comando`.
4. **Captura de salida**: `subprocess` con `capture_output=True` (pipe) producia
   un SIGSEGV reproducible en la corrida nudged. El pipeline ahora redirige la
   salida a un archivo temporal (`{{ {cmd} ; }} > {log} 2>&1`).
5. **max_obs = 10000**: con el default (0) el reader no lee obs (NIOBF=0).
6. **Validacion con ventana temporal**: `valida_wrf.py` ahora filtra las obs a
   +/- 30 min del tiempo valido (`--ventana-min 30`). Antes comparaba el campo
   de una hora contra las 652 obs del dia entero.

## Reproduccion

```bash
python pipeline_wrf.py \
  --date 2026-08-12 --hour 00:00 \
  --json tesis_wrf_pgich/historico/obs_flat_20260812.json \
  --case sanjuan_20260812 --run-real
```

Salida en `results/2026-08-12_0000z/sanjuan_20260812/`:
`input/OBS_DOMAIN101`, `nudged/` y `control/` (13 wrfout 00z-12z),
`metricas_resumen.txt`, `scatter_4panels.png`, `mapa_errores_t2.png`,
`tabla_metricas.png`.

## Resultados de validacion (ventana +-30 min)

Formato por variable: `Bias | MAE | RMSE | r` (N = nudged, C = control).

### 00:00 (14 obs) - estado inicial
Nudged == Control (ambas corridas parten del mismo `wrfinput`).

| Variable | Nudged | Control |
|---|---|---|
| T2 (K)   | +3.27 / 3.27 / 3.71 / -0.981 | +3.27 / 3.27 / 3.71 / -0.981 |
| PSFC (hPa) | -9.24 / 9.24 / 12.16 / 0.999 | -9.24 / 9.24 / 12.16 / 0.999 |
| RH (%)   | -17.26 / 17.26 / 17.40 / 0.081 | -17.26 / 17.26 / 17.40 / 0.081 |
| Wind (m/s) | +2.25 / 2.25 / 2.40 / -0.435 | +2.25 / 2.25 / 2.40 / -0.435 |

### 06:00 (26 obs)

| Variable | Nudged | Control |
|---|---|---|
| T2 (K)   | -1.11 / **1.11** / **1.22** / **0.854** | +1.62 / 1.68 / 2.09 / -0.854 |
| PSFC (hPa) | -8.11 / 8.32 / 11.50 / 0.994 | -8.47 / 8.49 / 11.68 / 0.994 |
| RH (%)   | +9.76 / **11.45** / **14.19** | -20.15 / 20.15 / 20.32 |
| Wind (m/s) | +2.09 / 2.20 / 2.26 / -0.162 | +1.98 / 2.01 / 2.23 / +0.162 |

### 12:00 (39 obs)

| Variable | Nudged | Control |
|---|---|---|
| T2 (K)   | -3.16 / 3.16 / 3.39 / +0.031 | -2.60 / **2.60** / **3.01** / -0.495 |
| PSFC (hPa) | -20.31 / 20.31 / 25.37 / 0.992 | -20.44 / 20.44 / 25.44 / 0.992 |
| RH (%)   | +5.25 / **5.44** / **6.88** / **0.587** | -10.34 / 10.34 / 11.49 / -0.715 |
| Wind (m/s) | -0.75 / 1.84 / 2.18 / +0.068 | +0.06 / **1.27** / **1.50** / **0.788** |

## Conclusion

El objetivo del experimento (verificar que el obs nudging asimila de verdad) se
cumple: a las 06z y 12z las corridas nudged y control **difieren**, mientras que
a las 00z (estado inicial) son identicas, confirmando que la asimilacion modifica
la solucion y que NSTA>0 durante todo el ciclo.

- **RH**: mejora consistente (06z y 12z, MAE y RMSE ~la mitad que control).
- **T2**: mejora marcada a 06z (MAE 1.11 vs 1.68); degrada leve a 12z (3.16 vs 2.60).
- **Wind / PSFC**: efecto neutro o leve.

El sesgo PSFC (~-20 hPa a 12z) es sistematico y coincide con el sesgo de elevacion
del modelo vs las estaciones; el nudging no actua sobre psfc directamente.

Pendiente de tuning: coeficiente de relajacion de T (gcoef) y filtro por nivel
para mitigar la degradacion de T2/viento a 12z.
