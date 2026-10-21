
# Utilise une image Python légère comme base
FROM python:3.11-slim

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie le fichier des dépendances
COPY requirements.txt .

# Installe les bibliothèques avec un délai plus long et des tentatives supplémentaires
RUN pip install --no-cache-dir --default-timeout=300 --retries=10 -r requirements.txt

# Copie le code de l'application Streamlit
COPY app.py .

# Expose le port utilisé par Streamlit
EXPOSE 8501

# Lance l'application Streamlit au démarrage du conteneur
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
