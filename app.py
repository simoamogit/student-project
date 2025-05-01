import re
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from bson import ObjectId
from bson.objectid import ObjectId

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
    filtro = dati.get('filtro_visualizzazione', 'quadrimestre')
    
    voti_formattati = []
    for materia, dettagli in dati['materie'].items():
        for i, voto in enumerate(dettagli['voti']):
            if filtro == 'tutto' or voto['quadrimestre'] == dati['quadrimestre']:
                voti_formattati.append({
                    'materia': materia,
                    'valore': voto['valore'],
                    'quadrimestre': voto['quadrimestre'],
                    'indice': i
                })
    
    return render_template('voti.html', dati=dati, voti=voti_formattati)

@app.route('/media')
def media():
    dati = get_dati()
    filtro = dati.get('filtro_visualizzazione', 'quadrimestre')
    quadrimestre = dati['quadrimestre']
    
    medie = {}
    for materia, dettagli in dati['materie'].items():
        voti_filtrati = [
            v['valore'] for v in dettagli['voti'] 
            if filtro == 'tutto' or v['quadrimestre'] == quadrimestre
        ]
        if voti_filtrati:
            medie[materia] = sum(voti_filtrati)/len(voti_filtrati)
    
    media_generale = sum(medie.values())/len(medie) if medie else 0
    return render_template('media.html', 
                         dati=dati,
                         medie=medie,
                         media_generale=media_generale)

@app.route('/orario', methods=['GET', 'POST'])
def orario():
    dati = get_dati()
    giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"]  # Sposta qui la definizione

    if request.method == 'POST':
        try:
            nuovo_orario = {}
            for giorno in giorni:
                nuovo_orario[giorno] = [request.form.get(f"{giorno}_{i}") for i in range(6)]
            
            # Salva per quadrimestre corrente
            dati['orario'][f'quadrimestre_{dati["quadrimestre"]}'] = nuovo_orario
            save_dati(dati)
            flash('Orario salvato!', 'success')
            
        except Exception as e:
            flash(f'Errore: {str(e)}', 'danger')

    # Carica orario per quadrimestre corrente
    orario_corrente = dati['orario'].get(
        f'quadrimestre_{dati["quadrimestre"]}', 
        {giorno: ['']*6 for giorno in giorni}  # Ora 'giorni' è definito
    )
    
    return render_template('orario.html', 
                         dati=dati,
                         orario=orario_corrente,
                         quadrimestre=dati['quadrimestre'])

@app.route('/modifica_orario')
def modifica_orario():
    # Redirect all'orario principale dove si può modificare
    return redirect(url_for('orario'))

@app.route("/api/voti/elimina", methods=["POST"])
def elimina_voto():
    try:
        data = request.json
        materia = data.get('materia')
        indice = int(data.get('indice'))
        
        dati = get_dati()
        
        # Verifica se la materia esiste
        if materia not in dati['materie']:
            return jsonify({"success": False, "error": "Materia non trovata"}), 404
            
        # Verifica se l'indice è valido
        voti_materia = dati['materie'][materia]['voti']
        if indice < 0 or indice >= len(voti_materia):
            return jsonify({"success": False, "error": "Indice non valido"}), 400
            
        # Rimuovi il voto
        del dati['materie'][materia]['voti'][indice]
        save_dati(dati)
        
        return jsonify({"success": True})
            
    except Exception as e:
        app.logger.error(f"Errore: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

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
            voto_valore = float(request.form.get('voto'))
            
            if voto_valore < 0 or voto_valore > 10:
                flash("Il voto deve essere tra 0 e 10!", 'danger')
                return redirect(url_for('aggiungi_voto'))
            
            if materia not in dati['materie']:
                flash("Materia non trovata!", 'danger')
                return redirect(url_for('voti'))

            nuovo_voto = {
                'valore': voto_valore,
                'quadrimestre': dati['quadrimestre'],
                'data': datetime.now().strftime("%Y-%m-%d")
            }
            
            dati['materie'][materia]['voti'].append(nuovo_voto)
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
        dati = get_dati()
        
        if request.method == 'POST':
            materia = request.form['materia']
            indice = int(request.form['indice'])
            nuovo_valore = float(request.form['nuovo_voto'])

            if materia not in dati['materie']:
                flash('❌ Materia non trovata!', 'danger')
                return redirect(url_for('modifica_voto'))

            voti_materia = dati['materie'][materia]['voti']
            
            if indice < 0 or indice >= len(voti_materia):
                flash('❌ Indice non valido!', 'danger')
                return redirect(url_for('modifica_voto'))

            # Mantieni i dati esistenti e aggiorna solo il valore
            voti_materia[indice]['valore'] = nuovo_valore
            save_dati(dati)
            
            flash('✅ Voto modificato con successo!', 'success')
            return redirect(url_for('voti'))

        return render_template('gestione/modifica_voto.html',
                             materie=dati['materie'],
                             dati=dati)
    except Exception as e:
        flash(f'❌ Errore critico: {str(e)}', 'danger')
        return redirect(url_for('modifica_voto'))

@app.route("/api/voti/elimina-multi", methods=["POST"])
def elimina_voti_multi():
    try:
        data = request.json
        votes_to_delete = data.get('votes', [])
        
        dati = get_dati()
        deleted_count = 0

        # Organizza per materia e verifica gli indici
        subjects = {}
        for vote in votes_to_delete:
            materia = vote.get('materia')
            indice = int(vote.get('indice', -1))
            
            if materia not in dati['materie']:
                continue
                
            if indice < 0 or indice >= len(dati['materie'][materia]['voti']):
                continue
                
            if materia not in subjects:
                subjects[materia] = []
            subjects[materia].append(indice)

        # Elimina in ordine inverso
        for materia, indices in subjects.items():
            unique_indices = list(set(indices))  # Rimuovi duplicati
            for indice in sorted(unique_indices, reverse=True):
                del dati['materie'][materia]['voti'][indice]
                deleted_count += 1

        save_dati(dati)
        return jsonify({
            "success": True,
            "count": deleted_count
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "count": 0
        }), 500
    
# Aggiungi queste route in app.py
@app.route('/api/imposta-filtro', methods=['POST'])
def imposta_filtro():
    dati = get_dati()
    nuovo_filtro = request.json.get('filtro')
    
    if nuovo_filtro not in ['anno', 'quadrimestre']:
        return jsonify({"success": False, "error": "Filtro non valido"}), 400
    
    dati['filtro_voti'] = nuovo_filtro
    save_dati(dati)
    return jsonify({"success": True})
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

@app.route('/api/update-view', methods=['POST'])
def update_view():
    try:
        data = request.json
        new_view = data.get('view')
        dati = get_dati()

        if str(new_view) in ['1', '2']:
            dati['quadrimestre'] = int(new_view)
            dati['filtro_visualizzazione'] = 'quadrimestre'
        elif new_view == 'tutto':
            dati['filtro_visualizzazione'] = 'tutto'

        save_dati(dati)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
# -----------------------------------------------
# AVVIO APPLICAZIONE
# -----------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)