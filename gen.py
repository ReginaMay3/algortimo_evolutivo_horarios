import csv
import json
import random
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

# Constantes
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
HORAS = ['7:00-8:00', '8:00-9:00', '9:00-10:00', '10:00-11:00', '11:00-12:00', 
         '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00', '17:00-18:00']

# Nueva función para cargar configuración
def cargar_configuracion(config_path='config.json'):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config['semestres_impares'], config['materias_transversales']

class Profesor:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.disponibilidad = defaultdict(list)
        self.materias = []
        self.horario_asignado = defaultdict(list)  # Para rastrear horarios ocupados

# Modificación en la clase Materia
class Materia:
    def __init__(self, nombre: str, semestre: int, horas_semana: int, activa: bool = True):
        self.nombre = nombre
        self.semestre = semestre
        self.horas_semana = horas_semana
        self.profesores = []
        self.activa = activa  # Nuevo campo

# Función para cargar los datos desde los archivos CSV
def cargar_datos(materias_csv: str, profesores_csv: str, materias_transversales: list, semestres_impares: bool):
    materias = {}
    profesores = {}

    # Cargar materias
    with open(materias_csv, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            nombre_materia = row['Materias']
            semestre = int(row['Semestre'])
            horas = int(row['Horas_semana'])
            profesores_materia = [p.strip() for p in row['Profesores'].split(';') if p.strip()]
            
            activa = (semestre % 2 == 1) if semestres_impares else (semestre % 2 == 0)
            activa = activa or (nombre_materia in materias_transversales)
            
            materia = Materia(nombre_materia, semestre, horas, activa)
            materia.profesores = profesores_materia
            materias[nombre_materia] = materia

    # Cargar profesores
    with open(profesores_csv, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            nombre_profesor = row['Nombre']
            profesor = Profesor(nombre_profesor)
            
            # Procesar disponibilidad
            for dia in DIAS:
                if row[dia]:
                    horas_dia = [h.strip() for h in row[dia].split(';')]
                    profesor.disponibilidad[dia] = horas_dia
            
            # Procesar materias que imparte
            if row['Materias']:
                profesor.materias = [m.strip() for m in row['Materias'].split(';')]
            
            profesores[nombre_profesor] = profesor

    return materias, profesores

class Horario:
    def __init__(self, materias: Dict[str, Materia], profesores: Dict[str, Profesor]):
        self.materias = {nombre: m for nombre, m in materias.items() if m.activa}
        self.profesores = profesores
        self.asignaciones = []
        self.fitness = 0
        
    def generar_horario_aleatorio(self):
        # Ordena por dificultad (más horas primero) y semestre
        materias_ordenadas = sorted(
            self.materias.values(),
            key=lambda x: (-x.horas_semana, x.semestre)
        )
        
        for materia in materias_ordenadas:
            intentos_maximos = materia.horas_semana * 2  # Más intentos para materias difíciles
            self.asignar_materia(materia, intentos_maximos)
    
    def asignar_materia(self, materia, max_intentos=200):  # Aumentar intentos
        horas_asignadas = 0
        intentos = 0
        horas_por_dia = defaultdict(list)
        
        # Ordenar profesores por disponibilidad (los más disponibles primero)
        profesores_ordenados = sorted(
            materia.profesores,
            key=lambda p: sum(len(h) for h in self.profesores[p].disponibilidad.values()),
            reverse=True
        )
        
        while horas_asignadas < materia.horas_semana and intentos < max_intentos:
            intentos += 1
            
            # Elegir profesor con más disponibilidad primero
            profesor_nombre = next(
                (p for p in profesores_ordenados 
                if any(h not in self.profesores[p].horario_asignado[d] 
                    for d in DIAS 
                    for h in self.profesores[p].disponibilidad[d])),
                random.choice(materia.profesores)
            )
            profesor = self.profesores[profesor_nombre]
            
            # Intentar asignar horas consecutivas primero
            if horas_por_dia and random.random() < 0.8:  # Mayor probabilidad
                for dia, horas in horas_por_dia.items():
                    if len(horas) >= 2:
                        continue
                    
                    hora_existente = horas[0]
                    idx = HORAS.index(hora_existente)
                    
                    # Probar horas adyacentes
                    for offset in [-1, 1]:
                        if 0 <= idx + offset < len(HORAS):
                            hora_posible = HORAS[idx + offset]
                            if (hora_posible in profesor.disponibilidad[dia] and 
                                hora_posible not in profesor.horario_asignado[dia] and
                                not self._hay_conflicto_semestre(materia, dia, hora_posible)):
                                self._asignar_hora(materia, profesor, dia, hora_posible)
                                horas_por_dia[dia].append(hora_posible)
                                horas_asignadas += 1
                                break
                    if horas_asignadas < materia.horas_semana:
                        break
            
            # Asignación normal si no se pudo consecutivo
            dia, hora = self.encontrar_slot_disponible(profesor, materia)
            if not dia:
                continue
                
            if len(horas_por_dia[dia]) >= 2:
                continue
                
            self._asignar_hora(materia, profesor, dia, hora)
            horas_por_dia[dia].append(hora)
            horas_asignadas += 1

    def _asignar_hora(self, materia, profesor, dia, hora):
        self.asignaciones.append((materia.nombre, profesor.nombre, dia, hora))
        profesor.horario_asignado[dia].append(hora)

    def _hay_conflicto_semestre(self, materia, dia, hora):
        return any(
            a[3] == hora and a[2] == dia and 
            self.materias[a[0]].semestre == materia.semestre
            for a in self.asignaciones
        )
    
    def encontrar_slot_disponible(self, profesor, materia):
        # Mezclar días y horas para aleatoriedad
        dias_disponibles = [dia for dia in DIAS if profesor.disponibilidad[dia]]
        random.shuffle(dias_disponibles)
        
        for dia in dias_disponibles:
            horas_disponibles = [
                h for h in profesor.disponibilidad[dia]
                if h not in profesor.horario_asignado[dia]
            ]
            random.shuffle(horas_disponibles)
            
            for hora in horas_disponibles:
                # Verificar que no haya otra materia del mismo semestre a esta hora
                semestre = materia.semestre
                conflicto = any(
                    a[3] == hora and a[2] == dia and 
                    self.materias[a[0]].semestre == semestre
                    for a in self.asignaciones
                )
                if not conflicto:
                    return dia, hora
        return None, None
    
    def calcular_fitness(self):
        penalizaciones = 0
        recompensas = 0
        
        # 1. Horas faltantes (penalización más fuerte)
        for materia in self.materias.values():
            horas_asignadas = sum(1 for a in self.asignaciones if a[0] == materia.nombre)
            if horas_asignadas < materia.horas_semana:
                penalizaciones += (materia.horas_semana - horas_asignadas) * 20  # Aumentado
        
        # 2. Conflictos de profesores (más severo)
        profesor_horarios = defaultdict(list)
        for _, profesor, dia, hora in self.asignaciones:
            profesor_horarios[(profesor, dia, hora)].append(profesor)
        
        for _, profesores in profesor_horarios.items():
            if len(profesores) > 1:
                penalizaciones += 100  # Aumentado
        
        # 3. Conflictos de semestre
        semestre_horarios = defaultdict(list)
        for materia_nombre, _, dia, hora in self.asignaciones:
            semestre = self.materias[materia_nombre].semestre
            semestre_horarios[(semestre, dia, hora)].append(materia_nombre)
        
        for _, materias in semestre_horarios.items():
            if len(materias) > 1:
                penalizaciones += 50  # Aumentado
        
        # 4. Semestres inactivos (aún más grave)
        for materia_nombre, profesor, dia, hora in self.asignaciones:
            materia = self.materias[materia_nombre]
            if not materia.activa:
                penalizaciones += 200  # Aumentado
        
        # 5. Máximo 2 horas por día por materia
        materia_dias = defaultdict(lambda: defaultdict(int))
        for materia_nombre, _, dia, _ in self.asignaciones:
            materia_dias[materia_nombre][dia] += 1
        
        for materia, dias in materia_dias.items():
            for dia, count in dias.items():
                if count > 2:
                    penalizaciones += 30 * (count - 2)  # Aumentado
        
        # 6. Horas consecutivas (mejorado)
        materia_horarios = defaultdict(lambda: defaultdict(list))
        for materia, _, dia, hora in self.asignaciones:
            materia_horarios[materia][dia].append(hora)
        
        for materia, dias in materia_horarios.items():
            for dia, horas in dias.items():
                if len(horas) > 1:
                    horas_ordenadas = sorted(horas, key=lambda x: HORAS.index(x))
                    consecutivas = True
                    for i in range(len(horas_ordenadas)-1):
                        if HORAS.index(horas_ordenadas[i+1]) != HORAS.index(horas_ordenadas[i]) + 1:
                            consecutivas = False
                            break
                    
                    if not consecutivas:
                        penalizaciones += 50  # Aumentado
                    else:
                        recompensas += 20  # Recompensa por horas consecutivas
        
        # 7. Recompensa por horas completas
        for materia in self.materias.values():
            horas_asignadas = sum(1 for a in self.asignaciones if a[0] == materia.nombre)
            if horas_asignadas == materia.horas_semana:
                recompensas += 10
        
        self.fitness = (1.0 + recompensas) / (1.0 + penalizaciones)
        return self.fitness
    
    def cruzar(self, otro_horario: 'Horario') -> 'Horario':
        hijo = Horario(self.materias, self.profesores)
        
        # Crear diccionarios temporales para las asignaciones de cada padre
        asignaciones_padre1 = defaultdict(list)
        asignaciones_padre2 = defaultdict(list)
        
        for materia, profesor, dia, hora in self.asignaciones:
            asignaciones_padre1[materia].append((dia, hora, profesor))
        
        for materia, profesor, dia, hora in otro_horario.asignaciones:
            asignaciones_padre2[materia].append((dia, hora, profesor))
        
        # Cruza uniforme: para cada materia, elegir aleatoriamente de cuál padre tomar la asignación
        for materia_nombre in self.materias:
            if random.random() < 0.5 and materia_nombre in asignaciones_padre1:
                # Tomar asignaciones del primer padre
                for dia, hora, profesor in asignaciones_padre1[materia_nombre]:
                    if not self.hay_conflicto(hijo, materia_nombre, profesor, dia, hora):
                        hijo.asignaciones.append((materia_nombre, profesor, dia, hora))
                        hijo.profesores[profesor].horario_asignado[dia].append(hora)
            elif materia_nombre in asignaciones_padre2:
                # Tomar asignaciones del segundo padre
                for dia, hora, profesor in asignaciones_padre2[materia_nombre]:
                    if not self.hay_conflicto(hijo, materia_nombre, profesor, dia, hora):
                        hijo.asignaciones.append((materia_nombre, profesor, dia, hora))
                        hijo.profesores[profesor].horario_asignado[dia].append(hora)
        
        return hijo
    
    def hay_conflicto(self, horario, materia_nombre, profesor_nombre, dia, hora):
        # Verificar conflictos con el profesor
        if hora in horario.profesores[profesor_nombre].horario_asignado[dia]:
            return True
        
        # Verificar conflictos con el semestre
        semestre = self.materias[materia_nombre].semestre
        for m, p, d, h in horario.asignaciones:
            if d == dia and h == hora and self.materias[m].semestre == semestre:
                return True
        
        return False
    
    def mutar(self, tasa_mutacion: float = 0.2):  # Aumentar tasa de mutación
        if random.random() < tasa_mutacion:
            # Seleccionar 1-3 materias aleatorias para mutar
            for _ in range(random.randint(1, 3)):
                materia_nombre = random.choice(list(self.materias.keys()))
                materia = self.materias[materia_nombre]
                
                # Eliminar todas las asignaciones de esta materia
                self.asignaciones = [a for a in self.asignaciones if a[0] != materia_nombre]
                
                # Limpiar horarios de profesores
                for profesor in self.profesores.values():
                    for dia in DIAS:
                        profesor.horario_asignado[dia] = [
                            h for h in profesor.horario_asignado[dia]
                            if not any(a[0] == materia_nombre and a[2] == dia and a[3] == h 
                                    for a in self.asignaciones)
                        ]
                
                # Reasignar la materia con más intentos
                self.asignar_materia(materia, max_intentos=200)

def validar_horas_consecutivas(horario: Horario) -> bool:
    """Verifica que las horas de cada materia por día sean consecutivas"""
    materia_horarios = defaultdict(lambda: defaultdict(list))
    for materia, _, dia, hora in horario.asignaciones:
        materia_horarios[materia][dia].append(hora)
    
    problemas = False
    for materia, dias in materia_horarios.items():
        for dia, horas in dias.items():
            if len(horas) > 1:
                horas_ordenadas = sorted(horas, key=lambda x: HORAS.index(x))
                for i in range(len(horas_ordenadas)-1):
                    if HORAS.index(horas_ordenadas[i+1]) != HORAS.index(horas_ordenadas[i]) + 1:
                        print(f"¡Error: Materia {materia} tiene horas no consecutivas el {dia}: {horas_ordenadas}")
                        problemas = True
    return not problemas

def validar_horas_por_dia(horario: Horario) -> bool:
    """Verifica que ninguna materia tenga más de 2 horas por día"""
    materia_dias = defaultdict(lambda: defaultdict(int))
    for materia_nombre, _, dia, _ in horario.asignaciones:
        materia_dias[materia_nombre][dia] += 1
    
    problemas = False
    for materia, dias in materia_dias.items():
        for dia, count in dias.items():
            if count > 2:
                print(f"¡Error: Materia {materia} tiene {count} horas el {dia}!")
                problemas = True
    return not problemas

def validar_profesores(horario: Horario, profesores: Dict[str, Profesor], semestres_impares: bool) -> bool:
    """
    Valida que:
    1. Ningún profesor tenga asignaciones duplicadas en el mismo horario
    2. Las asignaciones correspondan a semestres activos
    """
    for profesor in profesores.values():
        for dia, horas in profesor.horario_asignado.items():
            # 1. Verificar horarios duplicados
            if len(horas) != len(set(horas)):
                print(f"¡Conflicto: Profesor {profesor.nombre} tiene horas duplicadas el {dia}!")
                return False
            
            # 2. Verificar semestres activos
            for hora in horas:
                asignaciones_validas = [
                    a for a in horario.asignaciones
                    if a[1] == profesor.nombre and a[2] == dia and a[3] == hora
                    and ((horario.materias[a[0]].semestre % 2 == 1) == semestres_impares)
                ]
                if not asignaciones_validas:
                    print(f"¡Error: Profesor {profesor.nombre} asignado a semestre inactivo el {dia} a las {hora}!")
                    return False
    return True

# Después de las otras funciones de validación (validar_horas_consecutivas, validar_horas_por_dia, etc.)
def validar_horas_totales(horario: Horario) -> bool:
    """Verifica que todas las materias tengan sus horas completas"""
    problemas = False
    for materia in horario.materias.values():
        horas_asignadas = sum(1 for a in horario.asignaciones if a[0] == materia.nombre)
        if horas_asignadas != materia.horas_semana:
            print(f"¡Error: Materia {materia.nombre} tiene {horas_asignadas}/{materia.horas_semana} horas!")
            problemas = True
    return not problemas

# Algoritmo genético
class AlgoritmoGenetico:
    def __init__(self, materias: Dict[str, Materia], profesores: Dict[str, Profesor], 
                 tamano_poblacion: int = 300, generaciones: int = 1000, 
                 tasa_elitismo: float = 0.2, tasa_mutacion: float = 0.25):
        self.materias = materias
        self.profesores = profesores
        self.tamano_poblacion = tamano_poblacion
        self.generaciones = generaciones
        self.tasa_elitismo = tasa_elitismo
        self.tasa_mutacion = tasa_mutacion
        self.poblacion = []
        
    def inicializar_poblacion(self):
        self.poblacion = []
        for _ in range(self.tamano_poblacion):
            horario = Horario(self.materias, self.profesores)
            horario.generar_horario_aleatorio()
            horario.calcular_fitness()
            self.poblacion.append(horario)
    
    def seleccionar_padres(self) -> List[Horario]:
        # Selección por torneo
        tamano_torneo = 3
        padres = []
        
        for _ in range(2):  # Necesitamos 2 padres
            torneo = random.sample(self.poblacion, min(tamano_torneo, len(self.poblacion)))
            ganador = max(torneo, key=lambda x: x.fitness)
            padres.append(ganador)
        
        return padres
    
    def evolucionar(self):
        self.inicializar_poblacion()
        
        for generacion in range(self.generaciones):
            # Ordenar la población por fitness
            self.poblacion.sort(key=lambda x: x.fitness, reverse=True)
            
            # Seleccionar los mejores (elitismo)
            elite_size = int(self.tasa_elitismo * self.tamano_poblacion)
            nueva_poblacion = self.poblacion[:elite_size]
            
            # Completar la nueva población con descendencia
            while len(nueva_poblacion) < self.tamano_poblacion:
                padres = self.seleccionar_padres()
                hijo = padres[0].cruzar(padres[1])
                hijo.mutar(self.tasa_mutacion)
                hijo.calcular_fitness()
                nueva_poblacion.append(hijo)
            
            self.poblacion = nueva_poblacion
            
            # Mostrar progreso
            if generacion % 10 == 0:
                mejor_fitness = max(h.fitness for h in self.poblacion)
                print(f"Generación {generacion}: Mejor fitness = {mejor_fitness:.4f}")
        
        # Devolver el mejor horario
        self.poblacion.sort(key=lambda x: x.fitness, reverse=True)
        return self.poblacion[0]

def horario_a_json(horario: Horario, semestres_impares: bool) -> Dict:
    resultado = defaultdict(lambda: {
        "semestre": None,
        "materias": defaultdict(lambda: {
            "horas_semana": 0,
            "profesor": None,
            "horarios": []
        })
    })
    
    # Procesar asignaciones
    for materia_nombre, profesor, dia, hora in horario.asignaciones:
        materia = horario.materias[materia_nombre]
        semestre = materia.semestre
        
        if resultado[semestre]["semestre"] is None:
            resultado[semestre]["semestre"] = semestre
        
        mat_info = resultado[semestre]["materias"][materia_nombre]
        mat_info["horas_semana"] = materia.horas_semana
        mat_info["profesor"] = profesor
        mat_info["horarios"].append({
            "dia": dia,
            "hora": hora
        })
    
    # Convertir defaultdict a dict normal y listas
    resultado_final = {}
    for semestre, data in sorted(resultado.items()):
        if (semestre % 2 == 1) == semestres_impares:  # Filtro clave
            data["materias"] = [
                {"nombre": nombre, **info} 
                for nombre, info in data["materias"].items()
            ]
            resultado_final[f"Semestre {semestre}"] = data
    return resultado_final

# Función principal modificada
def main():
    semestres_impares, materias_transversales = cargar_configuracion()
    materias, profesores = cargar_datos('materias.csv', 'profesores.csv', materias_transversales, semestres_impares)
    
    ag = AlgoritmoGenetico(
        materias,
        profesores,
        tamano_poblacion=300,
        generaciones=1000,
        tasa_elitismo=0.2,
        tasa_mutacion=0.25
    )
    
    mejor_horario = ag.evolucionar()
    
    # Validación cruzada
    if not validar_profesores(mejor_horario, profesores, semestres_impares):
        print("¡Se detectaron conflictos graves! Revise los mensajes anteriores.")
    else:
        print("✓ Validación de profesores exitosa")
    
    if not validar_horas_por_dia(mejor_horario):
        print("¡Se detectaron problemas con horas por día!")
    
    # Nueva validación de horas totales
    if not validar_horas_totales(mejor_horario):
        print("¡Se detectaron materias con horas incompletas!")
    
    if not validar_horas_consecutivas(mejor_horario):
        print("¡Se detectaron horas no consecutivas!")
    
    # Validar
    print("\nValidación (Semestres Activos):")
    semestres_activos = {m.semestre for m in mejor_horario.materias.values()}
    for semestre in sorted(semestres_activos):
        print(f"\nSemestre {semestre}:")
        for materia in [m for m in materias.values() if m.semestre == semestre]:
            horas_asignadas = sum(1 for a in mejor_horario.asignaciones if a[0] == materia.nombre)
            print(f"  {materia.nombre}: {horas_asignadas}/{materia.horas_semana} horas")
    
    # Guardar JSON
    horario_json = horario_a_json(mejor_horario, semestres_impares)
    with open('horario_optimizado.json', 'w', encoding='utf-8') as f:
        json.dump(horario_json, f, ensure_ascii=False, indent=2)
    
    print("\nHorario optimizado guardado en 'horario_optimizado.json'")

if __name__ == "__main__":
    main()  # Sin parámetro, ya que se carga desde config.json