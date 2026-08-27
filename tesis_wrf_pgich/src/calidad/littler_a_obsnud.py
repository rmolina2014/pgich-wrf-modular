import math
import sys
import argparse
from pathlib import Path

def parse_littler_custom(filepath):
    """Parsea el formato custom Little_R generado por generador_littler.py:
       Header: estacion(40s) lat(12.5f) lon(12.5f) elev(12.5f) ' ' fecha hora nivel(6d)
       Data:   nivel(6d) n_niveles(6d) temp_K(15.5f) humedad%(15.5f) presion_Pa(15.5f)
               u_ms(15.5f) v_ms(15.5f) direcc(15.5f) rocio_K(15.5f)
       Null:   8 x -999999.00000
    """
    estaciones = []
    with open(filepath) as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n')
        # Detectar fin de archivo (tailer: 7 lineas de -999999 + 1 de ceros)
        stripped = line.strip()
        if stripped.startswith('0000000') or stripped == '':
            i += 1
            continue
        # Header: mínimo 80 chars para tener datos
        if len(line) < 90:
            i += 1
            continue
        # Si la línea empieza con espacios seguido de -999999, es null/fin
        if stripped.replace('.', '').replace('-', '').replace(' ', '').isdigit() and len(stripped) > 50:
            i += 1
            continue
        try:
            estacion = line[:40].strip()
            lat = float(line[40:52].strip())
            lon = float(line[52:64].strip())
            elev = float(line[64:76].strip())
            fecha = line[77:87].strip()
            hora = line[88:96].strip()
        except (ValueError, IndexError):
            i += 1
            continue

        # Data line
        if i + 1 >= len(lines):
            break
        data_line = lines[i + 1]
        try:
            nivel = float(data_line[0:6].strip())
            n_niv = float(data_line[6:12].strip())
            temp_k = float(data_line[12:27].strip()) if len(data_line) >= 27 else -999999.0
            humedad = float(data_line[27:42].strip()) if len(data_line) >= 42 else -999999.0
            presion = float(data_line[42:57].strip()) if len(data_line) >= 57 else -999999.0
            u_val = float(data_line[57:72].strip()) if len(data_line) >= 72 else -999999.0
            speed = float(data_line[72:87].strip()) if len(data_line) >= 87 else -999999.0
            direcc = float(data_line[87:102].strip()) if len(data_line) >= 102 else -999999.0
            rocio = float(data_line[102:117].strip()) if len(data_line) >= 117 else -999999.0
        except (ValueError, IndexError):
            i += 3
            continue

        # Saltar null line
        estaciones.append({
            'nombre': estacion,
            'lat': lat,
            'lon': lon,
            'elev': elev,
            'fecha': fecha,
            'hora': hora,
            'temp_k': temp_k,
            'humedad': humedad,
            'presion': presion,
            'speed': speed,
            'direcc': direcc,
            'rocio': rocio,
        })
        i += 3
    return estaciones


