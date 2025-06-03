import json
from collections import defaultdict

# Constantes (deben coincidir con las del generador principal)
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
HORAS = ['7:00-8:00', '8:00-9:00', '9:00-10:00', '10:00-11:00', '11:00-12:00', 
         '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00', '17:00-18:00']

def cargar_horario_json(ruta_json='horario_optimizado.json'):
    """Carga el horario desde el archivo JSON"""
    with open(ruta_json, 'r', encoding='utf-8') as f:
        return json.load(f)

def generar_html_visual(horario_json, archivo_salida='horario_visual.html'):
    """Genera un archivo HTML con la visualización del horario"""
    # Crear estructura HTML
    html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Horario Escolar Generado</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .semestre {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            overflow: hidden;
        }
        h2 {
            background-color: #2c3e50;
            color: white;
            padding: 15px;
            margin: 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
        }
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        .materia {
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 4px;
        }
        .profesor {
            font-size: 0.85em;
            color: #555;
            font-style: italic;
        }
        .hora {
            font-size: 0.8em;
            color: #7f8c8d;
        }
        .bloque-vacio {
            background-color: #f9f9f9;
        }
        @media print {
            body { padding: 0; background: none; }
            .semestre { box-shadow: none; page-break-after: always; }
        }
    </style>
</head>
<body>
"""

    # Generar tabla para cada semestre
    for semestre, datos in horario_json.items():
        html += f"""
    <div class="semestre">
        <h2>{semestre}</h2>
        <table>
            <thead>
                <tr>
                    <th>Hora</th>
                    {''.join(f'<th>{dia}</th>' for dia in DIAS)}
                </tr>
            </thead>
            <tbody>
"""
        # Filas para cada hora
        for hora in HORAS:
            html += f"<tr><td>{hora}</td>"
            
            # Celdas para cada día
            for dia in DIAS:
                contenido = []
                
                # Buscar materias en este slot
                for materia in datos['materias']:
                    for horario in materia['horarios']:
                        if horario['dia'] == dia and horario['hora'] == hora:
                            contenido.append(
                                f'<div class="materia">{materia["nombre"]}</div>'
                                f'<div class="profesor">{materia["profesor"]}</div>'
                            )
                
                if contenido:
                    html += f'<td>{"".join(contenido)}</td>'
                else:
                    html += '<td class="bloque-vacio"></td>'
            
            html += "</tr>"
        
        html += """
            </tbody>
        </table>
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    # Guardar archivo
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Horario visual generado en '{archivo_salida}'")

if __name__ == "__main__":
    print("=== Generador Visual de Horarios ===")
    print("Cargando horario desde 'horario_optimizado.json'...")
    
    try:
        horario = cargar_horario_json()
        generar_html_visual(horario)
        print("\nAbre el archivo HTML en tu navegador para ver el horario.")
    except FileNotFoundError:
        print("\n❌ Error: No se encontró 'horario_optimizado.json'")
        print("Ejecuta primero el generador de horarios principal.")
    except json.JSONDecodeError:
        print("\n❌ Error: El archivo JSON está corrupto o mal formateado")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")