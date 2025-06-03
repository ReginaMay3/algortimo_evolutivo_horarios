import csv
import json
import random
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

# Constantes
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
HORAS = ['7:00-8:00', '8:00-9:00', '9:00-10:00', '10:00-11:00', '11:00-12:00', 
         '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00', '17:00-18:00']

# --- Funciones de carga de datos ---
def cargar_configuracion(config_path='config.json'):
    """Carga la configuración desde archivo JSON"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config.get('semestres_impares', True), config.get('materias_transversales', [])

def cargar_datos(materias_csv: str, profesores_csv: str, materias_transversales: list, semestres_impares: bool):
    """Carga los datos de materias y profesores desde CSV"""
    materias = {}
    profesores = {}

    # Cargar materias
    with open(materias_csv, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            nombre = row['Materias']
            semestre = int(row['Semestre'])
            horas = int(row['Horas_semana'])
            profesores_materia = [p.strip() for p in row['Profesores'].split(';') if p.strip()]
            
            activa = (semestre % 2 == 1) if semestres_impares else (semestre % 2 == 0)
            activa = activa or (nombre in materias_transversales)
            
            materias[nombre] = Materia(nombre, semestre, horas, activa)
            materias[nombre].profesores = profesores_materia

    # Cargar profesores
    with open(profesores_csv, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            nombre = row['Nombre']
            profesor = Profesor(nombre)
            
            for dia in DIAS:
                if row[dia]:
                    profesor.disponibilidad[dia] = [h.strip() for h in row[dia].split(';')]
            
            if row['Materias']:
                profesor.materias = [m.strip() for m in row['Materias'].split(';')]
            
            profesores[nombre] = profesor

    return materias, profesores

# --- Clases principales ---
class Profesor:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.disponibilidad = defaultdict(list)
        self.materias = []
        self.horario_asignado = defaultdict(list)

class Materia:
    def __init__(self, nombre: str, semestre: int, horas_semana: int, activa: bool = True):
        self.nombre = nombre
        self.semestre = semestre
        self.horas_semana = horas_semana
        self.profesores = []
        self.activa = activa

class GeneradorHorarios:
    def __init__(self, materias: Dict[str, Materia], profesores: Dict[str, Profesor]):
        self.materias = {n: m for n, m in materias.items() if m.activa}
        self.profesores = profesores
        self.mejor_horario = None
        self.mejor_fitness = -math.inf
    
    def generar_horario_inicial(self):
        """Genera un horario inicial factible"""
        horario = []
        profesores_disponibles = {p: defaultdict(list) for p in self.profesores}
        
        for materia in sorted(self.materias.values(), key=lambda x: (-x.horas_semana, x.semestre)):
            horas_asignadas = 0
            intentos = 0
            
            while horas_asignadas < materia.horas_semana and intentos < 1000:
                intentos += 1
                profesor = random.choice([p for p in materia.profesores if p in self.profesores])
                
                # Buscar slot disponible
                for dia in random.sample(DIAS, len(DIAS)):
                    horas_dia = [h for h in self.profesores[profesor].disponibilidad[dia] 
                                if h not in profesores_disponibles[profesor][dia]]
                    
                    for hora in random.sample(horas_dia, len(horas_dia)):
                        # Verificar que no haya conflicto en el semestre
                        conflicto = any(
                            (a[2] == dia and a[3] == hora and 
                             self.materias[a[0]].semestre == materia.semestre)
                            for a in horario
                        )
                        
                        if not conflicto:
                            horario.append((materia.nombre, profesor, dia, hora))
                            profesores_disponibles[profesor][dia].append(hora)
                            horas_asignadas += 1
                            break
                
        return horario
    
    def calcular_fitness(self, horario):
        """Función de fitness más estricta"""
        penalizaciones = 0
        recompensas = 0
        
        # 1. Control de horas exactas por materia
        horas_por_materia = defaultdict(int)
        for asignacion in horario:
            horas_por_materia[asignacion[0]] += 1
        
        for nombre, materia in self.materias.items():
            diferencia = abs(horas_por_materia.get(nombre, 0) - materia.horas_semana)
            if diferencia != 0:
                penalizaciones += diferencia * 100
        
        # 2. Conflictos de profesores
        profesor_horarios = defaultdict(set)
        for asignacion in horario:
            key = (asignacion[1], asignacion[2], asignacion[3])
            if key in profesor_horarios:
                penalizaciones += 200
            profesor_horarios[key].add(asignacion[0])
        
        # 3. Conflictos de semestre
        semestre_horarios = defaultdict(set)
        for asignacion in horario:
            semestre = self.materias[asignacion[0]].semestre
            key = (semestre, asignacion[2], asignacion[3])
            if key in semestre_horarios:
                penalizaciones += 150
            semestre_horarios[key].add(asignacion[0])
        
        # 4. Recompensa por distribución equilibrada
        dias_por_materia = defaultdict(set)
        for asignacion in horario:
            dias_por_materia[asignacion[0]].add(asignacion[2])
        
        for materia, dias in dias_por_materia.items():
            recompensas += len(dias) * 5
        
        return 1000 / (1 + penalizaciones) + recompensas
    
    def generar_vecino(self, horario_actual):
        """Genera un horario vecino con pequeños cambios"""
        nuevo_horario = list(horario_actual)
        
        operador = random.choice([1, 2, 3])
        
        if operador == 1 and len(nuevo_horario) > 0:
            idx = random.randint(0, len(nuevo_horario) - 1)
            materia_nombre, profesor_old, dia_old, hora_old = nuevo_horario[idx]
            materia = self.materias[materia_nombre]
            
            for _ in range(50):
                profesor_new = random.choice(materia.profesores)
                dia_new = random.choice(DIAS)
                
                # Verificar que el profesor tenga disponibilidad ese día
                if not self.profesores[profesor_new].disponibilidad[dia_new]:
                    continue
                    
                hora_new = random.choice(self.profesores[profesor_new].disponibilidad[dia_new])
                
                conflicto_profesor = any(
                    (a[1] == profesor_new and a[2] == dia_new and a[3] == hora_new)
                    for a in nuevo_horario if a != nuevo_horario[idx]
                )
                
                conflicto_semestre = any(
                    (a[2] == dia_new and a[3] == hora_new and 
                    self.materias[a[0]].semestre == materia.semestre)
                    for a in nuevo_horario if a != nuevo_horario[idx]
                )
                
                if not conflicto_profesor and not conflicto_semestre:
                    nuevo_horario[idx] = (materia_nombre, profesor_new, dia_new, hora_new)
                    break
        
        elif operador == 2 and len(nuevo_horario) > 1:
            idx1, idx2 = random.sample(range(len(nuevo_horario)), 2)
            asig1 = nuevo_horario[idx1]
            asig2 = nuevo_horario[idx2]
            
            conflicto1 = any(
                (a[1] == asig1[1] and a[2] == asig2[2] and a[3] == asig2[3]) or
                (self.materias[a[0]].semestre == self.materias[asig1[0]].semestre and 
                a[2] == asig2[2] and a[3] == asig2[3])
                for a in nuevo_horario if a not in [asig1, asig2]
            )
            
            conflicto2 = any(
                (a[1] == asig2[1] and a[2] == asig1[2] and a[3] == asig1[3]) or
                (self.materias[a[0]].semestre == self.materias[asig2[0]].semestre and 
                a[2] == asig1[2] and a[3] == asig1[3])
                for a in nuevo_horario if a not in [asig1, asig2]
            )
            
            if not conflicto1 and not conflicto2:
                nuevo_horario[idx1] = (asig1[0], asig1[1], asig2[2], asig2[3])
                nuevo_horario[idx2] = (asig2[0], asig2[1], asig1[2], asig1[3])
        
        elif operador == 3:
            if random.random() < 0.5 and len(nuevo_horario) > 0:
                nuevo_horario.pop(random.randint(0, len(nuevo_horario) - 1))
            else:
                materia = random.choice(list(self.materias.values()))
                horas_actuales = sum(1 for a in nuevo_horario if a[0] == materia.nombre)
                
                if horas_actuales < materia.horas_semana:
                    for _ in range(50):
                        profesor = random.choice(materia.profesores)
                        dia = random.choice(DIAS)
                        
                        # Verificar disponibilidad del profesor
                        if not self.profesores[profesor].disponibilidad[dia]:
                            continue
                            
                        hora = random.choice(self.profesores[profesor].disponibilidad[dia])
                        
                        conflicto_profesor = any(
                            (a[1] == profesor and a[2] == dia and a[3] == hora)
                            for a in nuevo_horario
                        )
                        
                        conflicto_semestre = any(
                            (a[2] == dia and a[3] == hora and 
                            self.materias[a[0]].semestre == materia.semestre)
                            for a in nuevo_horario
                        )
                        
                        if not conflicto_profesor and not conflicto_semestre:
                            nuevo_horario.append((materia.nombre, profesor, dia, hora))
                            break
        
        return nuevo_horario
    
    def optimizar(self, iteraciones=10000, temp_inicial=1000, temp_final=0.1):
        """Algoritmo de enfriamiento simulado"""
        temp = temp_inicial
        factor_enfriamiento = (temp_final / temp_inicial) ** (1 / iteraciones)
        
        horario_actual = self.generar_horario_inicial()
        fitness_actual = self.calcular_fitness(horario_actual)
        
        self.mejor_horario = horario_actual
        self.mejor_fitness = fitness_actual
        
        for i in range(iteraciones):
            vecino = self.generar_vecino(horario_actual)
            fitness_vecino = self.calcular_fitness(vecino)
            
            if fitness_vecino > fitness_actual or \
               random.random() < math.exp((fitness_vecino - fitness_actual) / temp):
                horario_actual = vecino
                fitness_actual = fitness_vecino
                
                if fitness_actual > self.mejor_fitness:
                    self.mejor_horario = horario_actual
                    self.mejor_fitness = fitness_actual
            
            temp *= factor_enfriamiento
            
            if i % 100 == 0:
                print(f"Iteración {i}: Fitness = {fitness_actual:.2f}, Temp = {temp:.2f}")
        
        return self.mejor_horario

def formato_json_mejorado(horario: List[Tuple], materias: Dict[str, Materia]) -> Dict:
    """Organiza el horario por semestres con toda la información estructurada"""
    resultado = {}
    
    # Agrupar por semestre
    for nombre, materia in materias.items():
        if not materia.activa:
            continue
            
        if f"Semestre {materia.semestre}" not in resultado:
            resultado[f"Semestre {materia.semestre}"] = {
                "semestre": materia.semestre,
                "materias": []
            }
            
        # Filtrar asignaciones para esta materia
        asignaciones_materia = [a for a in horario if a[0] == nombre]
        horas_asignadas = len(asignaciones_materia)
        
        # Crear entrada de materia
        entrada_materia = {
            "nombre": nombre,
            "horas_semana": materia.horas_semana,
            "horas_asignadas": horas_asignadas,
            "profesor": asignaciones_materia[0][1] if horas_asignadas > 0 else "Sin asignar",
            "horarios": []
        }
        
        # Agregar horarios
        for asignacion in asignaciones_materia:
            entrada_materia["horarios"].append({
                "dia": asignacion[2],
                "hora": asignacion[3]
            })
        
        resultado[f"Semestre {materia.semestre}"]["materias"].append(entrada_materia)
    
    # Ordenar semestres y materias
    for semestre in resultado.values():
        semestre["materias"].sort(key=lambda x: x["nombre"])
    
    return dict(sorted(resultado.items(), key=lambda x: x[1]["semestre"]))


# --- Función principal ---
def main():
    semestres_impares, materias_transversales = cargar_configuracion()
    materias, profesores = cargar_datos('materias.csv', 'profesores.csv', materias_transversales, semestres_impares)
    
    generador = GeneradorHorarios(materias, profesores)
    mejor_horario = generador.optimizar(iteraciones=5000)
    
    # Formatear resultado
    horario_formateado = formato_json_mejorado(mejor_horario, materias)
    
    # Mostrar resumen
    print("\nResumen por semestre:")
    for semestre, data in horario_formateado.items():
        print(f"\n{semestre}:")
        for materia in data["materias"]:
            estado = "✓" if materia["horas_asignadas"] == materia["horas_semana"] else "✗"
            print(f"  {estado} {materia['nombre']}: {materia['horas_asignadas']}/{materia['horas_semana']} horas")
    
    # Guardar JSON
    with open('horario_optimizado.json', 'w', encoding='utf-8') as f:
        json.dump(horario_formateado, f, ensure_ascii=False, indent=2)
    
    print("\nHorario optimizado guardado en 'horario_optimizado.json'")

if __name__ == "__main__":
    main()