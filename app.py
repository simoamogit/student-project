from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json
from bson import ObjectId

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Connessione MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client.gestione_scuola
col = db.dati

def get_dati():
    dati = col.find_one()
    if not dati:
        # Crea nuovo documento
        nuovo_documento = {
            "materie": {},
            "professori": [],
            "quadrimestre": 1,
            "anno_scolastico": "2023/2024",
            "orario": {}
        }
        result = col.insert_one(nuovo_documento)
        nuovo_documento['_id'] = str(result.inserted_id)
        return nuovo_documento
    
    # Converti ObjectId a stringa
    dati['_id'] = str(dati['_id'])
    return dati

def save_dati(dati):
    # Crea copia senza _id per l'update
    dati_per_salvataggio = dati.copy()
    object_id = dati_per_salvataggio.pop('_id', None)
    
    # Esegui l'update usando l'ObjectId originale
    col.update_one(
        {'_id': ObjectId(object_id)},
        {'$set': dati_per_salvataggio},
        upsert=False
    )

# -----------------------------------------------
# ROUTE PRINCIPALI
# -----------------------------------------------

@app.route('/')
def home():
    dati = get_dati()
    return render_template('home.html', dati=dati)

@app.route('/voti')
def voti():
    dati = get_dati()
    return render_template('voti.html', dati=dati, materie=dati['materie'])

@app.route('/media')
def media():
    dati = get_dati()
    medie = {}
    for materia, dettagli in dati['materie'].items():
        if dettagli['voti']:
            medie[materia] = sum(dettagli['voti'])/len(dettagli['voti'])
    media_generale = sum(medie.values())/len(medie) if medie else 0
    return render_template('media.html', dati=dati, medie=medie, media_generale=media_generale)

@app.route('/orario', methods=['GET', 'POST'])
def orario():
    dati = get_dati()
    if request.method == 'POST':
        try:
            giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"]
            orario = {}
            # Assume 6 ore per giorno
            for giorno in giorni:
                orario[giorno] = [request.form.get(f"{giorno}_{i}") for i in range(6)]
            dati['orario'] = orario
            save_dati(dati)
            flash('Orario salvato!', 'success')
        except Exception as e:
            flash(f'Errore: {str(e)}', 'danger')
    return render_template('orario.html', dati=dati, orario=dati['orario'])

@app.route('/modifica_orario')
def modifica_orario():
    # Redirect all'orario principale dove si può modificare
    return redirect(url_for('orario'))

# -----------------------------------------------
# GESTIONE MATERIE
# -----------------------------------------------

@app.route('/aggiungi_materia', methods=['GET', 'POST'])
def aggiungi_materia():
    dati = get_dati()
    if request.method == 'POST':
        materia = request.form['materia'].strip()
        if materia not in dati['materie']:
            dati['materie'][materia] = {'voti': []}
            save_dati(dati)
            flash('Materia aggiunta con successo!', 'success')
            return redirect(url_for('voti'))
        else:
            flash('Materia già esistente!', 'error')
    return render_template('gestione/aggiungi_materia.html', dati=dati)

@app.route('/modifica_materia', methods=['GET', 'POST'])
def modifica_materia():
    dati = get_dati()
    if request.method == 'POST':
        vecchio = request.form['vecchio_nome']
        nuovo = request.form['nuovo_nome'].strip()
        if vecchio in dati['materie']:
            dati['materie'][nuovo] = dati['materie'].pop(vecchio)
            save_dati(dati)
            flash('Materia modificata!', 'success')
            return redirect(url_for('voti'))
    return render_template('gestione/modifica_materia.html', materie=dati['materie'].keys())

# -----------------------------------------------
# GESTIONE PROFESSORI
# -----------------------------------------------

@app.route('/aggiungi_professore', methods=['GET', 'POST'])
def aggiungi_professore():
    try:
        dati = get_dati()
        if request.method == 'POST':
            professore = request.form.get('professore', '').strip()
            if not professore:
                flash("Il campo non può essere vuoto!", 'error')
                return redirect(url_for('aggiungi_professore'))

            if professore in dati['professori']:
                flash('Professore già esistente!', 'error')
            else:
                dati['professori'].append(professore)
                save_dati(dati)
                flash('Professore aggiunto!', 'success')
            return redirect(url_for('gestione'))

        return render_template('gestione/aggiungi_professore.html', dati=dati)
    except Exception as e:
        flash(f'Errore: {str(e)}', 'danger')
        return redirect(url_for('gestione'))

