import os
import sys
from app.models.log_parser import STM32LogParser
from app.models.ai_client import AIClient
from app.utils.report_manager import ReportManager

def run_ai_test():
    # Force stdout to use UTF-8 to prevent encoding errors on Windows terminal
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    log_file = os.path.join("tests_logs", "mock_error.log")
    
    print("1. Lecture du log...")
    parser = STM32LogParser()
    # On parse le log pour avoir les objets LogEntry (qu'on enverra au ReportManager)
    entries = parser.parse_file(log_file)
    
    # On filtre pour l'IA
    issues = [e for e in entries if e.level in ["ERROR", "WARNING"]]
    if not issues:
        print("Aucun problème détecté dans le log.")
        return
        
    log_text_for_ai = "\n".join([f"[{e.level}] {e.message}" for e in issues])
    
    # Extraction du nom de la carte (Board)
    board_name = "Inconnu"
    for entry in entries:
        if "Board" in entry.raw_line and ":" in entry.raw_line:
            parts = entry.raw_line.split(":")
            for i, part in enumerate(parts):
                if "Board" in part:
                    if i + 1 < len(parts):
                        board_name = parts[i+1].strip()
                        break
            if board_name != "Inconnu":
                break
    
    print("2. Envoi à l'IA Groq (patiente quelques secondes)...")
    try:
        client = AIClient()
        diagnostic = client.analyze_logs(log_text_for_ai)
        
        print("3. Sauvegarde du rapport JSON...")
        manager = ReportManager()
        # On sauvegarde le rapport !
        saved_file = manager.save_report(log_file, entries, diagnostic, board_name)
        print(f"Rapport sauvegardé avec succès sous : {saved_file}")
        
        # On lit le fichier généré pour l'afficher à l'écran
        with open(saved_file, 'r', encoding='utf-8') as f:
            print("\n" + "="*60)
            print("📄 EXEMPLE DE FICHIER JSON SAUVEGARDÉ :")
            print("="*60)
            print(f.read())
            print("="*60)
            
    except Exception as e:
        print(f"\n[!] Erreur lors du test : {e}")

if __name__ == "__main__":
    run_ai_test()
