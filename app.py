import re
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from bson import ObjectId
from bson.objectid import ObjectId
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# Add this for development - allows OAuth over HTTP
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI"))
db = client.gestione_scuola
col = db.dati

# Login configuration
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Changed from 'google.login'

class User(UserMixin):
    def __init__(self, id, email, name, picture=None):
        self.id = id
        self.email = email
        self.name = name
        self.picture = picture

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({"google_id": user_id})
    if user_data:
        return User(
            user_data['google_id'], 
            user_data['email'], 
            user_data['name'],
            user_data.get('picture')
        )
    return None

# Google OAuth configuration
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    redirect_to="authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

# Get user data function
def get_dati():
    if current_user.is_authenticated:
        # Look for logged in user's data
        user_data = db.users.find_one({"google_id": current_user.id})
        
        if not user_data:
            # Create new document for user
            user_data = {
                "google_id": current_user.id,
                "email": current_user.email,
                "name": current_user.name,
                "picture": getattr(current_user, 'picture', None),
                "quadrimestre": 1,
                "anno_scolastico": "2023/2024",
                "materie": {},
                "professori": [],
                "orario": {
                    "quadrimestre_1": {},
                    "quadrimestre_2": {}
                }
            }
            db.users.insert_one(user_data)
        
        return user_data
    else:
        # Offline/demo mode (development only)
        return col.find_one() or {}

def save_dati(dati):
    if current_user.is_authenticated:
        db.users.update_one(
            {"google_id": current_user.id},
            {"$set": dati},
            upsert=True
        )

# -----------------------------------------------
# AUTHENTICATION ROUTES
# -----------------------------------------------

@app.route("/login")
def login():
    # Save the next parameter if it exists
    if 'next' in request.args:
        session['next'] = request.args['next']
    return redirect(url_for("google.login"))

@app.route("/authorized")
def authorized():
    """Route that handles the Google OAuth callback"""
    # Important: this is the route Flask-Dance will redirect to after Google auth
    if not google.authorized:
        flash("Accesso negato", "danger")
        return redirect(url_for("home"))
    
    try:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            user_info = resp.json()
            # Debug output to console
            print(f"Google user info received: {user_info}")
            
            # Find or create user
            user = db.users.find_one({"email": user_info["email"]})
            if not user:
                user = {
                    "google_id": user_info["id"],
                    "email": user_info["email"],
                    "name": user_info.get("name", user_info["email"]),
                    "picture": user_info.get("picture", None),  # Store profile picture URL
                    "quadrimestre": 1,
                    "materie": {},
                    "professori": [],
                    "anno_scolastico": "2023/2024",
                    "orario": {},
                    "filtro_visualizzazione": "quadrimestre"
                }
                db.users.insert_one(user)
            elif "picture" not in user or user["picture"] != user_info.get("picture"):
                # Update picture if changed
                db.users.update_one(
                    {"email": user_info["email"]},
                    {"$set": {"picture": user_info.get("picture")}}
                )
            
            user_obj = User(
                user_info["id"], 
                user_info["email"], 
                user_info.get("name", user_info["email"]),
                user_info.get("picture")  # Add profile picture to user object
            )
            login_user(user_obj)
            flash(f'Benvenuto, {user_info.get("name", user_info["email"])}!', 'success')
            
            # Get redirect target from session or default to home
            next_url = session.pop('next', url_for('home'))
            print(f"Redirecting to: {next_url}")
            return redirect(next_url)
        else:
            print(f"Error in Google response: {resp.text}")
            flash(f"Errore durante il login: {resp.text}", "danger")
    except Exception as e:
        print(f"Exception in authorized route: {str(e)}")
        app.logger.error(f"Error in authorized route: {str(e)}")
        flash(f"Errore durante il login: {str(e)}", "danger")
    
    return redirect(url_for("home"))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo', 'info')
    return redirect(url_for("home"))

# -----------------------------------------------
# MAIN ROUTES
# -----------------------------------------------

@app.route('/')
@login_required
def home():
    dati = get_dati()
    # Aggiungi controllo per assicurarti che i dati siano validi
    if not dati or 'anno_scolastico' not in dati:
        flash("Benvenuto! Inizia configurando il tuo account.", "info")
        return redirect(url_for('impostazioni'))
    return render_template('home.html', dati=dati)

@app.route('/voti')
@login_required
def voti():
    dati = get_dati()
    filtro = dati.get('filtro_visualizzazione', 'quadrimestre')
    
    voti_formattati = []
    for materia, dettagli in dati.get('materie', {}).items():
        for i, voto in enumerate(dettagli.get('voti', [])):
            if filtro == 'tutto' or voto['quadrimestre'] == dati['quadrimestre']:
                voti_formattati.append({
                    'materia': materia,
                    'valore': voto['valore'],
                    'quadrimestre': voto['quadrimestre'],
                    'indice': i
                })
    
    return render_template('voti.html', dati=dati, voti=voti_formattati)

