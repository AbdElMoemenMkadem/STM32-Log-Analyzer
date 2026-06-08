import json
import os
from datetime import datetime

class ReportManager:
    """Gère la création et la sauvegarde des rapports d'analyse au format JSON."""
    
    def __init__(self):
        self.output_dir = "output_reports"
        # On s'assure que le dossier existe
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def save_report(self, log_file_name: str, parsed_entries: list, ai_diagnostic: str, board_name: str = "Inconnu") -> str:
        """
        Crée la structure JSON et la sauvegarde dans un fichier.
        Retourne le chemin du fichier créé.
        """
        
        # --- ÉTAPE 10 : La structure du JSON ---
        errors = [e for e in parsed_entries if e.level == "ERROR"]
        warnings = [e for e in parsed_entries if e.level == "WARNING"]
        
        report_data = {
            "meta": {
                "date_generation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fichier_source": os.path.basename(log_file_name),
                "fichier_source_complet": os.path.abspath(log_file_name),
                "board": board_name
            },
            "statistiques": {
                "lignes_totales_lues": len(parsed_entries),
                "erreurs_trouvees": len(errors),
                "warnings_trouves": len(warnings)
            },
            "diagnostic_ia": ai_diagnostic,
            "details_erreurs_brutes": [
                {"heure": e.timestamp, "message": e.message} for e in errors
            ]
        }
        
        # --- ÉTAPE 11 : L'export et la sauvegarde ---
        # On génère un nom de fichier unique basé sur le nom du log et la date/heure
        base_name = os.path.basename(log_file_name)
        timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{base_name}_{timestamp_file}.json"
        report_path = os.path.join(self.output_dir, report_filename)
        
        # Écriture du fichier sur le disque
        with open(report_path, 'w', encoding='utf-8') as f:
            # indent=4 permet de mettre des retours à la ligne pour que ce soit beau à lire
            # ensure_ascii=False permet de garder nos accents français (é, à, etc.)
            json.dump(report_data, f, indent=4, ensure_ascii=False)
            
        return report_path
