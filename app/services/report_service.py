import pandas as pd
import os
from typing import Dict, Any

class ReportService:
    """
    Service responsible for converting analytical data into downloadable documents.
    """
    
    @staticmethod
    def generate_excel(video_id: str, results: Dict[str, Any]) -> str:
        """
        Transforms the final JSON results into a pandas DataFrame and exports it to Excel.
        Returns the path to the saved file.
        """
        os.makedirs("static/reports", exist_ok=True)
        report_path = f"static/reports/{video_id}_report.xlsx"
        
        # Convert the nested dictionary into a pandas DataFrame
        # .T transposes it so rows are (entrantes, passantes, total) and columns are genders
        df = pd.DataFrame(results).T
        
        # Save to disk
        df.to_excel(report_path)
        
        # Return the public URL path
        return f"/static/reports/{video_id}_report.xlsx"