from typing import List, Dict, Any
from collections import Counter
from app.core.geometry import check_intersection_and_direction
from datetime import datetime

CLASS_MAPPING = {
    0: "Homem",
    1: "Mulher",
    2: "NaoIdentificado"
}

class ZoneAnalytics:
    def __init__(self, entrant_line: List[Dict[str, float]], passerby_line: List[Dict[str, float]], in_side_direction: str):
        self.entrant_line = entrant_line
        self.passerby_line = passerby_line
        self.in_side = in_side_direction
        
        # Memória de rastreamento: tid -> estado atual
        self.track_states: Dict[int, Dict[str, Any]] = {}
        
        # Contadores reais
        self.counts = {
            "entrantes": 0,
            "saidas": 0,
            "passantes": 0
        }
        self.recent_events = []

    def _get_bbox_center(self, bbox: List[float]) -> tuple[float, float]:
        # Agora pegamos estritamente o centro do Bounding Box
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)

    def _log_event(self, event_type: str, cls_id: int):
        self.recent_events.append({
            "type": event_type, 
            "gender": CLASS_MAPPING.get(cls_id, "NaoIdentificado"),
            "time": datetime.now().strftime("%H:%M:%S")
        })

    def update(self, tracks: List[Dict[str, Any]]) -> None:
        """Processa frame a frame."""
        for track in tracks:
            tid = track["track_id"]
            bbox = track["bbox"]
            cls_id = track["class_id"]
            curr_center = self._get_bbox_center(bbox)
            
            if tid not in self.track_states:
                self.track_states[tid] = {
                    'last_center': curr_center,
                    'classes': [],
                    'final_action': None # Pode ser 'entrante', 'saida', 'passante'
                }
            
            state = self.track_states[tid]
            state['classes'].append(cls_id)
            last_center = state['last_center']
            
            # 1. Lógica da Linha Principal (Entradas e Saídas)
            if state['final_action'] not in ['entrante', 'saida']:
                direction = check_intersection_and_direction(last_center, curr_center, self.entrant_line, self.in_side)
                
                if direction in ['in', 'out']:
                    if state['final_action'] == 'passante':
                        self.counts["passantes"] = max(0, self.counts["passantes"] - 1)
                        # Remove o log antigo de passante para não sujar o painel (opcional)
                        self.recent_events = [e for e in self.recent_events if e.get("type") != "Passante"]
                    
                    if direction == 'in':
                        self.counts["entrantes"] += 1
                        state['final_action'] = 'entrante'
                        self._log_event("Entrada", cls_id)
                        
                    elif direction == 'out':
                        self.counts["saidas"] += 1
                        state['final_action'] = 'saida'
                        self._log_event("Saída", cls_id)

            # 2. Lógica da Linha de Passantes
            if state['final_action'] is None:
                # Usa 'right' como dummy, não importa a direção pra vitrine
                pass_direction = check_intersection_and_direction(last_center, curr_center, self.passerby_line, 'right')
                if pass_direction is not None:
                    self.counts["passantes"] += 1
                    state['final_action'] = 'passante'
                    self._log_event("Passante", cls_id)
                    
            # Atualiza o centro para o próximo frame
            state['last_center'] = curr_center

    def get_final_results(self) -> Dict[str, Any]:
        """Gera o relatório final com Votação Majoritária."""
        final_entrantes = {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0}
        final_saidas = {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0}
        final_passantes = {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0}
        
        for tid, state in self.track_states.items():
            action = state['final_action']
            if not action:
                continue
            
            classes_seen = state['classes']
            most_common_id = Counter(classes_seen).most_common(1)[0][0] if classes_seen else 2
            majority_cls = CLASS_MAPPING.get(most_common_id, "NaoIdentificado")
            
            if action == 'entrante':
                final_entrantes[majority_cls] += 1
            elif action == 'saida':
                final_saidas[majority_cls] += 1
            elif action == 'passante':
                final_passantes[majority_cls] += 1
                
        final_entrantes["Total"] = sum(final_entrantes.values())
        final_saidas["Total"] = sum(final_saidas.values())
        final_passantes["Total"] = sum(final_passantes.values())
        
        return {
            "entrantes": final_entrantes,
            "saidas": final_saidas,
            "passantes": final_passantes,
            "total_geral": {
                "Homem": final_entrantes["Homem"] + final_saidas["Homem"] + final_passantes["Homem"],
                "Mulher": final_entrantes["Mulher"] + final_saidas["Mulher"] + final_passantes["Mulher"],
                "NaoIdentificado": final_entrantes["NaoIdentificado"] + final_saidas["NaoIdentificado"] + final_passantes["NaoIdentificado"],
                "Total": final_entrantes["Total"] + final_saidas["Total"] + final_passantes["Total"]
            },
            "recent_events": self.recent_events
        }