@app.route('/media')
@login_required
def media():
    dati = get_dati()
    filtro = dati.get('filtro_visualizzazione', 'quadrimestre')
    quadrimestre = dati['quadrimestre']
    
    medie = {}
    for materia, dettagli in dati.get('materie', {}).items():
        voti_filtrati = [
            v['valore'] for v in dettagli.get('voti', []) 
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
@login_required
def orario():
    dati = get_dati()
    giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"]

    if request.method == 'POST':
        try:
            nuovo_orario = {}
            for giorno in giorni:
                nuovo_orario[giorno] = [request.form.get(f"{giorno}_{i}") for i in range(6)]
            
            # Save for current quarter
            if 'orario' not in dati:
                dati['orario'] = {}
            dati['orario'][f'quadrimestre_{dati["quadrimestre"]}'] = nuovo_orario
            save_dati(dati)
            flash('Orario salvato!', 'success')
            
        except Exception as e:
            flash(f'Errore: {str(e)}', 'danger')

    # Load schedule for current quarter
    orario_corrente = dati.get('orario', {}).get(
        f'quadrimestre_{dati["quadrimestre"]}', 
        {giorno: ['']*6 for giorno in giorni}
    )
    
    return render_template('orario.html', 
                         dati=dati,
                         orario=orario_corrente,
                         quadrimestre=dati['quadrimestre'])


@app.route("/api/voti/elimina", methods=["POST"])
@login_required
def elimina_voto():
    try:
        data = request.json
        materia = data.get('materia')
        indice = int(data.get('indice'))
        
        dati = get_dati()
        
        # Check if the subject exists
        if materia not in dati.get('materie', {}):
            return jsonify({"success": False, "error": "Materia non trovata"}), 404
            
        # Check if the index is valid
        voti_materia = dati['materie'][materia].get('voti', [])
        if indice < 0 or indice >= len(voti_materia):
            return jsonify({"success": False, "error": "Indice non valido"}), 400
            
        # Remove the grade
        del dati['materie'][materia]['voti'][indice]
        save_dati(dati)
        
        return jsonify({"success": True})
            
    except Exception as e:
        app.logger.error(f"Errore: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------------------------
# SUBJECT MANAGEMENT
# -----------------------------------------------

@app.route('/aggiungi_materia', methods=['GET', 'POST'])
@login_required
def aggiungi_materia():
    dati = get_dati()
    if request.method == 'POST':
        materia = request.form['materia'].strip()
        if 'materie' not in dati:
            dati['materie'] = {}
        if materia not in dati['materie']:
            dati['materie'][materia] = {'voti': []}
            save_dati(dati)
            flash('Materia aggiunta con successo!', 'success')
            return redirect(url_for('voti'))
        else:
            flash('Materia già esistente!', 'error')
    return render_template('gestione/aggiungi_materia.html', dati=dati)

@app.route('/modifica_materia', methods=['GET', 'POST'])
@login_required
def modifica_materia():
    dati = get_dati()
    if request.method == 'POST':
        vecchio = request.form['vecchio_nome']
        nuovo = request.form['nuovo_nome'].strip()
        if vecchio in dati.get('materie', {}):
            if 'materie' not in dati:
                dati['materie'] = {}
            dati['materie'][nuovo] = dati['materie'].pop(vecchio)
            save_dati(dati)
            flash('Materia modificata!', 'success')
            return redirect(url_for('voti'))
    return render_template('gestione/modifica_materia.html', materie=dati.get('materie', {}).keys())

# -----------------------------------------------
# TEACHER MANAGEMENT
# -----------------------------------------------

@app.route('/aggiungi_professore', methods=['GET', 'POST'])
@login_required
def aggiungi_professore():
    try:
        dati = get_dati()
        if request.method == 'POST':
            professore = request.form.get('professore', '').strip()
            if not professore:
                flash("Il campo non può essere vuoto!", 'error')
                return redirect(url_for('aggiungi_professore'))

            if 'professori' not in dati:
                dati['professori'] = []
                
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
@login_required
def modifica_professore():
    try:
        dati = get_dati()
        if request.method == 'POST':
            vecchio = request.form.get('vecchio_nome', '')
            nuovo = request.form.get('nuovo_nome', '').strip()
            
            if not nuovo:
                flash("Il nuovo nome non può essere vuoto!", 'error')
                return redirect(url_for('modifica_professore'))

            if 'professori' not in dati:
                dati['professori'] = []
                
            if vecchio in dati['professori']:
                index = dati['professori'].index(vecchio)
                dati['professori'][index] = nuovo
                save_dati(dati)
                flash('Professore modificato!', 'success')
            else:
                flash('Professore non trovato!', 'error')
            return redirect(url_for('gestione'))

        return render_template('gestione/modifica_professore.html', 
                            professori=dati.get('professori', []),
                            dati=dati)
    except Exception as e:
        flash(f'Errore: {str(e)}', 'danger')
        return redirect(url_for('gestione'))

# -----------------------------------------------
# GRADE MANAGEMENT
# -----------------------------------------------

@app.route('/aggiungi_voto', methods=['GET', 'POST'])
@login_required
def aggiungi_voto():
    try:
        dati = get_dati()
        if request.method == 'POST':
            materia = request.form.get('materia')
            voto_valore = float(request.form.get('voto'))
            
            if voto_valore < 0 or voto_valore > 10:
                flash("Il voto deve essere tra 0 e 10!", 'danger')
                return redirect(url_for('aggiungi_voto'))
            
            if materia not in dati.get('materie', {}):
                flash("Materia non trovata!", 'danger')
                return redirect(url_for('voti'))

            nuovo_voto = {
                'valore': voto_valore,
                'quadrimestre': dati['quadrimestre'],
                'data': datetime.now().strftime("%Y-%m-%d")
            }
            
            if 'materie' not in dati:
                dati['materie'] = {}
            if materia not in dati['materie']:
                dati['materie'][materia] = {'voti': []}
                
            dati['materie'][materia]['voti'].append(nuovo_voto)
            save_dati(dati)
            flash('Voto aggiunto con successo!', 'success')
            return redirect(url_for('voti'))

        return render_template('gestione/aggiungi_voto.html', 
                             materie=dati.get('materie', {}).keys(),
                             dati=dati)
    except Exception as e:
        flash(f'Errore: {str(e)}', 'danger')
        return redirect(url_for('voti'))

@app.route('/modifica_voto', methods=['GET', 'POST'])
@login_required
def modifica_voto():
    try:
        dati = get_dati()
        
        if request.method == 'POST':
            materia = request.form['materia']
            indice = int(request.form['indice'])
            nuovo_valore = float(request.form['nuovo_voto'])

            if materia not in dati.get('materie', {}):
                flash('❌ Materia non trovata!', 'danger')
                return redirect(url_for('modifica_voto'))

            voti_materia = dati['materie'][materia].get('voti', [])
            
            if indice < 0 or indice >= len(voti_materia):
                flash('❌ Indice non valido!', 'danger')
                return redirect(url_for('modifica_voto'))

            # Keep existing data and update only the value
            voti_materia[indice]['valore'] = nuovo_valore
            save_dati(dati)
            
            flash('✅ Voto modificato con successo!', 'success')
            return redirect(url_for('voti'))

        return render_template('gestione/modifica_voto.html',
                             materie=dati.get('materie', {}),
                             dati=dati)
    except Exception as e:
        flash(f'❌ Errore critico: {str(e)}', 'danger')
        return redirect(url_for('modifica_voto'))

@app.route("/api/voti/elimina-multi", methods=["POST"])
@login_required
def elimina_voti_multi():
    try:
        data = request.json
        votes_to_delete = data.get('votes', [])
        
        dati = get_dati()
        deleted_count = 0

        # Organize by subject and check indices
        subjects = {}
        for vote in votes_to_delete:
            materia = vote.get('materia')
            indice = int(vote.get('indice', -1))
            
            if materia not in dati.get('materie', {}):
                continue
                
            if indice < 0 or indice >= len(dati['materie'][materia].get('voti', [])):
                continue
                
            if materia not in subjects:
                subjects[materia] = []
            subjects[materia].append(indice)

        # Delete in reverse order
        for materia, indices in subjects.items():
            unique_indices = list(set(indices))  # Remove duplicates
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
    
@app.route('/api/imposta-filtro', methods=['POST'])
@login_required
def imposta_filtro():
    dati = get_dati()
    nuovo_filtro = request.json.get('filtro')
    
    if nuovo_filtro not in ['anno', 'quadrimestre']:
        return jsonify({"success": False, "error": "Filtro non valido"}), 400
    
    dati['filtro_voti'] = nuovo_filtro
    save_dati(dati)
    return jsonify({"success": True})

# -----------------------------------------------
# OTHER FUNCTIONS
# -----------------------------------------------

@app.route('/impostazioni', methods=['GET', 'POST'])
@login_required
def impostazioni():
    try:
        dati = get_dati()
        
        if request.method == 'POST':
            # Data validation
            nuovo_quadrimestre = int(request.form['quadrimestre'])
            nuovo_anno = request.form['anno_scolastico'].strip()
            
            if nuovo_quadrimestre not in [1, 2]:
                raise ValueError("Quadrimestre non valido")
                
            if not re.match(r'^\d{4}/\d{4}$', nuovo_anno):
                raise ValueError("Formato anno scolastico non valido (es. 2023/2024)")
            
            # Update data
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
@login_required
def reset():
    if request.method == 'POST':
        if current_user.is_authenticated:
            # Reset only current user's data
            dati = {
                "google_id": current_user.id,
                "email": current_user.email,
                "name": current_user.name,
                "picture": getattr(current_user, 'picture', None),  # Keep profile picture
                "materie": {},
                "professori": [],
                "quadrimestre": 1,
                "anno_scolastico": "2023/2024",
                "orario": {},
                "filtro_visualizzazione": "quadrimestre"
            }
            db.users.update_one({"google_id": current_user.id}, {"$set": dati})
            flash('Reset completato!', 'success')
        return redirect(url_for('home'))
    return render_template('reset.html')

@app.route('/gestione')
@login_required
def gestione():
    return render_template('gestione/menu.html')

@app.route('/api/update-view', methods=['POST'])
@login_required
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
# APPLICATION STARTUP
# -----------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Changed debug to True for easier troubleshooting