from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client.gestione_scuola

# Recupera i dati vecchi
vecchi_dati = db.dati.find_one()

if vecchi_dati:
    # Crea un utente demo
    user_data = {
        "google_id": "demo_user",
        "email": "demo@studentplanner.com",
        "name": "Utente Demo",
        "quadrimestre": vecchi_dati.get("quadrimestre", 1),
        "anno_scolastico": vecchi_dati.get("anno_scolastico", "2023/2024"),
        "materie": vecchi_dati.get("materie", {}),
        "professori": vecchi_dati.get("professori", []),
        "orario": vecchi_dati.get("orario", {})
    }
    
    # Inserisci nella nuova collection
    db.users.insert_one(user_data)
    
    # Opzionale: elimina i vecchi dati
    # db.dati.deleteMany({})
    
    print("Migrazione completata!")
else:
    print("Nessun dato da migrare")