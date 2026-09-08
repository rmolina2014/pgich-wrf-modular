configuración del espacio geográfico del experimento

Para dominar la simulación atmosférica y el análisis de datos climáticos aplicados a la Argentina, conviene estructurar el aprendizaje en tres etapas clave: **configuración del modelo (WRF)**, **procesamiento de datos (NetCDF con Python)** y **cálculo de índices de impacto ambiental**.

### **1\. Modelado Atmosférico con WRF (*Weather Research and Forecasting*)**

El modelo WRF requiere un entorno Linux (o WSL en Windows) y compiladores como GCC/Gfortran.

* **Preparación de datos de entrada:** Descargar condiciones de frontera e iniciales (como GFS a 0.25° o ERA5) desde el **NCAR Data Archive** o los servidores de la **NOAA**.  
*   
* **WPS (*WRF Preprocessing System*):**  
* 

  1. geogrid.exe: Define el dominio de simulación sobre Argentina (geografía, uso de suelo, topografía).  
  2.   
  3. ungrib.exe: Extrae y lee los archivos meteorológicos en formato GRIB/GRIB2.  
  4.   
  5. metgrid.exe: Interpola horizontalmente las variables meteorológicas al dominio configurado.  
  6.   
* **WRF Core:**  
* 

  1. real.exe: Genera las condiciones iniciales y de borde en la vertical.  
  2.   
  3. wrf.exe: Corre la integración numérica y genera la salida en formato **NetCDF** (wrfout\_d01\_\*).  
  4. 

### **2\. Acceso y Procesamiento de NetCDF con Python**

El ecosistema de Python ofrece librerías optimizadas para trabajar con arreglos multidimensionales (tiempo, niveles verticales, latitud, longitud).

**Herramientas recomendadas:**

* xarray y netcdf4: Manejo eficiente de archivos NetCDF.  
*   
* wrf-python: Cálculo simplificado de variables derivadas (temperatura equivalente, reflectividad, nivel de congelación).  
*   
* matplotlib y cartopy: Visualización cartográfica de alta calidad adaptada a las regiones de Argentina.  
* 

Python  
import xarray as xr  
import wrf  
from netCDF4 import Dataset

\# Cargar salida de WRF  
ncfile \= Dataset("wrfout\_d01\_2026-09-07\_12:00:00")

\# Extraer variables (ejemplo: Temperatura a 2m y Presión)  
T2 \= wrf.getvar(ncfile, "T2") \- 273.15  \# Conversión a °C  
RH2 \= wrf.getvar(ncfile, "rh2")         \# Humedad relativa a 2m

### **3\. Aplicación e Interpretación de Índices Climáticos**

Una vez extraídas las variables meteorológicas de la simulación, se calculan los índices para evaluar riesgos agrometeorológicos y ambientales:

* **ET0 (Evapotranspiración de Referencia \- Penman-Monteith / FAO-56):**  
* 

  * *Inputs necesarios:* Temperatura, humedad relativa, velocidad del viento a 2 m y radiación solar global.  
  *   
  * *Uso en Argentina:* Gestión de riego e hidrología agrícola en regiones como Cuyo, Pampas y NOA.  
  *   
* **ITH (Índice de Temperatura y Humedad):**  
* 

  * *Fórmula básica:* $\\text{ITH} \= (1.8 \\times T \+ 32\) \- (0.55 \- 0.0055 \\times \\text{RH}) \\times (1.8 \\times T \- 26)$  
  *   
  * *Uso en Argentina:* Evaluación de estrés térmico en ganado bovino (leche y carne), crítico en la Cuenca Lechera Santa Fe-Córdoba durante el verano.  
  *   
* **FWI (*Fire Weather Index*):**  
* 

  * *Inputs necesarios:* Temperatura a las 12 PM, humedad relativa, velocidad del viento y precipitación acumulada en 24 h.  
  *   
  * *Uso en Argentina:* Prevención de incendios forestales y de pastizales en el Centro-Norte del país, Sierras de Córdoba y la Patagonia.

Configurar este dominio experimental para Cuyo tiene **aspectos acertados**, pero contiene **dos observaciones críticas de diseño WRF** que debes corregir antes de ejecutar el preprocesamiento (geogrid.exe):

