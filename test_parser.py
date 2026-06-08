import os
from app.models.log_parser import STM32LogParser

def test_parser():
    # Chemin vers notre faux log
    log_file = os.path.join("tests_logs", "mock_error.log")
    
    print(f"--- DÉMARRAGE DU TEST SUR {log_file} ---")
    
    # 1. On initialise notre nouvel outil
    parser = STM32LogParser()
    
    # 2. On analyse le fichier
    entries = parser.parse_file(log_file)
    
    # 3. On trie les résultats
    errors = [e for e in entries if e.level == "ERROR"]
    warnings = [e for e in entries if e.level == "WARNING"]
    infos = [e for e in entries if e.level == "INFO"]
    
    # 4. On affiche le résumé
    print(f"\n--- RÉSUMÉ DE L'ANALYSE : ---")
    print(f"Lignes totales lues : {len(entries)}")
    print(f"[I] Infos    : {len(infos)}")
    print(f"[W] Warnings : {len(warnings)}")
    print(f"[E] Erreurs  : {len(errors)}")
    
    # 5. On vérifie que les erreurs sont bien extraites
    print("\n--- DÉTAIL DES ERREURS DÉTECTÉES : ---")
    for err in errors:
        print(f"  -> Heure: {err.timestamp} | Message: {err.message}")

if __name__ == "__main__":
    test_parser()
