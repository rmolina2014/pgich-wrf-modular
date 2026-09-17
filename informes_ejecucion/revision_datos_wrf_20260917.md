# Revisión de datos de ejecuciones WRF

Fecha de revisión: 2026-09-17. Alcance: copia local de `results/`, `informes_ejecucion/`, `validacion/`, `validacion_20260705/` y artefactos relacionados. No se ejecutó WRF ni se modificaron resultados existentes.

## Verificación directa de las salidas

Se abrieron los 182 archivos `wrfout` con h5py. Todos declaran WRF-Chem V4.5 en `TITLE`. Cada archivo contiene un tiempo interno coincidente con su nombre, sustituyendo los dos puntos por guiones bajos. Se leyeron T2, Q2, PSFC, U10 y V10: no se detectaron valores no finitos ni magnitudes superiores a 1e30 en esas variables. Esto no constituye una comprobación de todas las variables ni una certificación de corrección física.

| Carpeta bajo results/ | Nudged | Control | Cobertura interna |
|---|---:|---:|---|
| 2026-01-01_0000z/caso2_calor | 13 | 13 | 01/01, 00–12Z, horaria |
| 2026-05-16_0000z/caso3_frentefrio | 13 | 13 | 16/05, 00–12Z, horaria |
| 2026-07-31_0000z/caso1_zonda | 13 | 13 | 31/07, 00–12Z, horaria |
| 2026-08-06_0000z/sanjuan_20260806 | 13 | 13 | 06/08, 00–12Z, horaria |
| 2026-08-06_0000z/sens_coef0001 | 13 | 13 | 06/08, 00–12Z, horaria |
| 2026-08-12_0000z/validate | 26 | 26 | Dos ciclos: 12/08 y 13/08, cada uno 00–12Z |

En cada ciclo, las cinco variables comparadas son idénticas entre nudged y control a 00Z y diferentes a 06Z y 12Z. Esto respalda que las parejas comparten esos campos iniciales y evolucionan de manera diferente; no prueba por sí solo que toda la configuración y todas las entradas sean idénticas.

Los tres casos de estudio tienen preflight con todos los chequeos en OK. `estado_casos.json` registra sus ejecuciones el 12 y 13 de septiembre. El consolidado fue generado el 16 de septiembre: esa fecha no representa una nueva ejecución.

## Resultado cuantitativo de los casos recientes

Porcentajes calculados a partir de `tabla_evolutiva.json`: 100 × (RMSE control − RMSE nudged) / RMSE control. Positivo significa reducción del error; negativo, aumento. No se recalcularon las métricas desde las observaciones.

| Caso | T2 06Z | T2 12Z | RH 06Z | RH 12Z | Viento 06Z | Viento 12Z |
|---|---:|---:|---:|---:|---:|---:|
| Zonda | +27,52% | +1,62% | +16,38% | −4,63% | +18,25% | +36,20% |
| Calor | +10,68% | +6,00% | +30,16% | +3,94% | −46,23% | +25,52% |
| Frente frío | +20,80% | −9,81% | +24,40% | +26,84% | −54,53% | −31,70% |
| Sensibilidad 06/08 | +27,04% | −16,07% | +13,04% | +43,93% | +24,35% | −15,48% |

La mejora no es uniforme. En Zonda a 12Z, T2 conserva RMSE 9,13 K y bias −8,87 K pese a la pequeña mejora relativa. En frente frío, la temperatura empeora a 12Z y el viento empeora en ambos horarios evaluados. El consolidado de los tres casos coincide, al redondeo mostrado, con los valores T2/RH de sus JSON.

## Hallazgos de trazabilidad e interpretación

1. **Dos ciclos en una carpeta.** `2026-08-12_0000z/validate` contiene archivos con `SIMULATION_START_DATE` 2026-08-12 y 2026-08-13. Son dos inicializaciones de 12 horas, no una corrida continua de 36 horas. Su `metricas_resumen.txt` evalúa únicamente el 12/08 a 00Z, cuando ambas corridas aún son idénticas. No documenta el efecto posterior del nudging ni el segundo ciclo. Conviene separar por fecha de inicialización y generar métricas por ciclo.

2. **Conclusión de coeficiente óptimo no sustentada.** `INFORME_EJECUCION_2026-09-10_sens_coef0001.md` compara sensibilidad a 12Z con base a 06Z y afirma que el óptimo está entre 0.0001 y 0.0002. El propio informe reconoce la diferencia horaria. Es necesario comparar ambos experimentos a los mismos tiempos y con las mismas observaciones. Los resultados archivados sí respaldan mejora de RH frente a control a 12Z, pero no permiten deducir ese intervalo óptimo.

3. **Faltan logs y manifiestos en esta copia.** No se encontraron archivos `rsl*`, `.log` ni manifiestos de control. `sanjuan_20260806` conserva estados OK/DONE. Hay evidencia de salidas hasta 12Z, pero no se pueden comprobar directamente mensajes de finalización, reintentos, duración ni procedencia exacta del binario y las entradas. La ausencia local no demuestra que esos registros no existan en la máquina de ejecución.

4. **N no equivale a estaciones independientes.** Los resúmenes repiten estaciones para distintas observaciones. Por ejemplo, `validate/metricas_resumen.txt` contiene 14 registros de dos estaciones; `sanjuan_20260806/metricas_resumen.txt` contiene 65 registros de cinco estaciones aunque su título dice siete. Deben distinguirse cantidad de pares, cantidad de estaciones y ventana temporal al interpretar las métricas.

5. **Validaciones históricas con metadatos distintos.** `validacion/metricas_resumen.txt` usa coordenadas y elevaciones diferentes del catálogo actual. Por ejemplo, INTA_POCITO figura en −31.5678, −67.8901, 580 m, frente a −31.6500, −68.5833, 615 m en `config/estaciones.json`. Sus resultados no deben combinarse con los actuales sin aclarar la versión del catálogo. `validacion_20260705/` conserva métricas y gráficos, pero no se localizaron sus wrfout en results/.

6. **Carpetas de preparación, sin evidencia local de corrida.** `2026-05-25_2100z/base` y `2026-08-06_0000z/refactor_test` contienen entradas, pero no wrfout. No corresponde clasificarlas como ejecuciones completas a partir de esta copia.

7. **Namelists y descripción literal.** En los tres casos y en sensibilidad, los namelists difieren en `obs_nudge_opt` y también en los tres `obs_coef_*` (0.0001 en nudged y 0.0005 en control). La frase «solo cambia obs_nudge_opt» no describe literalmente los archivos archivados. Esta diferencia debe documentarse; por sí sola no demuestra un efecto de los coeficientes en una corrida cuyo nudging está desactivado.

## Prioridad de trabajo

Conservar los resultados originales. Separar los ciclos mezclados; recuperar logs/manifiestos desde la máquina de ejecución; comparar base y sensibilidad en horarios coincidentes; explicitar estaciones, pares y metadatos de cada validación. Las salidas revisadas respaldan ejecuciones con evolución diferencial, pero las conclusiones deben expresar tanto mejoras como degradaciones.