### **Análisis del Dominio**

| Parámetro | Tu Configuración | Evaluación / Recomendación |
| :---- | :---- | :---- |
| **Centro** | $31.5^\\circ\\text{S}, 68.5^\\circ\\text{O}$ | **Excelente.** Cae justo sobre San Juan (cerca del Gran San Juan / Pocito), ideal para enfocar la región. |
| **Proyección** | Mercator | ⚠️ **Inadecuada.** Para latitudes medias (como $31^\\circ\\text{S}-33^\\circ\\text{S}$), la proyección estándar recomendada en WRF es lambert (Lambert Conformal). Mercator amplifica la distorsión fuera de los trópicos. |
| **Resolución** | $15\\text{ km}$ | **Incompleta para Cuyo.** $15\\text{ km}$ sirve para un dominio regional amplio, pero es demasiado gruesa para resolver la Cordillera de los Andes, el Valle del Zonda y las Sierras Pampeanas. |
| **Tamaño** | $80 \\times 60$ celdas | **Ajustado.** A $15\\text{ km}$, cubre $1200 \\times 900\\text{ km}$ (suficiente extensión). Sin embargo, el tamaño de grilla debe optimizarse con factores primos pequeños para la FFT del modelo. |

### **Malla y Cobertura Topográfica ($80 \\times 60$ celdas a $15\\text{ km}$)**

* **Extensión Geográfica:**  
* 

  * **Latitud:** $27.4^\\circ\\text{S}$ a $35.6^\\circ\\text{S}$ (Desde el sur de Catamarca / La Rioja hasta el norte de La Pampa y Mendoza).  
  *   
  * **Longitud:** $74.8^\\circ\\text{O}$ a $62.2^\\circ\\text{O}$ (Desde el Océano Pacífico / Chile hasta Córdoba).  
  *   
* **Cobertura:** Cubre San Juan, Mendoza, San Luis, La Rioja y la barrera andina completa.  
* 

### **Recomendaciones de Optimización**

#### **1\. Proyección Cartográfica**

Cambia la proyección a Lambert Conformal en el archivo namelist.wps:

Fortran  
\&geogrid  
 map\_proj \= 'lambert',  
 ref\_lat   \= \-31.5,  
 ref\_lon   \= \-68.5,  
 truelat1  \= \-30.0,  
 truelat2  \= \-33.0,  
 stand\_lon \= \-68.5,  
/

#### **2\. Dimensiones Compatibles con WRF (Factorización FFT)**

WRF requiere que el número de puntos en $X$ e $Y$ (e\_we y e\_sn) sea divisible por factores $2, 3, 5$.

* Usa **$85 \\times 65$** puntos de grilla en lugar de $80 \\times 60$:  
* 

* Fortran

e\_we \= 85,  
e\_sn \= 65,  
dx \= 15000,  
dy \= 15000,

*   
* 

#### **3\. Anidamiento (*Nesting*) Obligatorio para Cuyo**

Para capturar los vientos locales (como el Viento Zonda) y los gradientes térmicos en valles de cultivo, $15\\text{ km}$ no es suficiente. Se sugiere agregar un dominio interno (*Nest*):

* **Dominio Padre (d01):** $15\\text{ km}$ ($85 \\times 65$ celdas) — Sinóptico.  
*   
* **Dominio Anidado (d02):** $3\\text{ km}$ (Relación 1:5) centrado en San Juan / Valles Cuyanos — Alta resolución.

      \[ Dominio d01 \- 15 km (Cuyo Extendido) \]  
  \+-------------------------------------------------+  
  |                                                 |  
  |             \[ Dominio d02 \- 3 km \]              |  
  |         \+----------------------------+          |  
  |         |  San Juan / Mendoza Norte  |          |  
  |         |   (Resolución Cordillera)  |          |  
  |         \+----------------------------+          |  
  \+-------------------------------------------------+

Aquí tienes la sección \&geogrid completa y optimizada para la región de Cuyo, configurada en el archivo namelist.wps.

Esta configuración incluye:

