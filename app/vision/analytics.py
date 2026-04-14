from typing import List, Dict, Any
from app.core.geometry import get_point_side

class ZoneAnalytics:
    """
    Handles the business logic for counting objects crossing specific lines.
    Maintains the state of each tracked object over time.
    """

    def __init__(self, entrant_line: List[Dict[str, float]], passerby_line: List[Dict[str, float]], in_side_direction: str):
        self.entrant_line = entrant_line
        self.passerby_line = passerby_line
        self.in_side = in_side_direction  # 'right' or 'left'
        self.entrant_out_side = 'left' if self.in_side == 'right' else 'right'
        
        # Track states: tid -> {'status': str, 'last_ent_side': str, 'last_pass_side': str}
        self.track_states: Dict[int, Dict[str, str]] = {}
        
        # Counters
        self.counts = {
            "entrant": 0,
            "passerby": 0
        }

    def _get_bbox_center(self, bbox: List[float]) -> tuple[float, float]:
        """Calculates the center point of a bounding box."""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def update(self, tracks: List[Dict[str, Any]]) -> None:
        """
        Updates the analytics state based on the latest tracked objects.
        
        Args:
            tracks (List[Dict]): Tracked objects from the VideoPipeline.
        """
        for track in tracks:
            tid = track["track_id"]
            bbox = track["bbox"]
            
            # Initialize state for new tracks
            if tid not in self.track_states:
                self.track_states[tid] = {
                    'status': 'neutral',
                    'last_ent_side': 'unknown',
                    'last_pass_side': 'unknown'
                }
            
            state = self.track_states[tid]
            center_point = self._get_bbox_center(bbox)

            # 1. Process Passerby Logic
            curr_pass_side = get_point_side(center_point, self.passerby_line)
            if curr_pass_side != 'on_line':
                if state['last_pass_side'] != 'unknown' and state['last_pass_side'] != curr_pass_side:
                    if state['status'] == 'neutral':
                        state['status'] = 'passerby'
                        self.counts["passerby"] += 1
                
                state['last_pass_side'] = curr_pass_side

            # 2. Process Entrant Logic
            curr_ent_side = get_point_side(center_point, self.entrant_line)
            if curr_ent_side != 'on_line':
                # Check for a valid crossing from OUT to IN
                if state['last_ent_side'] == self.entrant_out_side and curr_ent_side == self.in_side:
                    if state['status'] == 'neutral':
                        state['status'] = 'entrant'
                        self.counts["entrant"] += 1
                    
                    elif state['status'] == 'passerby':
                        # Reclassification: Object was a passerby, but entered the store
                        state['status'] = 'entrant'
                        self.counts["passerby"] -= 1
                        self.counts["entrant"] += 1

                state['last_ent_side'] = curr_ent_side