@app.route('/modifica_professore', methods=['GET', 'POST'])
def modifica_professore():
    try:
        dati = get_dati()
        if request.method == 'POST':
            vecchio = request.form.get('vecchio_nome', '')
            nuovo = request.form.get('nuovo_nome', '').strip()
            
            if not nuovo:
                flash("Il nuovo nome non può essere vuoto!", 'error')
                return redirect(url_for('modifica_professore'))

            if vecchio in dati['professori']:
                index = dati['professori'].index(vecchio)
                dati['professori'][index] = nuovo
                save_dati(dati)
                flash('Professore modificato!', 'success')
            else:
                flash('Professore non trovato!', 'error')
            return redirect(url_for('gestione'))

        return render_template('gestione/modifica_professore.html', 
                            professori=dati['professori'],
                            dati=dati)
    except Exception as e:
        flash(f'Errore: {str(e)}', 'danger')
        return redirect(url_for('gestione'))

# -----------------------------------------------
# GESTIONE VOTI
# -----------------------------------------------

@app.route('/aggiungi_voto', methods=['GET', 'POST'])
def aggiungi_voto():
    try:
        dati = get_dati()
        if request.method == 'POST':
            materia = request.form.get('materia')
            voto = float(request.form.get('voto'))
            
            # Validazione
            if voto < 0 or voto > 10:
                flash("Il voto deve essere tra 0 e 10!", 'danger')
                return redirect(url_for('aggiungi_voto'))
            
            if materia not in dati['materie']:
                flash("Materia non trovata!", 'danger')
                return redirect(url_for('voti'))
            
            dati['materie'][materia]['voti'].append(voto)
            save_dati(dati)
            flash('Voto aggiunto con successo!', 'success')
            return redirect(url_for('voti'))

        return render_template('gestione/aggiungi_voto.html', 
                             materie=dati['materie'].keys(),
                             dati=dati)
    except Exception as e:
        flash(f'Errore: {str(e)}', 'danger')
        return redirect(url_for('voti'))

@app.route('/modifica_voto', methods=['GET', 'POST'])
def modifica_voto():
    try:
        dati = get_dati()  # Dati già convertiti con _id come stringa
        
        if request.method == 'POST':
            materia = request.form['materia']
            indice = int(request.form['indice'])
            nuovo_voto = float(request.form['nuovo_voto'])

            # Verifica esistenza materia
            if materia not in dati['materie']:
                flash('❌ Materia non trovata!', 'danger')
                return redirect(url_for('modifica_voto'))

            # Controllo indice valido
            voti_materia = dati['materie'][materia]['voti']
            if indice < 0 or indice >= len(voti_materia):
                flash('❌ Indice non valido!', 'danger')
                return redirect(url_for('modifica_voto'))

            # Modifica e salvataggio
            voti_materia[indice] = nuovo_voto
            
            # DEBUG: Converti manualmente _id per la stampa
            debug_data = dati.copy()
            debug_data['_id'] = str(debug_data['_id'])
            print(f"DEBUG - Dati aggiornati:\n{json.dumps(debug_data, indent=2, ensure_ascii=False)}")
            
            save_dati(dati)  # Salva su MongoDB
            flash('✅ Voto modificato con successo!', 'success')
            return redirect(url_for('voti'))

        return render_template('gestione/modifica_voto.html',
                             materie=dati['materie'],
                             dati=dati)
                             
    except Exception as e:
        flash(f'❌ Errore critico: {str(e)}', 'danger')
        return redirect(url_for('modifica_voto'))

# -----------------------------------------------
# ALTRE FUNZIONI
# -----------------------------------------------

@app.route('/impostazioni', methods=['GET', 'POST'])
def impostazioni():
    try:
        dati = get_dati()
        
        if request.method == 'POST':
            # Validazione dati
            nuovo_quadrimestre = int(request.form['quadrimestre'])
            nuovo_anno = request.form['anno_scolastico'].strip()
            
            if nuovo_quadrimestre not in [1, 2]:
                raise ValueError("Quadrimestre non valido")
                
            if not re.match(r'^\d{4}/\d{4}$', nuovo_anno):
                raise ValueError("Formato anno scolastico non valido (es. 2023/2024)")
            
            # Aggiornamento dati
            dati['quadrimestre'] = nuovo_quadrimestre
            dati['anno_scolastico'] = nuovo_anno
            save_dati(dati)
            
            flash('🎉 Impostazioni aggiornate con successo!', 'success')
            return redirect(url_for('impostazioni'))

        return render_template('gestione/impostazioni.html', 
                             quadrimestre=dati['quadrimestre'],
                             anno_scolastico=dati['anno_scolastico'])

    except Exception as e:
        flash(f'❌ Errore: {str(e)}', 'danger')
        return redirect(url_for('impostazioni'))

@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'POST':
        col.delete_many({})
        dati = {
            "materie": {},
            "professori": [],
            "quadrimestre": 1,
            "anno_scolastico": "2023/2024",
            "orario": {}
        }
        col.insert_one(dati)
        flash('Reset completato!', 'success')
        return redirect(url_for('home'))
    return render_template('reset.html')

@app.route('/gestione')
def gestione():
    return render_template('gestione/menu.html')

# -----------------------------------------------
# AVVIO APPLICAZIONE
# -----------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)