1. **Dominio Padre (**d01**):** $15\\text{ km}$ de resolución, cubriendo la escala sinóptica (Océano Pacífico, Chile, Cuyo y centro de Argentina).  
2.   
3. **Dominio Anidado (**d02**):** $3\\text{ km}$ de resolución (relación 1:5), enfocado en los valles de San Juan, Mendoza y la alta cordillera para resolver el flujo orográfico y fenómenos locales como el **Viento Zonda**.  
4.   
5. **Proyección Lambert Conformal:** Adecuada para latitudes medias en el hemisferio sur.  
6.   
7. **Dimensiones compatibles con FFT:** Puntos de grilla divididos eficientemente para los algoritmos numéricos de WRF.  
8. 

Fortran  
\&geogrid  
 parent\_id         \=   1,   1,  
 parent\_grid\_ratio \=   1,   5,  
 i\_parent\_start    \=   1,  23,  
 j\_parent\_start    \=   1,  18,  
 e\_we              \=  85, 101,  
 e\_sn              \=  65, 101,  
 \!  
 \! Specification of Grid Cell Size (d01 \= 15 km)  
 \!  
 dx \= 15000,  
 dy \= 15000,  
 \!  
 \! Map Projection: Lambert Conformal para Latitudes Medias  
 \!  
 map\_proj \= 'lambert',  
 ref\_lat   \= \-31.5,  
 ref\_lon   \= \-68.5,  
 truelat1  \= \-30.0,  
 truelat2  \= \-33.0,  
 stand\_lon \= \-68.5,  
 \!  
 \! Coordenadas e interpolación de uso de suelo y topografía  
 \!  
 geog\_data\_res \= 'default','default',  
 geog\_data\_path \= '/ruta/a/tus/datos/geog/'  
/

### **Detalles clave de la configuración:**

* **Relación de anidamiento 1:5 (**parent\_grid\_ratio \= 1, 5**):** Reduce de $15\\text{ km}$ en d01 a $3\\text{ km}$ en d02 de un solo paso.  
*   
* **Ubicación del Nest (**i\_parent\_start \= 23**,** j\_parent\_start \= 18**):** Coloca la esquina inferior izquierda del dominio de $3\\text{ km}$ en una posición balanceada dentro de Cuyo.  
*   
* **Tamaño del Nest (**101 x 101 **puntos):** Ocupa una región aproximada de $300\\text{ km} \\times 300\\text{ km}$, cubriendo todo el Valle del Tulum, Pocito, Ullum, Zonda, la Precordillera y el límite fronterizo con Mendoza y Chile.

Aquí tienes la configuración recomendada del bloque principal para el archivo namelist.input de WRF, adaptada al dominio de dos dominios ($15\\text{ km}$ y $3\\text{ km}$) centrado en Cuyo.

Esta configuración utiliza parametrizaciones optimizadas para terreno complejo/orografía andina y resolución convectiva explícita en el dominio interno ($3\\text{ km}$).

Fortran  
\&time\_control  
 run\_days                 \= 0,  
 run\_hours                \= 48,  
 run\_minutes              \= 0,  
 run\_seconds              \= 0,  
 start\_year               \= 2026, 2026,  
 start\_month              \= 09,   09,  
 start\_day                \= 07,   07,  
 start\_hour               \= 00,   00,  
 end\_year                 \= 2026, 2026,  
 end\_month                \= 09,   09,  
 end\_day                  \= 09,   09,  
 end\_hour                 \= 00,   00,  
 interval\_seconds         \= 21600,  \! Datos de entrada cada 6 horas (ej. GFS)  
 history\_interval         \= 180,  60, \! Guardar d01 cada 3h (180 min) y d02 cada 1h (60 min)  
 frames\_per\_outfile       \= 1,     1,  
 restart                  \= .false.,  
 io\_form\_history          \= 2,      \! Formato NetCDF  
 io\_form\_restart          \= 2,  
 io\_form\_input            \= 2,  
 io\_form\_boundary         \= 2,  
/

