import os
from dotenv import load_dotenv
from groq import Groq

# Le même cerveau qu'avant
SYSTEM_PROMPT = """Tu es un ingénieur expert STM32 et STM32CubeProgrammer.
Analyse les logs fournis et réponds UNIQUEMENT avec ce format exact :

TYPE: [SUCCÈS ou CRITIQUE ou AVERTISSEMENT] - [Titre court]
RESUME: [2 phrases max]
SOLUTIONS:
1. [Action concrète ou "Aucune action requise"]
VÉRIFICATION MATÉRIELLE: [Oui ou Non] - [Raison courte]

RÈGLES STRICTES — applique-les dans l'ordre :
1. Si le log contient "Download verified successfully" → TYPE: SUCCÈS
2. Si le log contient "Start operation achieved successfully" → TYPE: SUCCÈS  
3. Si TYPE est SUCCÈS → VÉRIFICATION MATÉRIELLE: Non - Flash réussi sans anomalie
4. Si le log contient "Error:" → TYPE: CRITIQUE
5. Si le log contient "Warning:" → TYPE: AVERTISSEMENT
6. VÉRIFICATION MATÉRIELLE est "Oui" UNIQUEMENT si TYPE est CRITIQUE avec une erreur SWD, alimentation ou câble
7. Les lignes "Debug in Low Power mode", "UPLOADING OPTION BYTES", "Revision ID" sont informatives — les ignorer
"""

class AIClient:
    """Gère la communication avec l'API gratuite de Groq."""
    
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        
        if not api_key:
            raise ValueError("ERREUR: Clé API Groq manquante dans le fichier .env !")
            
        # Initialisation du client Groq
        self.client = Groq(api_key=api_key)
        
        # Llama 3.1 (8 milliards de paramètres) : gratuit, ultra-rapide et très intelligent
        self.model = "llama-3.1-8b-instant"

    def analyze_logs(self, log_content: str) -> str:
        """Envoie les logs à Groq et retourne le diagnostic."""
        if not log_content.strip():
            return "Aucun log à analyser."
            
        try:
            # L'API Groq fonctionne comme celle d'OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Voici les logs de mon STM32 à analyser :\n\n{log_content}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"TYPE: ERREUR API\nRESUME: Impossible de contacter l'IA.\nSOLUTIONS:\n1. Vérifie ta connexion internet\n2. Vérifie ta clé API\nDétail technique: {e}"
