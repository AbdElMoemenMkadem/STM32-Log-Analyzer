"""
Contrôleur principal : orchestre le Parser, l'IA et le ReportManager.
C'est le cerveau qui relie tous les modules ensemble.
"""
from app.models.log_parser import STM32LogParser
from app.models.ai_client import AIClient
from app.utils.report_manager import ReportManager


class AnalysisController:
    """Orchestre l'analyse complète d'un fichier de log."""

    def __init__(self):
        self.parser = STM32LogParser()
        self.ai_client = AIClient()
        self.report_manager = ReportManager()

    def run_full_analysis(self, file_path: str, progress_callback=None) -> dict:
        """
        Lance le pipeline complet d'analyse.
        Retourne un dictionnaire avec tous les résultats.
        progress_callback(step: int, message: str) — optionnel pour mettre à jour l'UI.
        """

        def notify(step, msg):
            if progress_callback:
                progress_callback(step, msg)

        # ÉTAPE 1 — Parsing
        notify(1, "📂 Lecture et analyse du fichier de log...")
        entries = self.parser.parse_file(file_path)

        errors   = [e for e in entries if e.level == "ERROR"]
        warnings = [e for e in entries if e.level == "WARNING"]

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

        # ÉTAPE 2 — Préparation du texte pour l'IA
        notify(2, "🧠 Envoi des erreurs à l'IA Groq pour diagnostic...")
        error_lines = "\n".join(e.raw_line for e in errors + warnings)
        if not error_lines:
            error_lines = "\n".join(e.raw_line for e in entries)   # Tout si pas d'erreur

        # ÉTAPE 3 — Appel IA
        ai_diagnosis = self.ai_client.analyze_logs(error_lines)

        # ÉTAPE 4 — Sauvegarde du rapport
        notify(3, "💾 Génération du rapport JSON...")
        report_path = self.report_manager.save_report(file_path, entries, ai_diagnosis, board_name)

        notify(4, f"✅ Analyse terminée — rapport sauvegardé !")

        return {
            "entries":      entries,
            "errors":       errors,
            "warnings":     warnings,
            "ai_diagnosis": ai_diagnosis,
            "report_path":  report_path,
            "total_lines":  len(entries),
            "board":        board_name,
        }
