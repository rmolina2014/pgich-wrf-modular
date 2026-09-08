#!/usr/bin/env python3
"""
App Streamlit del Pipeline WRF nativo (sin Docker).

Expone pipeline_wrf.py a traves de una interfaz web para preparar y ejecutar
el circuito de asimilacion de observaciones PGICH en el modelo WRF local.

Uso:
    uv run streamlit run app_streamlit.py
"""

import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

import pipeline_wrf as pw  # noqa: E402


def mostrar_archivo(path, titulo: str, max_lines: int = 40):
    if path:
        path_obj = Path(path)
        if path_obj.exists():
            with st.expander(titulo, expanded=False):
                st.code(path_obj.read_text(encoding="utf-8", errors="ignore"))
            return
    st.info(f"No se encontro {titulo}: {path}")


def graficar_observaciones(df: pd.DataFrame):
    """Genera un grafico de observaciones por estacion (matplotlib)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    estaciones = df["estacion"].unique()
    variables = {
        "temp": ("Temperatura (°C)", "tab:red"),
        "presion_absoluta": ("Presión absoluta (hPa)", "tab:blue"),
        "viento": ("Viento (km/h)", "tab:green"),
        "humedad": ("Humedad (%)", "tab:orange"),
    }

    fig, axes = plt.subplots(len(variables), 1, figsize=(10, 2.4 * len(variables)), sharex=True)
    if len(variables) == 1:
        axes = [axes]

    for ax, (var, (label, color)) in zip(axes, variables.items()):
        if var not in df.columns:
            continue
        for est in estaciones:
            sub = df[df["estacion"] == est]
            ax.plot(sub.index, pd.to_numeric(sub[var], errors="coerce"),
                    marker="o", label=est, color=plt.cm.tab10(hash(est) % 10))
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    if "estacion" in df.columns and "time_unix" not in df.columns:
        axes[0].set_title("Observaciones por estación")
    axes[-1].set_xlabel("Índice de registro")
    fig.tight_layout()
    return fig


def fecha_wrfinput_disponible():
    """Lee la fecha (Times) del wrfinput_d01 en el run dir, si existe."""
    try:
        import xarray as xr

        fi = pw.LOCAL_WRF_DIR / "wrfinput_d01"
        if not fi.exists():
            return None
        ds = xr.open_dataset(fi)
        times = list(ds["Times"].values)
        ds.close()
        return times[0].decode() if times else None
    except Exception:
        return None


def inyectar_estilos():
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }

        .pgich-hero {
            background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 55%, #3B82F6 100%);
            padding: 1.75rem 2rem;
            border-radius: 14px;
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 18px rgba(37, 99, 235, 0.25);
        }
        .pgich-hero h1 {
            color: white; font-size: 1.9rem; margin: 0 0 0.4rem 0; line-height: 1.2;
        }
        .pgich-hero p { color: #DBEAFE; margin: 0; font-size: 0.95rem; }
        .pgich-hero code {
            background: rgba(255,255,255,0.15); color: #EFF6FF;
            padding: 0.1rem 0.4rem; border-radius: 4px;
        }

        .pgich-section {
            font-size: 1.15rem; font-weight: 600; color: #1E3A8A;
            border-bottom: 2px solid #DBEAFE;
            padding-bottom: 0.4rem; margin: 1.8rem 0 1rem 0;
        }

        [data-testid="stMetric"] {
            background: #F8FAFC; border: 1px solid #E2E8F0;
            border-radius: 10px; padding: 0.9rem 1rem 0.6rem 1rem;
        }
        [data-testid="stMetricLabel"] { color: #475569; }

        .stButton > button { border-radius: 8px; font-weight: 600; }

        [data-testid="stSidebar"] { background: #F8FAFC; }
        [data-testid="stSidebar"] h2 { color: #1E3A8A; }

        .pgich-footer {
            text-align: center; color: #64748B; font-size: 0.85rem;
            padding-top: 1rem; margin-top: 2rem; border-top: 1px solid #E2E8F0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def seccion(titulo: str):
    st.markdown(f'<div class="pgich-section">{titulo}</div>', unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="Pipeline WRF PGICH",
        page_icon="🌦️",
        layout="wide",
    )
    inyectar_estilos()

    st.markdown(
        f"""
        <div class="pgich-hero">
          <h1>🌦️ Pipeline WRF PGICH</h1>
          <p>Asimilación de observaciones · WRF nativo (sin Docker) ·
             corriendo sobre <code>{pw.LOCAL_WRF_DIR}</code></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Fecha del wrfinput disponible (para alinear la corrida)
    wrf_fecha = fecha_wrfinput_disponible()
    fecha_default = date(2026, 8, 13)
    hora_default = "00:00"
    if wrf_fecha:
        try:
            dt0 = pd.to_datetime(wrf_fecha)
            fecha_default = dt0.date()
            hora_default = dt0.strftime("%H:%M")
        except Exception:
            pass

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Configuración")
        fecha = st.date_input("Fecha de inicio", value=fecha_default)
        hora = st.text_input("Hora UTC (HH:MM)", value=hora_default)
        if wrf_fecha:
            st.caption(
                f"ℹ️ El wrfinput_d01 del run dir es del **{wrf_fecha}**. "
                "Para correr WRF sin regenerar, la fecha debe coincidir."
            )
        caso = st.text_input("Caso", value="base")
        namelist = st.text_input(
            "Namelist.input base",
            value=str(Path(__file__).parent / "namelist.input"),
        )
        json_path = st.text_input(
            "JSON de estaciones (data/raw)",
            value="data/raw/obs_flat_20260813.json",
        )

        st.markdown("---")
        st.subheader("🔧 WRF local")
        st.write(f"**Run dir:** {pw.LOCAL_WRF_DIR}")
        st.write(f"**Env bash:** {pw.WRF_ENV_BASH}")
        st.write(f"**NP:** {pw.WRF_NP}")

        st.markdown("---")
        modo = st.radio(
            "Modo de ejecución",
            ["Solo preparar (JSON → Little_R + OBS_DOMAIN101)",
             "Pipeline completo (preparar + WRF + control + validar)"],
        )
        if "completo" in modo:
            st.warning("El pipeline ejecutará wrf.exe local (puede tardar horas).")
            usar_real = st.checkbox(
                "Regenerar wrfinput/wrfbdy con real.exe "
                "(solo si faltan o están vacíos; si ya existen válidos se reutilizan)",
                value=True,
            )
        else:
            usar_real = False

    # --- VERIFICACIONES ---
    seccion("🔍 Estado del entorno")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ok = pw.check_run_dir()
            st.metric("WRF run dir", "✅ OK" if ok else "❌", str(pw.LOCAL_WRF_DIR), delta_color="off")
        with c2:
            ok_env = Path(pw.WRF_ENV_BASH).exists()
            st.metric("Env bash", "✅ OK" if ok_env else "❌", pw.WRF_ENV_BASH, delta_color="off")
        with c3:
            ok_est = pw.ESTACIONES_JSON.exists()
            st.metric("Estaciones", "✅ OK" if ok_est else "❌", str(pw.ESTACIONES_JSON), delta_color="off")
        with c4:
            ok_meta = list(pw.ESTACIONES_JSON.exists() and
                           __import__("json").load(open(pw.ESTACIONES_JSON)) if pw.ESTACIONES_JSON.exists() else [])
            st.metric("Metadatos estaciones", f"✅ {len(ok_meta)}" if ok_meta else "❌", "config/estaciones.json", delta_color="off")

    _json_abs = Path(json_path)
    if not _json_abs.is_absolute():
        _json_abs = Path.cwd() / json_path

    if _json_abs.exists():
        st.success(f"JSON de estaciones encontrado: `{_json_abs}`")
    elif not json_path:
        st.info("Indicá la ruta a un JSON de observaciones.")
    else:
        st.error(f"No se encuentra el JSON: `{_json_abs}`")

    # --- PREVISUALIZACIÓN DE DATOS ---
    p_json = Path(_json_abs)
    if p_json.exists():
        raw = pd.read_json(p_json)
        seccion("📄 Datos crudos")
        st.dataframe(raw)

    # --- ACCIONES ---
    seccion("🚀 Acciones")

    with st.container(border=True):
        b1, b2, b3 = st.columns(3)
        with b1:
            ejecutar_prepare = st.button("1️⃣ Preparar OBS_DOMAIN101", type="secondary", use_container_width=True)
        with b2:
            ejecutar_completo = st.button("2️⃣ Ejecutar pipeline completo", type="primary", use_container_width=True)
        with b3:
            ver_ultimo = st.button("3️⃣ Ver archivos del último caso", use_container_width=True)

    results_dir = pw.RESULTS_DIR / f"{fecha.strftime('%Y-%m-%d')}_{hora.replace(':', '')}z" / caso
    input_dir = results_dir / "input"
    hourly = {"run_real": usar_real, "skip_control": False}

    if ejecutar_prepare or ejecutar_completo:
        if not p_json.exists():
            st.error(f"JSON no encontrado: `{p_json}` abortando.")
        else:
            with st.spinner("Procesando observaciones (pasos 1-3)..."):
                try:
                    littler_path, timestamp, df = pw.generar_littler_desde_json(
                        str(p_json), input_dir
                    )
                    # Solo estaciones con metadatos geograficos (evita obs con lat/lon=0)
                    import json as _json
                    if pw.ESTACIONES_JSON.exists():
                        meta = _json.load(open(pw.ESTACIONES_JSON))
                        df = df[df["estacion"].isin(meta)].copy()
                    obsdomain = pw.generar_obsdomain(df, input_dir, pw.LOCAL_WRF_DIR, no_copiar=False)
                except Exception as e:
                    st.error(f"Error al preparar: {type(e).__name__}: {e}")
                    st.stop()

            if obsdomain:
                st.success("OBS_DOMAIN101 generado y copiado al run dir de WRF.")
            else:
                st.warning("OBS_DOMAIN101 generado pero no se copió al run dir.")

            with st.container():
                seccion("📊 Observaciones procesadas")
                st.dataframe(df)
                fig = graficar_observaciones(df)
                st.pyplot(fig)

                st.subheader("Archivos generados")
                st.write(f"- **CSV:** `{input_dir / f'datos_validados_{timestamp}.csv'}`")
                st.write(f"- **Little_R:** `{littler_path}`")
                st.write(f"- **OBS_DOMAIN101:** `{obsdomain}`")

            mostrar_archivo(obsdomain, "📄 OBS_DOMAIN101")
            mostrar_archivo(littler_path, "📄 Little_R")

            if ejecutar_completo:
                seccion("🌀 Ejecutando WRF (shell script via setsid)")
                st.info(
                    "La corrida WRF corre en un shell script lanzado con setsid para "
                    "evitar el crash de wrf.exe con obs nudging dentro del servidor "
                    "Streamlit. Puede tardar varios minutos (nudged + control)."
                )

                if st.session_state.get("wrf_corriendo", False):
                    st.warning(
                        "Ya hay una corrida WRF en curso. Esperá a que termine "
                        "antes de lanzar otra (el run dir WRF no soporta corridas "
                        "simultaneas y se corrompen entre si)."
                    )
                    ok_nudged = False
                    ok_control = False
                else:
                    # Preparar namelists en Python (operaciones ligeras, no wrf.exe)
                    case_dir = pw.RESULTS_DIR / f"{fecha.strftime('%Y-%m-%d')}_{hora.replace(':', '')}z" / caso
                    case_dir.mkdir(parents=True, exist_ok=True)
                    start_dt = None
                    try:
                        start_dt = datetime.strptime(f"{fecha.strftime('%Y-%m-%d')} {hora}", "%Y-%m-%d %H:%M")
                    except ValueError:
                        pass
                    namelist_nudged = case_dir / "namelist_nudged.input"
                    pw.preparar_namelist(namelist, 1, str(namelist_nudged), start_dt=start_dt)
                    if not hourly["skip_control"]:
                        namelist_control = case_dir / "namelist_control.input"
                        pw.preparar_namelist(namelist, 0, str(namelist_control), start_dt=start_dt)

                    # Escribir el script shell a un archivo temporal
                    log_file = f"/tmp/wrf_pipeline_{fecha.strftime('%Y%m%d')}_{hora.replace(':', '')}.log"
                    status_file = f"/tmp/wrf_pipeline_{fecha.strftime('%Y%m%d')}_{hora.replace(':', '')}.status"
                    # Limpiar status anterior
                    Path(status_file).write_text("")
                    Path(log_file).write_text("")

                    shell_script = Path(__file__).parent / "run_full_pipeline.sh"
                    cmd = [
                        "bash", str(shell_script),
                        str(pw.LOCAL_WRF_DIR),       # run_dir
                        str(pw.WRF_ENV_BASH),         # env_bash
                        str(namelist),                 # namelist base
                        str(case_dir),                 # case_dir
                        "yes" if hourly["run_real"] else "no",
                        "yes" if hourly["skip_control"] else "no",
                        log_file,                      # log_file
                        status_file,                   # status_file
                    ]

                    st.code(f"# Lanzado en nueva sesion con FDs cerrados\n"
                            f"# (start_new_session + close_fds para aislar wrf.exe)\n"
                            f"bash run_full_pipeline.sh ...", language="bash")
                    st.caption(f"Log: `{log_file}`")

                    st.session_state["wrf_corriendo"] = True
                    log_box = st.empty()
                    log_lines = []
                    ok_nudged = False
                    ok_control = False

                    proc = subprocess.Popen(
                        cmd,
                        cwd=str(Path(__file__).parent),
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                        close_fds=True,
                    )

                    progress_file = case_dir / "wrf_progress.log"
                    try:
                        proc_logged = 0
                        while proc.poll() is None:
                            time.sleep(3)
                            # Leer el progress-file del script (solo lineas del
                            # propio script, no el volcado bruto de wrf.exe)
                            try:
                                with open(progress_file, "r") as fh:
                                    p_lines = fh.read().strip().split("\n")
                                p_lines = [l for l in p_lines if l]
                                if len(p_lines) > proc_logged:
                                    new_lines = p_lines[proc_logged:]
                                    proc_logged = len(p_lines)
                                    log_lines.extend(new_lines)
                                    log_box.code("\n".join(log_lines[-80:]), language="bash")
                                    # Detectar el resultado final marcado por el script
                                    for line in new_lines:
                                        if "nudged OK" in line:
                                            ok_nudged = True
                                        if "control OK" in line:
                                            ok_control = True
                            except FileNotFoundError:
                                pass
                            # Si el status_file ya tiene resultado final, el pipeline
                            # termino -> leer como fallback
                            try:
                                fs = Path(status_file).read_text().strip()
                                if fs in ("DONE", "NUDGED_FAIL", "CONTROL_FAIL", "REAL_FAIL"):
                                    break
                            except FileNotFoundError:
                                pass
                    finally:
                        st.session_state["wrf_corriendo"] = False

                    # Leer resultado final
                    try:
                        final_status = Path(status_file).read_text().strip()
                    except FileNotFoundError:
                        final_status = "UNKNOWN"

                    # Re-leer log completo
                    try:
                        with open(log_file, "r") as fh:
                            all_lines = fh.read().strip().split("\n")
                        log_box.code("\n".join(all_lines[-120:]), language="bash")
                    except FileNotFoundError:
                        pass

                    ok_nudged = final_status in ("DONE",) and ok_nudged
                    ok_control = final_status == "DONE" and ok_control
                    if final_status == "NUDGED_FAIL":
                        ok_nudged = False
                        ok_control = False
                    elif final_status == "CONTROL_FAIL":
                        ok_control = False

                st.session_state["ok_nudged"] = ok_nudged
                st.session_state["ok_control"] = ok_control

                st.write(f"**WRF nudged:** {'✅ OK' if ok_nudged else '❌ FAILED'}")
                if not hourly["skip_control"]:
                    st.write(f"**WRF control:** {'✅ OK' if ok_control else '❌ FAILED'}")

    if ver_ultimo:
        st.markdown(f"### 📁 Archivos de `{caso}`")
        if results_dir.exists():
            for f in sorted(results_dir.rglob("*")):
                if f.is_file():
                    st.write(f"- `{f.relative_to(results_dir)}`")
        else:
            st.info(f"No existe el directorio: `{results_dir}`")

    st.markdown(
        '<div class="pgich-footer">🌦️ <b>PGICH v0.2.0</b> — Pipeline WRF modular (nativo, sin Docker)</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