def convertir_a_obsnud(estaciones, output_path):
    """Convierte a formato .obsnud que WRF lee (wrf_fddaobs_in.F format 105)"""
    fmt_h1 = " {:<14s}\n"  # 1x,a14 - date
    fmt_h2 = "  {:<9.4f} {:<9.4f}\n"  # 2x,f9.4,1x,f9.4,1x - lat, lon
    fmt_h3 = "  {:<40s}   {:<40s}   \n"  # 2x,a40,3x,a40,3x
    fmt_h4 = "  {:<16s}  {:<16s}  {:8.0f}  F     F       1\n"
    fmt_data = " " + "{:<11.3f} {:<11.3f}" * 9 + "\n"  # 1x,9(f11.3,1x,f11.3,1x)

    with open(output_path, 'w') as f:
        for obs in estaciones:
            temp = obs['temp_k']
            rh = obs['humedad']
            psfc = obs['presion']
            elev = obs['elev']
            speed = obs['speed']
            direcc = obs['direcc']
            rocio = obs['rocio']
            lat = obs['lat']
            lon = obs['lon']
            nombre = obs['nombre']

            # Convertir fecha a formato YYYYMMDDHHMMSS (14 chars, sin separadores)
            fecha_str = obs['fecha'].replace('-', '')
            hora_str = obs['hora'][:5].replace(':', '') + "00"

            # U, V desde direccion + velocidad (earth-relative, QC=129)
            tiene_viento = (speed > -888888 and direcc > -888888
                           and speed >= 0 and direcc >= 0)

            if tiene_viento:
                rad = math.radians(direcc)
                u_met = -speed * math.sin(rad)
                v_met = -speed * math.cos(rad)
                u_qc = 129.0
                v_qc = 129.0
            else:
                u_met = -888888.0
                v_met = -888888.0
                u_qc = -888888.0
                v_qc = -888888.0

            # QC flags
            def qc(val):
                return 0.0 if val > -888888 else -888888.0

            # Fecha header
            date_char = f"{fecha_str}{hora_str}"
            f.write(fmt_h1.format(date_char))

            # Lat, lon
            f.write(fmt_h2.format(lat, lon))

            # id, namef (40 chars c/u)
            id_str = f"{nombre:<40s}"
            namef_str = f"{'SURFACE':<40s}"
            f.write(fmt_h3.format(id_str, namef_str))

            # platform, source, elevation, is_sound, bogus, meas_count
            # obsproc ubica el tipo en chars 7-11 del campo a16 (wrf_fddaobs_in.f90)
            platform = f"{'SYNOP':>11s}" + " " * 5
            source = f"{nombre:<16s}"
            f.write(fmt_h4.format(platform, source, elev))

            # 9 pares (valor, QC) en el orden del formato 105 de wrf_fddaobs_in.f90
            # (obs de superficie): slp, ref_pres, height(m), temperature(K),
            # u(m/s), v(m/s), rh(%), psfc(Pa), precip
            pares = [
                (-888888.0, -888888.0),   # slp
                (-888888.0, -888888.0),   # ref_pres
                (elev, qc(elev)),          # height (m)
                (temp, qc(temp)),          # temperature (K)
                (u_met, u_qc),             # u wind (m/s)
                (v_met, v_qc),             # v wind (m/s)
                (rh, qc(rh)),              # relative humidity (%)
                (psfc, qc(psfc)),          # surface pressure (Pa; WRF la pasa a kPa)
                (-888888.0, -888888.0),   # precip
            ]
            linea = ""
            for val, qc_val in pares:
                linea += f"{val:11.3f} {qc_val:11.3f} "
            f.write(" " + linea.rstrip() + "\n")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Convierte Little_R a OBS_DOMAIN101 para WRF obs nudging")
    parser.add_argument("--input", "-i", required=True,
                        help="Ruta al archivo Little_R de entrada")
    parser.add_argument("--output", "-o", default=None,
                        help="Ruta de salida para OBS_DOMAIN101 (default: mismo dir que input)")
    parser.add_argument("--container", "-c", default="teachme",
                        help="Nombre del contenedor Docker (default: teachme)")
    parser.add_argument("--no-docker", action="store_true",
                        help="No copiar al contenedor")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"Error: no se encuentra {src}")
        sys.exit(1)

    if args.output:
        dst = Path(args.output)
    else:
        dst = src.parent / "OBS_DOMAIN101"

    estaciones = parse_littler_custom(str(src))
    if not estaciones:
        print(f"Error: no se pudieron parsear estaciones de {src}")
        sys.exit(1)
    print(f"Leídas {len(estaciones)} estaciones")

    convertir_a_obsnud(estaciones, str(dst))
    print(f"Archivo OBS_DOMAIN101 generado: {dst}")

    if not args.no_docker:
        import subprocess
        result = subprocess.run(
            ["docker", "exec", args.container, "mkdir", "-p", "/wrf/WRF/test/em_real"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            subprocess.run(
                ["docker", "cp", str(dst), f"{args.container}:/wrf/WRF/test/em_real/OBS_DOMAIN101"],
                capture_output=True, timeout=30
            )
            print(f"Copiado al contenedor {args.container}:/wrf/WRF/test/em_real/OBS_DOMAIN101")
        else:
            print(f"Contenedor '{args.container}' no disponible, copia manual necesaria")
            print(f"  docker cp {dst} {args.container}:/wrf/WRF/test/em_real/OBS_DOMAIN101")
    else:
        print("Saltando copia al contenedor (--no-docker)")


if __name__ == "__main__":
    main()
