import pandas as pd
import os
from typing import Dict, Any

class ReportService:
    """
    Service responsible for converting analytical data into downloadable documents.
    """
    
    @staticmethod
    def generate_excel(video_id: str, results: Dict[str, Any]) -> str:
        os.makedirs("static/reports", exist_ok=True)
        report_path = f"static/reports/{video_id}_report.xlsx"
        
        dados_planilha = {
            "entrantes": results.get("entrantes", {}),
            "passantes": results.get("passantes", {}),
            "total_geral": results.get("total_geral", {})
        }
        
        # Converte o dicionário purificado em um DataFrame pandas e exporta
        df = pd.DataFrame(dados_planilha).T
        df.to_excel(report_path)
        
        return f"/static/reports/{video_id}_report.xlsx"