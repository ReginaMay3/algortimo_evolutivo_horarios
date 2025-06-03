import json
from collections import defaultdict

DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
HORAS = ['7:00-8:00', '8:00-9:00', '9:00-10:00', '10:00-11:00', '11:00-12:00', 
         '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00', '17:00-18:00']

def cargar_horario(ruta_json='horario_optimizado.json'):
    with open(ruta_json, 'r', encoding='utf-8') as f:
        return json.load(f)

def generar_horario_profesores(horario_json):
    # Primero organizamos los datos por profesor
    profesores = defaultdict(lambda: {dia: [] for dia in DIAS})
    
    for semestre, datos in horario_json.items():
        for materia in datos['materias']:
            profesor = materia['profesor']
            if profesor == "Sin asignar":
                continue
                
            for horario in materia['horarios']:
                dia = horario['dia']
                hora = horario['hora']
                profesores[profesor][dia].append({
                    'hora': hora,
                    'materia': materia['nombre'],
                    'semestre': semestre
                })
    
    return profesores

def generar_html_profesores(horario_profesores, archivo_salida='horario_profesores.html'):
    html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Horarios - Vista Profesores</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .profesor {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            overflow: hidden;
        }
        h2 {
            background-color: #27ae60;
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
            background-color: #2ecc71;
            color: white;
            font-weight: bold;
        }
        .materia {
            font-weight: bold;
            color: #2c3e50;
        }
        .semestre {
            font-size: 0.85em;
            color: #7f8c8d;
            font-style: italic;
        }
        .hora {
            font-weight: bold;
            color: #e74c3c;
        }
        .bloque-vacio {
            background-color: #f9f9f9;
        }
        .nav-profesores {
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .nav-profesores a {
            display: inline-block;
            padding: 8px 15px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        .nav-profesores a:hover {
            background-color: #2980b9;
        }
        @media print {
            body { padding: 0; background: none; }
            .profesor { box-shadow: none; page-break-after: always; }
            .nav-profesores { display: none; }
        }
    </style>
</head>
<body>
    <h1>Horarios - Vista Profesores</h1>
    <div class="nav-profesores" id="indice-profesores">
        <!-- Se llena con JavaScript -->
    </div>
"""

    # Generar sección para cada profesor
    for profesor, horarios in horario_profesores.items():
        html += f"""
    <div class="profesor" id="prof-{profesor.replace(' ', '-')}">
        <h2>{profesor}</h2>
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
            html += f"<tr><td class='hora'>{hora}</td>"
            
            # Celdas para cada día
            for dia in DIAS:
                clases = [clase for clase in horarios[dia] if clase['hora'] == hora]
                
                if clases:
                    contenido = []
                    for clase in clases:
                        contenido.append(
                            f'<div class="materia">{clase["materia"]}</div>'
                            f'<div class="semestre">{clase["semestre"]}</div>'
                        )
                    html += f'<td>{"".join(contenido)}</td>'
                else:
                    html += '<td class="bloque-vacio"></td>'
            
            html += "</tr>"
        
        html += """
            </tbody>
        </table>
    </div>
"""
    
    # JavaScript para navegación
    html += """
<script>
    // Crear índice de profesores
    const profesores = document.querySelectorAll('.profesor');
    const indice = document.getElementById('indice-profesores');
    
    profesores.forEach(prof => {
        const nombre = prof.querySelector('h2').textContent;
        const id = prof.id;
        const link = document.createElement('a');
        link.href = '#' + id;
        link.textContent = nombre;
        indice.appendChild(link);
    });
</script>
</body>
</html>
"""
    
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Horario para profesores generado en '{archivo_salida}'")

if __name__ == "__main__":
    print("=== Visualizador de Horarios para Profesores ===")
    print("Cargando datos desde 'horario_optimizado.json'...")
    
    try:
        horario = cargar_horario()
        horario_profesores = generar_horario_profesores(horario)
        generar_html_profesores(horario_profesores)
        
        print("\nInstrucciones:")
        print("1. Abre el archivo HTML en tu navegador")
        print("2. Usa los botones al inicio para navegar a cada profesor")
        print("3. Puedes imprimir los horarios (Ctrl+P)")
    except FileNotFoundError:
        print("\n❌ Error: No se encontró 'horario_optimizado.json'")
        print("Ejecuta primero el generador de horarios principal.")
    except json.JSONDecodeError:
        print("\n❌ Error: El archivo JSON está corrupto o mal formateado")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")