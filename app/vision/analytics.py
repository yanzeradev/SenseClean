from typing import List, Dict, Any
from collections import Counter
from app.core.geometry import get_point_side

# Domain mapping for classes (Based on your YOLO model training)
CLASS_MAPPING = {
    0: "Homem",
    1: "Mulher",
    2: "NaoIdentificado"
}

class ZoneAnalytics:
    """
    Handles the business logic for counting objects crossing specific lines.
    Maintains the state and class history of each tracked object.
    """

    def __init__(self, entrant_line: List[Dict[str, float]], passerby_line: List[Dict[str, float]], in_side_direction: str):
        self.entrant_line = entrant_line
        self.passerby_line = passerby_line
        self.in_side = in_side_direction
        self.entrant_out_side = 'left' if self.in_side == 'right' else 'right'
        
        # State memory: tid -> {'status': str, 'last_ent_side': str, 'last_pass_side': str}
        self.track_states: Dict[int, Dict[str, str]] = {}
        
        # Class memory for Majority Voting: tid -> [class_id, class_id, ...]
        self.track_classes: Dict[int, List[int]] = {}
        
        # Real-time UI Counters (Aggregated, ignoring gender for real-time speed)
        self.counts = {
            "entrant": 0,
            "passerby": 0
        }

    def _get_bbox_center(self, bbox: List[float]) -> tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def update(self, tracks: List[Dict[str, Any]]) -> None:
        """Updates the analytics state frame by frame."""
        for track in tracks:
            tid = track["track_id"]
            bbox = track["bbox"]
            cls_id = track["class_id"]
            
            if tid not in self.track_states:
                self.track_states[tid] = {
                    'status': 'neutral',
                    'last_ent_side': 'unknown',
                    'last_pass_side': 'unknown'
                }
                self.track_classes[tid] = []
            
            # Store the class prediction for this specific frame
            self.track_classes[tid].append(cls_id)
            
            state = self.track_states[tid]
            center_point = self._get_bbox_center(bbox)

            # Passerby Logic
            curr_pass_side = get_point_side(center_point, self.passerby_line)
            if curr_pass_side != 'on_line':
                if state['last_pass_side'] != 'unknown' and state['last_pass_side'] != curr_pass_side:
                    if state['status'] == 'neutral':
                        state['status'] = 'passerby'
                        self.counts["passerby"] += 1
                state['last_pass_side'] = curr_pass_side

            # Entrant Logic
            curr_ent_side = get_point_side(center_point, self.entrant_line)
            if curr_ent_side != 'on_line':
                if state['last_ent_side'] == self.entrant_out_side and curr_ent_side == self.in_side:
                    if state['status'] == 'neutral':
                        state['status'] = 'entrant'
                        self.counts["entrant"] += 1
                    elif state['status'] == 'passerby':
                        state['status'] = 'entrant'
                        self.counts["passerby"] -= 1
                        self.counts["entrant"] += 1
                state['last_ent_side'] = curr_ent_side

    def get_final_results(self) -> Dict[str, Any]:
        """
        Executes Majority Voting on the collected class data and generates the final JSON report.
        """
        final_entrantes = {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0}
        final_passantes = {"Homem": 0, "Mulher": 0, "NaoIdentificado": 0}
        
        for tid, state in self.track_states.items():
            status = state['status']
            if status == 'neutral':
                continue
            
            # Majority Voting Execution
            classes_seen = self.track_classes.get(tid, [])
            if not classes_seen:
                majority_cls = "NaoIdentificado"
            else:
                most_common_id = Counter(classes_seen).most_common(1)[0][0]
                majority_cls = CLASS_MAPPING.get(most_common_id, "NaoIdentificado")
            
            # Tally up
            if status == 'entrant':
                final_entrantes[majority_cls] += 1
            elif status == 'passerby':
                final_passantes[majority_cls] += 1
                
        # Calculate Totals
        final_entrantes["Total"] = sum(final_entrantes.values())
        final_passantes["Total"] = sum(final_passantes.values())
        
        return {
            "entrantes": final_entrantes,
            "passantes": final_passantes,
            "total_geral": {
                "Homem": final_entrantes["Homem"] + final_passantes["Homem"],
                "Mulher": final_entrantes["Mulher"] + final_passantes["Mulher"],
                "NaoIdentificado": final_entrantes["NaoIdentificado"] + final_passantes["NaoIdentificado"],
                "Total": final_entrantes["Total"] + final_passantes["Total"]
            }
        }