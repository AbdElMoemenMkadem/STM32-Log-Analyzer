import os
from dataclasses import dataclass
from typing import List

@dataclass
class LogEntry:
    """Structure de données représentant une seule ligne de log."""
    timestamp: str
    level: str  # Peut être 'INFO', 'WARNING' ou 'ERROR'
    message: str
    raw_line: str # La ligne originale brute

class STM32LogParser:
    """Classe responsable de la lecture et de l'analyse des fichiers de log."""
    
    def parse_file(self, file_path: str) -> List[LogEntry]:
        """
        Lit un fichier de log et retourne une liste d'objets LogEntry.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Le fichier {file_path} n'existe pas.")

        entries = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue  # On ignore les lignes vides
                
                # Le log STM32 typique est au format "10:42:01 : Message"
                # On coupe la ligne en deux à la première occurrence de " : "
                parts = raw.split(" : ", 1)
                
                if len(parts) == 2:
                    timestamp = parts[0].strip()
                    msg_part = parts[1].strip()
                    
                    level = "INFO"
                    message = msg_part
                    
                    # On détermine la gravité de la ligne
                    if msg_part.startswith("Error:"):
                        level = "ERROR"
                        message = msg_part.replace("Error:", "", 1).strip()
                    elif msg_part.startswith("Warning:"):
                        level = "WARNING"
                        message = msg_part.replace("Warning:", "", 1).strip()
                        
                    entries.append(LogEntry(
                        timestamp=timestamp,
                        level=level,
                        message=message,
                        raw_line=raw
                    ))
                else:
                    # Si la ligne n'a pas le format attendu, on la garde brute
                    entries.append(LogEntry(
                        timestamp="",
                        level="INFO",
                        message=raw,
                        raw_line=raw
                    ))
                    
        return entries
