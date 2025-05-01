import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Carica le variabili d'ambiente
load_dotenv()

# Configura la connessione usando la stessa URI dell'app
client = MongoClient(os.getenv("MONGO_URI"))
db = client.gestione_scuola
col = db.dati

try:
    # Verifica la connessione
    client.admin.command('ping')
    print("Connessione a MongoDB riuscita!")

    doc = col.find_one()

    if doc and 'orario' in doc:
        # Migrazione struttura orario solo se necessario
        if not any(key.startswith('quadrimestre_') for key in doc['orario']):
            print("Avvio migrazione dati orario...")
            
            # Crea la nuova struttura
            nuovo_orario = {
                'quadrimestre_1': doc['orario'],
                'quadrimestre_2': {giorno: ['']*6 for giorno in doc['orario']}
            }
            
            # Aggiorna il documento
            col.update_one(
                {'_id': doc['_id']},
                {'$set': {'orario': nuovo_orario}}
            )
            print("Migrazione completata con successo!")
        else:
            print("Struttura orario già aggiornata, nessuna migrazione necessaria.")
    else:
        print("Nessun documento trovato o campo 'orario' mancante")

except Exception as e:
    print(f"Errore durante la migrazione: {str(e)}")
finally:
    client.close()