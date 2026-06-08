import sys
import os

# On s'assure d'être dans le bon répertoire de travail
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from app.views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("STM32 Log Analyzer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("STM32 Tools")

    # Vérification rapide des dépendances critiques
    try:
        from dotenv import load_dotenv
        from groq import Groq
    except ImportError as e:
        msg = QMessageBox()
        msg.setWindowTitle("Dépendance manquante")
        msg.setIcon(QMessageBox.Critical)
        msg.setText(f"Module manquant : {e}\n\nLancez :\n  pip install -r requirements.txt")
        msg.exec()
        sys.exit(1)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