\&domains  
 time\_step                \= 90,     \! Regla general: 6 \* dx\_d01 en km (6 \* 15 \= 90 s)  
 time\_step\_fract\_num      \= 0,  
 time\_step\_fract\_den      \= 1,  
 max\_dom                  \= 2,  
 e\_we                     \= 85,  101,  
 e\_sn                     \= 65,  101,  
 e\_vert                   \= 45,   45, \! 45 niveles verticales (recomendado para orografía alta)  
 p\_top\_requested          \= 5000,     \! Tope de la atmósfera a 50 hPa (\~20 km)  
 num\_metgrid\_levels       \= 34,       \! Típico para GFS (ajustar según tu input metgrid)  
 num\_metgrid\_soil\_levels  \= 4,  
 dx                       \= 15000, 3000,  
 dy                       \= 15000, 3000,  
 grid\_id                  \= 1,     2,  
 parent\_id                \= 0,     1,  
 i\_parent\_start           \= 1,    23,  
 j\_parent\_start           \= 1,    18,  
 parent\_grid\_ratio        \= 1,     5,  
 parent\_time\_step\_ratio   \= 1,     5,  
 feedback                 \= 1,  
 smooth\_option            \= 0,  
/

\&physics  
 mp\_physics               \= 6,     6, \! WSM6 (WSM 6-class single-moment) \- Bueno para granizo/nieve  
 ra\_lw\_physics            \= 1,     1, \! RRTM  
 ra\_sw\_physics            \= 1,     1, \! Dudhia  
 radt                     \= 15,    3, \! Frecuencia de cálculo de radiación (en minutos, \~dx en km)  
 sf\_sfclay\_physics        \= 1,     1, \! Monin-Obukhov  
 sf\_surface\_physics       \= 2,     2, \! Noah Land Surface Model (Crucial para humedad de suelo y ET0)  
 bl\_pbl\_physics           \= 1,     1, \! YSU (Yonsai University) \- Excelente para capa límite y Viento Zonda  
 bldt                     \= 0,     0,  
 cu\_physics               \= 1,     0, \! Kain-Fritsch en d01 (15km). DESACTIVADO (0) en d02 (3km)  
 cudt                     \= 5,     0,  
 isfflx                   \= 1,  
 ifsnow                   \= 1,  
 icloud                   \= 1,  
 surface\_input\_source     \= 1,  
 num\_soil\_layers          \= 4,  
 sf\_urban\_physics         \= 0,     0,  
/

\&dynamics  
 w\_damping                \= 1,        \! Amortiguamiento para vientos verticales intensos en montaña  
 diff\_opt                 \= 1,     1,  
 km\_opt                   \= 4,     4,  
 diff\_6th\_opt             \= 0,     0,  
 base\_temp                \= 290\.,  
 damp\_opt                 \= 3,        \! Capa de absorción superior para ondas orográficas  
 dampcoef                 \= 0.2,   0.2,  
 zdamp                    \= 5000\., 5000\.,  
/

\&bdy\_control  
 spec\_bdy\_width           \= 5,  
 spec\_zone                \= 1,  
 relax\_zone               \= 4,  
 specified                \= .true., .false.,  
 nested                   \= .false., .true.,  
/

### **Consideraciones clave para la región de Cuyo:**

1. **Pauta en Convección (**cu\_physics \= 1, 0**):**  
2. 

   * En el dominio de **$3\\text{ km}$ (**d02**)** se coloca cu\_physics \= 0 porque a esta resolución la convección se resuelve de forma explícita (*convective-permitting*). Esto previene doble contabilización de precipitaciones en la precordillera.  
   *   
3. **Número de Niveles Verticales (**e\_vert \= 45**):**  
4. 

   * Es recomendable usar al menos 40–45 niveles para tener buena resolución vertical en la capa límite sobre zonas con grandes diferencias topográficas (desde $600\\text{ m s.n.m.}$ en el Valle hasta $+6000\\text{ m}$ en los Andes).  
   *   
5. **PBL YSU y Land Surface Noah (**bl\_pbl\_physics \= 1**,** sf\_surface\_physics \= 2**):**  
6. 

   * Esta combinación funciona de forma sólida para modelar las inversiones térmicas nocturnas y el calentamiento diurno extremo en valles semiáridos, fundamentales para el cálculo posterior de **ET0** e **ITH**.

