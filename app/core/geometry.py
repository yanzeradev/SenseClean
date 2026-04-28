import numpy as np
from typing import List, Dict, Tuple, Optional

def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    """Verifica a orientação dos pontos (Sentido anti-horário)."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def do_intersect(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
    """Verifica se o segmento de reta p1-p2 cruza fisicamente com p3-p4."""
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

def check_intersection_and_direction(last_pos: Tuple[float, float], curr_pos: Tuple[float, float], line_points: List[Dict[str, float]], in_side: str) -> Optional[str]:
    """
    Verifica se o rastro da pessoa cortou as linhas desenhadas.
    Se cortou, calcula a direção (in ou out) com base EXATAMENTE no segmento cruzado.
    """
    if len(line_points) < 2 or last_pos is None:
        return None
        
    intersected = False
    crossed_segment = None
    
    # 1. Checa se cruzou fisicamente e SALVA qual foi a aresta exata cortada
    for i in range(len(line_points) - 1):
        C = (line_points[i]['x'], line_points[i]['y'])
        D = (line_points[i+1]['x'], line_points[i+1]['y'])
        if do_intersect(last_pos, curr_pos, C, D):
            intersected = True
            crossed_segment = (C, D)
            break
            
    if not intersected or crossed_segment is None:
        return None
        
    # 2. Usa APENAS o segmento cruzado para definir as metades "IN" e "OUT"
    p_start = np.array(crossed_segment[0])
    p_end = np.array(crossed_segment[1])
    
    def get_side(point):
        target = np.array(point)
        # Produto vetorial relativo à aresta específica
        cross_product = np.cross(p_end - p_start, target - p_start)
        return 'right' if cross_product > 0 else 'left'
        
    side_last = get_side(last_pos)
    side_curr = get_side(curr_pos)
    
    # Se ele veio de um lado e foi para o outro, sabemos a direção exata!
    if side_last != side_curr:
        if side_curr == in_side:
            return 'in'  # Estava Fora -> Entrou
        else:
            return 'out' # Estava Dentro -> Saiu
    
    return None