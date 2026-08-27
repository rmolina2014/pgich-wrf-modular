# Instrucciones para subir el proyecto a GitHub

El proyecto ha sido preparado para subir al repositorio `https://github.com/rmolina2014/pgich-wrf-modular.git`, pero se necesita autenticación.

## Pasos para completar la subida:

### 1. Verificar que el repositorio existe
- Asegúrate de que el repositorio `pgich-wrf-modular` existe en la cuenta `rmolina2014`
- Si no existe, créalo en GitHub

### 2. Configurar autenticación

#### Opción A: Usar token de acceso personal (recomendado)
1. Ve a GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Genera un nuevo token con permisos de `repo`
3. Copia el token

#### Opción B: Configurar credenciales en Windows
```powershell
# Configurar credenciales
git config --global credential.helper manager

# Luego intentar push nuevamente
git push -u origin master
```

#### Opción C: Usar SSH (si tienes clave SSH configurada)
```bash
# Cambiar el remoto a SSH
git remote set-url origin git@github.com:rmolina2014/pgich-wrf-modular.git

# Luego hacer push
git push -u origin master
```

### 3. Ejecutar el push

Una vez configurada la autenticación, ejecuta:

```bash
git push -u origin master
```

O si prefieres crear una rama main:

```bash
# Renombrar branch master a main
git branch -M main
git push -u origin main
```

## Estructura subida al repositorio:

✅ **Archivos incluidos:**
- `src/` - Código fuente modular organizado por funcionalidad
- `config/` - Archivos de configuración y templates
- `wps_sanjuan/` - Configuración específica para dominio San Juan
- `scripts/` - Scripts exploratorios y de desarrollo
- `tests/` - Pruebas del sistema
- `pipeline_wrf.py` - Pipeline principal de ejecución
- `README.md` - Documentación del proyecto
- `LICENSE` - Licencia MIT
- `pyproject.toml` - Dependencias de Python

✅ **Excluidos (en .gitignore):**
- `data/` - Datos crudos y procesados (grandes)
- `results/` - Resultados de simulaciones
- `plots/` - Gráficos generados
- Entornos virtuales
- Archivos temporales y logs
- Archivos de IDE
- Archivos binarios y ejecutables

## Notas importantes:

1. **Datos excluidos**: Los datos observacionales y resultados de WRF no se incluyen por su tamaño
2. **Configuraciones locales**: Las rutas absolutas en algunos archivos pueden necesitar ajustes
3. **Duplicaciones**: Existe código duplicado entre `src/` y `tesis_wrf_pgich/src/` que podría consolidarse
4. **Credenciales**: No se incluyen archivos `.env` con credenciales

## Próximos pasos recomendados:

1. Consolidar código duplicado entre `src/` y `tesis_wrf_pgich/src/`
2. Crear un archivo `.env.example` con variables de configuración
3. Agregar documentación más detallada de uso
4. Configurar GitHub Actions para pruebas automáticas
5. Agregar badges al README.md (build status, coverage, etc.)

## Comandos ejecutados hasta ahora:

```bash
# Inicialización del repositorio
git init
git remote add origin https://github.com/rmolina2014/pgich-wrf-modular.git

# Agregar archivos principales
git add .gitignore LICENSE README.md pyproject.toml uv.lock .python-version
git add src/ config/ wps_sanjuan/ scripts/ tests/
git add pipeline_wrf.py probar_circuito.py namelist.input namelist.wps
git add tesis_wrf_pgich/src/ tesis_wrf_pgich/app.py tesis_wrf_pgich/main.py

# Commit inicial
git commit -m "Initial commit: PGICH WRF Modular System..."

# Falta: git push -u origin master (requiere autenticación)
```

Para cualquier problema con la autenticación, consulta la documentación oficial de GitHub sobre autenticación: https://docs.github.com/en/authentication