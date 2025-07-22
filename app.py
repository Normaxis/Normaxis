from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from functools import wraps
import os, re
from werkzeug.security import generate_password_hash
from models import db, User, Section, Message as MessageModel, Abonnement, Poste, Tache, Risque, Section
from models import User
from models import Abonnement
from datetime import date
from flask_login import current_user
from models import FicheSecurite
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy import func
from utils.auth import require_abonnement
from models import DUERPArchive
from models import FicheDonneesSecurite
from models import AccidentTravail
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'videos')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
upload_folder = app.config['UPLOAD_FOLDER']
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file, folder):
    filename = secure_filename(file.filename)
    full_path = os.path.join('static', folder)
    os.makedirs(full_path, exist_ok=True)
    file_path = os.path.join(full_path, filename)
    file.save(file_path)
    return f'/static/{folder}/{filename}'

app.config['SECRET_KEY'] = 'cle_secrete'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'lefebvre.flavien2018@gmail.com'
app.config['MAIL_PASSWORD'] = 'dcstvxgftayrxohe'
app.config['MAIL_DEFAULT_SENDER'] = 'lefebvre.flavien2018@gmail.com'

db.init_app(app)

from flask_migrate import Migrate
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = None
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

from flask_migrate import Migrate
migrate = Migrate(app, db)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("Accès refusé : vous n'avez pas les droits administrateur.", "danger")
        return redirect(url_for('dashboard'))
    return render_template('admin_dashboard.html')

@app.route('/admin/users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash("Accès refusé.", "danger")
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/promote/<int:user_id>')
@login_required
def promote_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    user = User.query.get(user_id)
    if user:
        user.role = 'admin'
        db.session.commit()
        flash("Utilisateur promu en admin.", "success")
    return redirect(url_for('manage_users'))

@app.route('/admin/demote/<int:user_id>')
@login_required
def demote_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    user = User.query.get(user_id)
    if user and user.id != current_user.id:
        user.role = 'user'
        db.session.commit()
        flash("Utilisateur rétrogradé.", "info")
    return redirect(url_for('manage_users'))

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    user = User.query.get(user_id)
    if user and user.id != current_user.id:
        db.session.delete(user)
        db.session.commit()
        flash("Utilisateur supprimé.", "danger")
    return redirect(url_for('manage_users'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            if user.confirmed:
                login_user(user)
                flash('Connexion réussie.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Veuillez confirmer votre adresse e-mail avant de vous connecter.', 'warning')
        else:
            flash('Identifiants incorrects.', 'danger')

    return render_template('login.html')

@app.route('/get_poste_by_tache/<int:tache_id>')
def get_poste_by_tache(tache_id):
    tache = Tache.query.get(tache_id)
    if tache:
        return jsonify({'poste_id': tache.poste_id})
    return jsonify({'error': 'Tâche introuvable'}), 404

@app.route('/fsp')
@login_required
def fiche_securite_liste():
    fiches = FicheSecurite.query.filter_by(user_id=current_user.id).order_by(FicheSecurite.date_mise_a_jour.desc()).all()
    return render_template('fiche_securite_liste.html', fiches=fiches)

@app.route('/creer_fiche_securite', methods=['GET', 'POST'])
@login_required
def creer_fiche_securite():
    import os
    img_epi_path = os.path.join(app.static_folder, 'img_EPI')
    epis_disponibles = sorted([f for f in os.listdir(img_epi_path) if f.endswith('.png')])

    img_danger_path = os.path.join(app.static_folder, 'img_dangers')
    dangers_disponibles = sorted([f for f in os.listdir(img_danger_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])

    img_interdiction_path = os.path.join(app.static_folder, 'img_interdictions')
    interdictions_disponibles = sorted([f for f in os.listdir(img_interdiction_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])

    fds_disponibles = FicheDonneesSecurite.query.filter_by(user_id=current_user.id).order_by(FicheDonneesSecurite.nom_produit).all()

    if request.method == 'POST':
        titre = request.form.get('titre')
        poste_nom = request.form.get('poste_nom')
        poste_lieu = request.form.get('poste_lieu')
        poste_responsable = request.form.get('poste_responsable')
        taches = request.form.get('taches', '').split(',')
        risques = [request.form.get(f'risque_desc_{i}') for i in range(5)]
        epis = request.form.getlist('epis')
        dangers = request.form.getlist('dangers')
        interdictions = request.form.getlist('interdictions')
        accident = request.form.get('accident')
        regles = request.form.get('regles')
        infos = request.form.get('infos_reglementaires')
        fds_ids = request.form.getlist('fds_ids')
        fds_associees = FicheDonneesSecurite.query.filter(FicheDonneesSecurite.id.in_(fds_ids)).all()

        photo_filename = None
        if 'photo_poste' in request.files:
            photo = request.files['photo_poste']
            if photo and photo.filename:
                filename = secure_filename(photo.filename)
                photo.save(os.path.join('static/uploads', filename))
                photo_filename = filename

        contenu = render_template('fiche_securite_template.html',
            poste_nom=poste_nom,
            poste_lieu=poste_lieu,
            poste_responsable=poste_responsable,
            taches=taches,
            risques=risques,
            epis=epis,
            dangers=dangers,
            interdictions=interdictions,
            accident=accident,
            regles=regles,
            infos_reglementaires=infos,
            photo_filename=photo_filename,
            user=current_user,
            fds_associees=fds_associees  # ✅ à ajouter ici
        )

        fiche = FicheSecurite(
            titre=titre,
            contenu=contenu,
            user_id=current_user.id,
            photo_poste=photo_filename,
            fds_associees=fds_associees
        )
        db.session.add(fiche)
        db.session.commit()
        flash("Fiche créée avec succès.", "success")
        return redirect(url_for('fiche_securite_liste'))

    return render_template("fiche_securite_form.html",
        fiche=None,
        epis_disponibles=epis_disponibles,
        dangers_disponibles=dangers_disponibles,
        interdictions_disponibles=interdictions_disponibles,
        fds_disponibles=fds_disponibles
    )

@app.route('/fsp/<int:fiche_id>')
@login_required
def voir_fiche_securite(fiche_id):
    fiche = FicheSecurite.query.get_or_404(fiche_id)
    if fiche.user_id != current_user.id:
        abort(403)
    return render_template('fiche_securite_voir.html', fiche=fiche)

from werkzeug.utils import secure_filename
import os

@app.route('/fsp/<int:fiche_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_fiche_securite(fiche_id):
    fiche = FicheSecurite.query.get_or_404(fiche_id)
    if fiche.user_id != current_user.id:
        flash("Accès refusé.", "danger")
        return redirect(url_for('fiche_securite_liste'))

    import os
    from bs4 import BeautifulSoup
    from urllib.parse import unquote

    img_epi_path = os.path.join(app.static_folder, 'img_EPI')
    epis_disponibles = sorted([f for f in os.listdir(img_epi_path) if f.endswith('.png')])

    img_danger_path = os.path.join(app.static_folder, 'img_dangers')
    dangers_disponibles = sorted([f for f in os.listdir(img_danger_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])

    img_interdiction_path = os.path.join(app.static_folder, 'img_interdictions')
    interdictions_disponibles = sorted([f for f in os.listdir(img_interdiction_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])

    fds_disponibles = FicheDonneesSecurite.query.filter_by(user_id=current_user.id).order_by(FicheDonneesSecurite.nom_produit).all()

    if request.method == 'POST':
        titre = request.form.get('titre')
        poste_nom = request.form.get('poste_nom')
        poste_lieu = request.form.get('poste_lieu')
        poste_responsable = request.form.get('poste_responsable')
        taches = request.form.get('taches', '').split(',')
        risques = [request.form.get(f'risque_desc_{i}') for i in range(5)]
        epis = request.form.getlist('epis')
        dangers = request.form.getlist('dangers')
        interdictions = request.form.getlist('interdictions')
        accident = request.form.get('accident')
        regles = request.form.get('regles')
        infos = request.form.get('infos_reglementaires')
        fds_ids = request.form.getlist('fds_ids')
        fiche.fds_associees = FicheDonneesSecurite.query.filter(FicheDonneesSecurite.id.in_(fds_ids)).all()

        if 'photo_poste' in request.files:
            photo = request.files['photo_poste']
            if photo and photo.filename:
                filename = secure_filename(photo.filename)
                photo.save(os.path.join('static/uploads', filename))
                fiche.photo_poste = filename

        contenu = render_template('fiche_securite_template.html',
            poste_nom=poste_nom,
            poste_lieu=poste_lieu,
            poste_responsable=poste_responsable,
            taches=taches,
            risques=risques,
            epis=epis,
            dangers=dangers,
            interdictions=interdictions,
            accident=accident,
            regles=regles,
            infos_reglementaires=infos,
            photo_filename=fiche.photo_poste,
            user=current_user,
            fds_associees=fiche.fds_associees  # ✅ correction ici
        )

        fiche.titre = titre
        fiche.contenu = contenu
        fiche.date_mise_a_jour = datetime.utcnow()
        db.session.commit()
        flash("Fiche mise à jour avec succès.", "success")
        return redirect(url_for('fiche_securite_liste'))

    # Extraction via BeautifulSoup
    soup = BeautifulSoup(fiche.contenu, 'html.parser')

    def extract_text(soup, label):
        for p in soup.find_all('p'):
            if label in p.get_text():
                return p.get_text().replace(label, '').strip()
        return ''

    fiche.poste_nom = extract_text(soup, 'Intitulé :')
    fiche.poste_lieu = extract_text(soup, 'Lieu :')
    fiche.poste_responsable = extract_text(soup, 'Responsable :')

    taches_section = soup.find('div', class_='section-title', string='2. Description des tâches')
    fiche.taches = ''
    if taches_section:
        ul = taches_section.find_next_sibling('ul')
        if ul:
            fiche.taches = ', '.join(li.get_text(strip=True) for li in ul.find_all('li'))

    fiche.risques = [div.get_text().replace('Description :', '').strip()
                     for div in soup.find_all('div', class_='alert alert-warning')]

    fiche.epis = []
    fiche.dangers = []
    fiche.interdictions = []

    for img in soup.find_all('img', src=True):
        src = unquote(img['src'])
        if '/static/img_EPI/' in src:
            fiche.epis.append(src.split('/img_EPI/')[-1])
        if '/static/img_dangers/' in src:
            fiche.dangers.append(src.split('/img_dangers/')[-1])
        if '/static/img_interdictions/' in src:
            fiche.interdictions.append(src.split('/img_interdictions/')[-1])

    acc_section = soup.find('div', class_='section-title', string='5. Conduite à tenir en cas d’accident')
    fiche.accident = acc_section.find_next_sibling('p').get_text() if acc_section else ''

    reg_section = soup.find('div', class_='section-title', string='6. Règles de sécurité spécifiques')
    fiche.regles = reg_section.find_next_sibling('p').get_text() if reg_section else ''

    info_section = soup.find('div', class_='section-title', string='7. Informations réglementaires')
    fiche.infos_reglementaires = info_section.find_next_sibling('p').get_text() if info_section else ''

    return render_template("fiche_securite_form.html",
        fiche=fiche,
        epis_disponibles=epis_disponibles,
        dangers_disponibles=dangers_disponibles,
        interdictions_disponibles=interdictions_disponibles,
        fds_disponibles=fds_disponibles
    )

@app.route('/fsp/<int:fiche_id>/supprimer')
@login_required
def supprimer_fiche_securite(fiche_id):
    fiche = FicheSecurite.query.get_or_404(fiche_id)
    if fiche.user_id != current_user.id:
        abort(403)
    db.session.delete(fiche)
    db.session.commit()
    flash("Fiche supprimée.", "info")
    return redirect(url_for('fiche_securite_liste'))

@app.route('/modifier_poste/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_poste(id):
    poste = Poste.query.get_or_404(id)

    if poste.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        poste.nom = request.form['nom']
        poste.description = request.form['description']

        # Gestion de la photo du poste
        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file and photo_file.filename != '':
                filename = secure_filename(photo_file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo_file.save(filepath)
                poste.photo = filename

        db.session.commit()
        flash("✅ Poste mis à jour avec succès.", "success")
        return redirect(url_for('liste_postes'))

    return render_template('modifier_poste.html', poste=poste)

import os

@app.route('/modifier_risque/<int:id>', methods=['GET', 'POST'])
def modifier_risque(id):
    risque = Risque.query.get_or_404(id)
    dossier_epi = os.path.join(app.static_folder, 'img_EPI')
    epis_disponibles = os.listdir(dossier_epi)

    if request.method == 'POST':
        risque.description = request.form['description']
        risque.gravite = int(request.form['gravite'])
        risque.frequence = int(request.form['frequence'])
        risque.epis = request.form.getlist('epis')  # Liste d'EPIs cochés
        db.session.commit()
        flash("Risque mis à jour avec succès", "success")
        return redirect(url_for('liste_risques'))

    return render_template("modifier_risque.html", risque=risque,
                           epis=epis_disponibles, selected_epis=risque.epis or [])

@app.route('/abonnements')
@login_required
def abonnements():
    return render_template('packs.html', 
                           publishable_key=os.getenv("STRIPE_PUBLISHABLE_KEY"), 
                           price_basic=os.getenv("STRIPE_BASIC_PRICE_ID"),
                           price_premium=os.getenv("STRIPE_PREMIUM_PRICE_ID"))

@app.route('/paiement')
@login_required
def paiement():
    return render_template('paiement.html')

@app.route('/poste/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau_poste():
    if request.method == 'POST':
        nom = request.form.get('nom')
        description = request.form.get('description')
        if nom and description:
            nouveau = Poste(nom=nom, description=description, user_id=current_user.id)
            db.session.add(nouveau)
            db.session.commit()
            flash("Poste créé avec succès.", "success")
            return redirect(url_for('liste_postes'))
        else:
            flash("Tous les champs sont obligatoires.", "warning")
    return render_template('post_form.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", password):
            flash("Mot de passe invalide. Vérifiez les critères de sécurité.", "warning")
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash("Adresse e-mail déjà utilisée.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("Nom d'utilisateur déjà pris.", "danger")
        else:
            hashed = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed)
            db.session.add(new_user)
            db.session.commit()
            flash("Compte créé avec succès. Connectez-vous.", "success")
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/admin/repondre/<int:message_id>', methods=['GET', 'POST'])
@login_required
def repondre_message(message_id):
    if current_user.role != 'admin':
        abort(403)


    msg = Message.query.get_or_404(message_id)

    if request.method == 'POST':
        reponse = request.form['reponse']

        # Enregistrement de la réponse dans une table ou envoi d'email
        # Exemple : stocker dans msg.reponse et marquer comme répondu
        msg.reponse = reponse
        msg.traite = True
        db.session.commit()

        flash("Réponse envoyée avec succès.", "success")
        return redirect(url_for('admin_messages'))

    return render_template('repondre_message.html', msg=msg)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash("Lien de réinitialisation invalide ou expiré.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form['password']
        # Ajoute ici une validation supplémentaire si nécessaire
        user.set_password(password)
        db.session.commit()
        flash("Mot de passe mis à jour avec succès.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html', email=user.email)

@app.route('/poste/<int:poste_id>/ajouter_tache', methods=['GET', 'POST'])
@login_required
def ajouter_tache(poste_id):
    poste = Poste.query.get_or_404(poste_id)

    if poste.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        nom = request.form['nom']
        nouvelle_tache = Tache(nom=nom, poste_id=poste.id, user_id=current_user.id)
        db.session.add(nouvelle_tache)
        db.session.commit()
        flash('Tâche ajoutée avec succès.', 'success')
        return redirect(url_for('liste_postes'))

    return render_template('tache_form.html', poste=poste)

@app.route('/ajouter_section/<theme>', methods=['GET', 'POST'])
@login_required
def ajouter_section(theme):
    if not current_user.is_authenticated:
     flash("Session expirée. Veuillez vous reconnecter.", "warning")
     return redirect(url_for('login'))

    print(f"[DEBUG] current_user.id = {current_user.id}")

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        video_file = request.files.get('video')

        video_url = None
        if video_file and video_file.filename != '':
            video_url = '/static/' + save_file(video_file, 'videos')

        nouvelle_section = Section(
            title=title,
            content=content,
            theme=theme,
            user_id=current_user.id,
            video_url=video_url
        )
        db.session.add(nouvelle_section)
        db.session.commit()
        flash('Section ajoutée avec succès.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('admin/edit_section.html', section=None, theme=theme)

@app.route('/admin/sections/<theme>/update', methods=['GET', 'POST'])
@app.route('/admin/sections/<theme>/update/<int:section_id>', methods=['GET', 'POST'])
@login_required
def update_section(theme, section_id=None):
    section = Section.query.get(section_id) if section_id else None

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        video_file = request.files.get('video')
        attached_file = request.files.get('file')

        if not section:
            section = Section(theme=theme)

        section.title = title
        section.content = content


        if video_file and video_file.filename:
            video_path = save_file(video_file, folder='videos')
            section.video_url = url_for('static', filename='videos/' + os.path.basename(video_path))

        if attached_file and attached_file.filename:
            file_path = save_file(attached_file, folder='files')
            section.file_path = os.path.join('files', os.path.basename(file_path))

        db.session.add(section)
        db.session.commit()
        flash("Section enregistrée avec succès.", "success")
        return redirect(url_for('edit_sections'))

    return render_template('update_section.html', section=section, theme=theme)

@app.route('/edit_section/<int:section_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_section(section_id):
    section = Section.query.get_or_404(section_id)
    theme = section.theme  # déduit simplement depuis l'objet

    if request.method == 'POST':
        section.title = request.form['title']
        section.content = request.form['content']

        if 'video' in request.files:
            video = request.files['video']
            if video and video.filename != '':
                video_filename = secure_filename(video.filename)
                video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
                video.save(video_path)
                section.video_url = video_filename

        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                file_filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_filename)
                file.save(file_path)
                section.file_path = file_filename

        db.session.commit()
        flash("Section mise à jour avec succès.", "success")
        return redirect(url_for('edit_sections'))

    return render_template('edit_section_form.html', section=section, theme=theme)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if user:
            try:
                token = s.dumps(email, salt='password-reset')
                reset_link = url_for('reset_password', token=token, _external=True)
                msg = Message("🔐 Réinitialisation de votre mot de passe",
                              recipients=[email])
                msg.body = f"Bonjour,\n\nCliquez sur le lien suivant pour réinitialiser votre mot de passe : {reset_link}\n\nCe lien est valable 30 minutes."
                mail.send(msg)
                flash("Un lien de réinitialisation vous a été envoyé par e-mail.", "info")
            except Exception as e:
                flash("Erreur lors de l'envoi de l'e-mail.", "danger")
        else:
            flash("Aucun compte trouvé avec cet e-mail.", "warning")

    return render_template('forgot_password.html')

@app.route('/postes')
@login_required
def liste_postes():
    postes = Poste.query.filter_by(user_id=current_user.id).all()
    return render_template('liste_postes.html', postes=postes)

@app.route('/risque/<int:id>/supprimer', methods=['POST'])
@login_required
def supprimer_risque(id):
    risque = Risque.query.get_or_404(id)

    if risque.user_id != current_user.id:
        abort(403)

    db.session.delete(risque)
    db.session.commit()
    flash("Risque supprimé avec succès.", "success")
    return redirect(url_for('tache_detail', id=risque.tache_id))

@app.route('/poste/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer_poste(id):
    poste = Poste.query.get_or_404(id)

    if poste.user_id != current_user.id:
        abort(403)

    db.session.delete(poste)
    db.session.commit()
    flash("Poste supprimé avec succès", "success")
    return redirect(url_for('liste_postes'))

from flask_login import login_required, current_user
from datetime import date
from models import Abonnement, Section  # adapte selon ton modèle réel

@app.route('/dashboard')
@login_required
def dashboard():
    theme_content = {}
    themes = ['securite', 'qualite', 'environnement']

    for theme in themes:
        if current_user.has_active_abonnement(theme):
            # ❌ Ne filtre plus sur user_id pour que toutes les sections du thème soient visibles
            theme_content[theme] = Section.query.filter_by(theme=theme).all()

    return render_template('dashboard.html', theme_content=theme_content)

@app.route('/debug-sections')
@login_required
def debug_sections():
    sections = Section.query.all()
    for sec in sections:
        print(f"ID: {sec.id} | Thème: {sec.theme} | Titre: {sec.title} | User ID: {sec.user_id}")
    return "Voir console Flask"

@app.route('/profil/<int:id>', methods=['GET', 'POST'])
@login_required
def profil(id):
    if current_user.id != id:
        flash("⛔ Accès non autorisé.", "danger")
        return redirect(url_for('dashboard'))

    user = current_user

    if request.method == 'POST':
        user.nom = request.form.get('nom', '')
        user.prenom = request.form.get('prenom', '')
        user.fonction = request.form.get('fonction', '')
        user.telephone = request.form.get('telephone', '')
        user.entreprise = request.form.get('entreprise', '')
        user.adresse = request.form.get('adresse', '')

        # Gestion du fichier logo
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and logo_file.filename != '':
                filename = secure_filename(logo_file.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logo_file.save(upload_path)
                user.logo = filename

        db.session.commit()
        flash("✅ Profil mis à jour avec succès.", "success")
        return redirect(url_for('profil', id=user.id))

    return render_template('profil.html', user=user)

@app.route('/tache/<int:tache_id>')
@login_required
def detail_tache(tache_id):
    tache = Tache.query.get_or_404(tache_id)

    if tache.user_id != current_user.id:
        abort(403)

    return render_template('detail_tache.html', tache=tache, id=tache.id)

@app.route('/admin/attribuer_abonnement/<int:user_id>', methods=['GET', 'POST'])
@login_required
def attribuer_abonnement(user_id):
    if current_user.role != 'admin':
        flash("Accès non autorisé", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        theme = request.form['theme']
        db.session.commit()
        flash("Abonnement attribué avec succès.", "success")
        return redirect(url_for('admin_users'))

    return render_template('attribuer_abonnement.html', user=user)

@app.route('/theme/securite')
@login_required
def theme_securite():
    if not current_user.has_active_abonnement('securite'):
        flash("Accès non autorisé", "danger")
        return redirect(url_for('dashboard'))
    return render_template('theme_securite.html')

@app.route('/duerp')
@login_required
def duerps():
    postes = Poste.query.filter_by(user_id=current_user.id).all()
    return render_template('duerp.html', postes=postes)

@app.route('/duerp/archive', methods=['POST'])
@login_required
def archiver_duerp():
    postes = Poste.query.filter_by(user_id=current_user.id).all()
    html_snapshot = render_template('duerp.html', postes=postes)
    
    archive = DUERPArchive(
        user_id=current_user.id,
        contenu_html=html_snapshot,
        commentaire=request.form.get('commentaire', 'Archivage manuel')
    )
    db.session.add(archive)
    db.session.commit()
    flash("📦 DUERP archivé avec succès.", "success")
    return redirect(url_for('duerps'))

@app.route('/duerp/archive/<int:archive_id>')
@login_required
def voir_archive_duerp(archive_id):
    archive = DUERPArchive.query.get_or_404(archive_id)
    if archive.user_id != current_user.id and current_user.role != 'admin':
        abort(403)
    return archive.contenu_html  # rendu brut (HTML enregistré)

@app.route('/duerp/historique')
@login_required
def historique_duerp():
    query = DUERPArchive.query.filter_by(user_id=current_user.id)

    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    mot_cle = request.args.get('mot_cle')

    if date_debut:
        query = query.filter(DUERPArchive.date_archivage >= date_debut)
    if date_fin:
        query = query.filter(DUERPArchive.date_archivage <= date_fin)
    if mot_cle:
        query = query.filter(DUERPArchive.commentaire.ilike(f"%{mot_cle}%"))

    archives = query.order_by(DUERPArchive.date_archivage.desc()).all()
    return render_template('duerp_historique.html', archives=archives)

@login_required
def upload_video():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if 'video' not in request.files:
            flash('Aucun fichier envoyé')
            return redirect(request.url)
        file = request.files['video']
        if file.filename == '':
            flash('Fichier invalide')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('Vidéo uploadée avec succès')
        return redirect(url_for('admin_dashboard'))
    return render_template('upload.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        flash("Le lien a expiré. Veuillez vous réinscrire.", "danger")
        return redirect(url_for('register'))
    except BadSignature:
        flash("Lien de confirmation invalide.", "danger")
        return redirect(url_for('register'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for('register'))
    if user.confirmed:
        flash("Votre compte est déjà confirmé. Vous pouvez vous connecter.", "info")
    else:
        user.confirmed = True
        db.session.commit()
        flash("Votre compte a été confirmé avec succès !", "success")
    return redirect(url_for('login'))

@app.route('/resend-confirmation', methods=['GET', 'POST'])
def resend_confirmation():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Aucun compte n'est associé à cette adresse e-mail.", "danger")
            return redirect(url_for('resend_confirmation'))
        if user.confirmed:
            flash("Ce compte est déjà confirmé. Vous pouvez vous connecter.", "info")
            return redirect(url_for('login'))
        token = s.dumps(email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        msg = Message('Confirmez votre adresse e-mail', recipients=[email])
        msg.body = f"Cliquez ici pour confirmer votre compte : {confirm_url}"
        mail.send(msg)
        flash("Un nouveau lien de confirmation vous a été envoyé par e-mail.", "success")
        return redirect(url_for('login'))
    return render_template('resend_confirmation.html')

@app.route('/admin/download/<filename>')
@login_required
def download_video(filename):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/admin/delete/<filename>')
@login_required
def delete_video(filename):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash("Vidéo supprimée.", "success")
    else:
        flash("Fichier introuvable.", "danger")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Aucun compte trouvé avec cet e-mail.", "warning")
            return redirect(url_for('admin_login'))

        if not check_password_hash(user.password, password):
            flash("Mot de passe incorrect.", "warning")
            return redirect(url_for('admin_login'))

        if not user.confirmed:
            flash("Veuillez confirmer votre adresse e-mail avant de vous connecter.", "warning")
            return redirect(url_for('admin_login'))

        if user.role != 'admin':
            flash("Accès refusé : vous n'êtes pas administrateur.", "danger")
            return redirect(url_for('login'))

        login_user(user)
        flash("Connexion admin réussie.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_login.html')

@app.route('/admin/users/search')
@login_required
def search_users():
    if current_user.role != 'admin':
        return jsonify({'error': 'Accès refusé'}), 403

    keyword = request.args.get('keyword', '').lower()
    role = request.args.get('role')
    confirmed = request.args.get('confirmed')
    page = int(request.args.get('page', 1))
    per_page = 10

    query = User.query
    if keyword:
        query = query.filter((User.username.ilike(f"%{keyword}%")) | (User.email.ilike(f"%{keyword}%")))
    if role:
        query = query.filter_by(role=role)
    if confirmed == 'oui':
        query = query.filter_by(confirmed=True)
    elif confirmed == 'non':
        query = query.filter_by(confirmed=False)

    pagination = query.paginate(page=page, per_page=per_page)
    users_data = []
    for user in pagination.items:
        abonnements = [{
            'id': ab.id,
            'theme': ab.theme,
            'date_debut': ab.date_debut.isoformat(),
            'date_fin': ab.date_fin.isoformat()
        } for ab in user.abonnements]
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'confirmed': 'Oui' if user.confirmed else 'Non',
            'abonnements': abonnements
        })

    return jsonify({
        'users': users_data,
        'total': pagination.total,
        'per_page': per_page,
        'page': page
    })

@app.route('/admin/users/create', methods=['POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        return jsonify({'error': 'Accès refusé'}), 403

    if 'excel' in request.files:
        # Traitement du fichier Excel
        # ...
        return jsonify({'success': True, 'message': 'Import Excel terminé.'})

    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role', 'user')

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email déjà utilisé.'})

    user = User(
        username=username,
        email=email,
        password=generate_password_hash(password),
        role=role,
        confirmed=True
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin/abonnement/create', methods=['POST'])
@login_required
def create_abonnement():
    if current_user.role != 'admin':
        return jsonify(success=False, error="Accès refusé")

    user_id = request.form.get('user_id')
    theme = request.form.get('theme')
    date_debut = request.form.get('date_debut')
    date_fin = request.form.get('date_fin')

    if not all([user_id, theme, date_debut, date_fin]):
        return jsonify(success=False, error="Champs manquants")

    try:
        ab = Abonnement(user_id=user_id, theme=theme, date_debut=date.fromisoformat(date_debut), date_fin=date.fromisoformat(date_fin))
        db.session.add(ab)
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/admin/abonnement/<int:user_id>/ajouter', methods=['POST'])
@admin_required
def ajouter_abonnement(user_id):
    theme = request.form.get('theme')
    user = User.query.get_or_404(user_id)

    # Vérifie que l'abonnement n'existe pas déjà
    existing = Abonnement.query.filter_by(user_id=user.id, theme=theme).first()
    if existing:
        flash("L'utilisateur a déjà accès à ce thème.", "warning")
        return redirect(url_for('admin_users'))

    # Ajoute l'abonnement valide pour 1 an
    new_abonnement = Abonnement(
        user_id=user.id,
        theme=theme,
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=365)
    )
    db.session.add(new_abonnement)
    db.session.commit()
    flash(f"Abonnement au thème '{theme}' ajouté à {user.username}.", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/abonnement/delete/<int:abonnement_id>', methods=['DELETE'])
@login_required
def delete_abonnement(abonnement_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Accès refusé'}), 403
    ab = Abonnement.query.get_or_404(abonnement_id)
    db.session.delete(ab)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/papripact')
@login_required
def papripact():
    tri = request.args.get('tri')
    ordre = request.args.get('ordre', 'asc')

    query = Risque.query.filter_by(user_id=current_user.id)

    if tri == 'score':
        if ordre == 'desc':
            query = query.order_by(Risque.score.desc())
        else:
            query = query.order_by(Risque.score.asc())

    risques = query.all()

    return render_template('papripact.html', risques=risques)

@app.route('/poste/<int:id>/fiche_securite')
@login_required
def fiche_securite(id):
    poste = Poste.query.get_or_404(id)
    user = current_user
    risques = poste.risques

    # 🔄 Agrégation des EPI cochés dans les risques
    epis_utilises = set()
    for risque in risques:
        if risque.epis:
            epis_utilises.update(risque.epis)

    return render_template('fiche_securite.html',
                           poste=poste,
                           user=user,
                           risques=risques,
                           epis_utilises=sorted(epis_utilises))  # Tri facultatif

@app.route('/risque/ajouter/<int:tache_id>', methods=['GET', 'POST'])
@login_required
def ajouter_risque(tache_id):
    tache = Tache.query.get_or_404(tache_id)

    if tache.user_id != current_user.id:
        flash("Accès non autorisé à cette tâche.", "danger")
        return redirect(url_for('dashboard'))

    postes = Poste.query.all()
    dossier_epi = os.path.join(app.static_folder, 'img_EPI')
    epis_disponibles = os.listdir(dossier_epi)  # ← charge les fichiers images

    if request.method == 'POST':
        # ... récupération des champs du formulaire ...
        epis = request.form.getlist('epis[]')  # ← récupère les EPIs cochés
        # ... création de l'objet Risque ...
        risque = Risque(
            # ...
            epis=epis,  # ← les epis sont enregistrés
            # ...
        )
        db.session.add(risque)
        db.session.commit()
        flash("Risque ajouté avec succès.", "success")
        return redirect(url_for('liste_postes'))

    return render_template('ajouter_risque.html',
                           tache=tache,
                           postes=postes,
                           epis=epis_disponibles,
                           selected_epis=[])


@app.route('/edit_risque/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_risque(id):
    risque = Risque.query.get_or_404(id)

    # 📂 Liste des images EPI dans le dossier static/img_EPI
    dossier_epi = os.path.join(app.static_folder, 'img_EPI')
    epis_disponibles = sorted([f for f in os.listdir(dossier_epi) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    if request.method == 'POST':
        risque.famille_danger = request.form.get('famille_danger')
        risque.description = request.form.get('description')
        risque.dommages = request.form.get('dommages_potentiels')
        risque.mesures_prevention = request.form.get('mesures_prevention')
        risque.gravite = int(request.form.get('gravite'))
        risque.frequence = int(request.form.get('frequence'))
        risque.maitrise = float(request.form.get('maitrise'))
        risque.actions_a_mener = request.form.get('actions_a_mener')
        risque.responsable_action = request.form.get('responsable_action')
        risque.etat_action = 'etat_action' in request.form
        risque.cout_action = float(request.form.get('cout_action')) if request.form.get('cout_action') else None
        risque.delai_mise_en_oeuvre = request.form.get('delai')
        risque.date_realisation = request.form.get('date_realisation') or None

        # 🔁 Récupération des EPI cochés
        risque.epis = request.form.getlist('epis')

        # 🧮 Recalcul du score
        risque.score = (risque.frequence * risque.gravite) * risque.maitrise

        db.session.commit()
        flash('✅ Risque modifié avec succès.', 'success')
        return redirect(url_for('papripact'))

    return render_template('edit_risque.html',
                           risque=risque,
                           epis=epis_disponibles,
                           selected_epis=risque.epis or [])

@app.route('/tache/<int:id>')
@login_required
def tache_detail(id):
    tache = Tache.query.get_or_404(id)

    if tache.user_id != current_user.id:
        abort(403)

    risques = Risque.query.filter_by(tache_id=id, user_id=current_user.id).all()
    return render_template('tache_detail.html', tache=tache, id=id)

@app.route('/cancel')
@login_required
def cancel():
    return render_template('cancel.html')

@app.route('/admin/users/toggle_access', methods=['POST'])
@login_required
def toggle_user_access():
    if current_user.role != 'admin':
        return jsonify(success=False), 403
    user_id = request.form.get('user_id')
    theme = request.form.get('theme')
    user = User.query.get(user_id)
    if not user or theme not in ['securite', 'qualite', 'environnement']:
        return jsonify(success=False)
    current_value = getattr(user, theme)
    setattr(user, theme, not current_value)
    db.session.commit()
    return jsonify(success=True)

@app.route('/subscribe')
@login_required
def subscription_page():
    return render_template('abonnement.html')  # à adapter si le fichier HTML porte un autre nom

@app.route('/subscribe/<theme>')
@login_required
def subscribe(theme):
    if theme not in ['securite', 'qualite', 'environnement']:
        flash("Thème invalide.", "danger")
        return redirect(url_for('packs'))

    return render_template(
        'checkout.html',
        theme=theme,
        publishable_key=os.getenv('STRIPE_PUBLISHABLE_KEY')  # Ou config['STRIPE_PUBLISHABLE_KEY']
    )

import stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    data = request.get_json()
    theme = data.get('theme')

    if theme not in ['securite', 'qualite', 'environnement']:
        return jsonify({'error': 'Thème non valide.'}), 400

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': f'Abonnement {theme.capitalize()}'},
                    'unit_amount': 900,  # 9€ en centimes
                    'recurring': {'interval': 'month'}
                },
                'quantity': 1
            }],
            mode='subscription',
            success_url=url_for('success', _external=True) + f'?theme={theme}',
            cancel_url=url_for('cancel', _external=True),
            customer_email=current_user.email
        )
        return jsonify({'id': session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/success')
@login_required
def success():
    theme = request.args.get('theme')
    # Ici tu peux enregistrer un abonnement dans ta base
    flash("Abonnement activé avec succès !", "success")
    return render_template('success.html', theme=theme)

@app.route('/admin/section/edit/<theme>', methods=['GET', 'POST'])
@login_required
def edit_theme_section(theme):
    if current_user.role != 'admin':
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('dashboard'))

    if theme not in ['securite', 'qualite', 'environnement']:
        flash("Thème inconnu.", "warning")
        return redirect(url_for('admin_dashboard'))

    section = Section.query.filter_by(theme=theme).first()
    if not section:
        section = Section(
        title='',
        content='',
        theme=theme,
        user_id=current_user.id
    )
    db.session.add(section)
    db.session.commit()

    if request.method == 'POST':
        section.title = request.form['title']
        section.content = request.form['content']

        if 'video' in request.files and request.files['video'].filename:
            video_file = request.files['video']
            video_filename = secure_filename(video_file.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
            video_file.save(video_path)
            section.video_url = video_filename

        if 'file' in request.files and request.files['file'].filename:
            doc_file = request.files['file']
            file_filename = secure_filename(doc_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_filename)
            doc_file.save(file_path)
            section.file_path = file_filename

        db.session.commit()
        flash("Section mise à jour avec succès.", "success")
        return redirect(url_for('edit_sections'))

    return render_template("add_section.html", theme=theme, section=section)

@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    if request.method == 'POST':
        sujet = request.form['sujet']
        message = request.form['message']

        if not sujet or not message:
            flash("Sujet et message requis.", "warning")
            return redirect(url_for('contact'))

        try:
            msg = Message(subject=f"Message de {current_user.username} : {sujet}",
                          recipients=[app.config['MAIL_DEFAULT_SENDER']])
            msg.body = f"De : {current_user.email}\n\n{message}"
            mail.send(msg)
            flash("Votre message a été envoyé à l'administrateur.", "success")
        except Exception as e:
            flash("Erreur lors de l'envoi du message.", "danger")

    return render_template('contact.html')

@app.route('/contenu')
@login_required
def contenu():
    theme_content = {}
    themes = ['securite', 'qualite', 'environnement']

    for theme in themes:
        if current_user.has_active_abonnement(theme):
            theme_content[theme] = Section.query.filter_by(theme=theme).all()

    return render_template('contenu.html', theme_content=theme_content)

@app.route('/add', methods=['GET', 'POST'])
def add_section():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        video_url = None
        video = request.files.get('video')
        if video and video.filename:
            video_url = save_file(video, 'videos')

        section = {'id': len(Section) + 1, 'title': title, 'content': content, 'video_url': video_url}
        Section.append(section)
        flash('Section ajoutée !', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_section.html')

# 🖥️ Page d'affichage
@app.route('/')
def homepage():
    return render_template('dashboard.html', sections=Section)

@app.route('/delete/<int:section_id>', methods=['POST'])
@login_required
def delete_section(section_id):
    section = Section.query.get_or_404(section_id)

    if section.user_id != current_user.id and current_user.role != 'admin':
        flash("⛔ Accès refusé.", "danger")
        return redirect(url_for('dashboard'))

    db.session.delete(section)
    db.session.commit()
    flash("✅ Section supprimée avec succès.", "success")
    return redirect(url_for('dashboard'))

@app.route('/admin/edit_sections/<theme>/delete/<int:section_id>', methods=['POST'])
@login_required
def delete_section_admin(theme, section_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    section = Section.query.get_or_404(section_id)
    db.session.delete(section)
    db.session.commit()
    flash("Section supprimée avec succès.", "success")
    return redirect(url_for('edit_sections'))

@app.route('/admin/edit_sections')
@login_required
def edit_sections():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    # Organise les sections par thème
    data = {'securite': [], 'qualite': [], 'environnement': []}
    all_sections = Section.query.all()
    for section in all_sections:
        if section.theme == 'securite':
            data['securite'].append(section)
        if section.theme == 'qualite' :
            data['qualite'].append(section)
        if section.theme == 'environnement':
            data['environnement'].append(section)

    return render_template("admin_edit_sections.html", data=data)

@app.route('/admin/edit_sections/<theme>/edit/<int:section_id>', methods=['GET', 'POST'])
@login_required
def edit_section_form(theme, section_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    section = Section.query.get_or_404(section_id)

    if request.method == 'POST':
        # Titre et contenu
        section.title = request.form['title']
        section.content = request.form['content']

        # Vidéo (facultative)
        video_file = request.files.get('video')
        if video_file and video_file.filename:
            section.video_url = save_file(video_file, folder='videos')

        # Fichier attaché (facultatif)
        file = request.files.get('file')
        if file and file.filename:
            section.file_path = save_file(file, folder='documents')

        # Sauvegarde en BDD
        db.session.commit()
        flash("Section mise à jour avec succès.", "success")
        return redirect(url_for('edit_sections'))

    return render_template("add_section.html", theme=theme, section=section)

@app.route('/admin/edit_sections/<theme>/add', methods=['GET', 'POST'])
@login_required
def add_section_form(theme):
    if not current_user.is_authenticated:
        flash("Session expirée. Veuillez vous reconnecter.", "warning")
        return redirect(url_for('login'))

    print(f"[DEBUG] user connecté ? {current_user.is_authenticated}, ID = {current_user.id}")

    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        video_url = None
        file_path = None

        video_file = request.files.get('video')
        if video_file and video_file.filename:
            video_url = save_file(video_file, folder='videos')

        file = request.files.get('file')
        if file and file.filename:
            file_path = save_file(file, folder='documents')

        nouvelle_section = Section(
            title=title,
            content=content,
            theme=theme,
            video_url=video_url,
            file_path=file_path,
            user_id=current_user.id
        )

        db.session.add(nouvelle_section)
        db.session.commit()
        flash("Section ajoutée avec succès.", "success")
        return redirect(url_for('dashboard'))

    return render_template("add_section.html", theme=theme, section=None)

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/messages')
@login_required
def admin_messages():
    if current_user.role != 'admin':
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('dashboard'))

    messages = MessageModel.query.order_by(MessageModel.timestamp.desc()).all()
    return render_template('admin_messages.html', messages=messages)

@app.route('/admin/stats')
@login_required
def admin_stats():
    if current_user.role != 'admin':
        flash("Accès réservé aux administrateurs.", "danger")
        return redirect(url_for('dashboard'))

    total_users = User.query.count()
    total_admins = User.query.filter_by(role='admin').count()
    confirmed_users = User.query.filter_by(confirmed=True).count()
    unconfirmed_users = User.query.filter_by(confirmed=False).count()

    from sqlalchemy import func

    abonnements_securite = Abonnement.query.filter_by(theme='securite').count()
    abonnements_qualite = Abonnement.query.filter_by(theme='qualite').count()
    abonnements_environnement = Abonnement.query.filter_by(theme='environnement').count()


    abonnements_total = abonnements_securite + abonnements_qualite + abonnements_environnement

    stats = {
        "total_users": total_users,
        "total_admins": total_admins,
        "confirmed_users": confirmed_users,
        "unconfirmed_users": unconfirmed_users,
        "total_abonnements": abonnements_total,
        "abonnements_actifs": abonnements_total,  # si pas de notion d’expiration
        "abonnements_expires": 0,  # placeholder
        "abonnements_par_theme": {
            "securite": abonnements_securite,
            "qualite": abonnements_qualite,
            "environnement": abonnements_environnement
        }
    }

    return render_template('admin_stats.html', stats=stats)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/fds')
@login_required
def liste_fds():
    query = FicheDonneesSecurite.query.filter_by(user_id=current_user.id)


    # Filtres
    nom = request.args.get('nom')
    fournisseur = request.args.get('fournisseur')
    dangereux = request.args.get('dangereux')

    if nom:
        query = query.filter(FicheDonneesSecurite.nom_produit.ilike(f"%{nom}%"))
    if fournisseur:
        query = query.filter(FicheDonneesSecurite.fournisseur.ilike(f"%{fournisseur}%"))
    if dangereux == 'on':
        query = query.filter_by(dangereux=True)

    fds_list = query.order_by(FicheDonneesSecurite.date_fds.desc()).all()
    return render_template('liste_fds.html', fds_list=fds_list)

@app.route('/fds/<int:fds_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_fds(fds_id):
    fds = FicheDonneesSecurite.query.get_or_404(fds_id)

    # Protection : seul le créateur ou un admin peut modifier
    if fds.user_id != current_user.id and current_user.role != 'admin':
        abort(403)

    if request.method == 'POST':
        fds.nom_produit = request.form['nom_produit']
        fds.fournisseur = request.form['fournisseur']
        fds.date_fds = datetime.strptime(request.form['date_fds'], '%Y-%m-%d')
        fds.numero_version = request.form['numero_version']
        fds.dangereux = 'dangereux' in request.form

        fichier = request.files.get('fichier_pdf')
        if fichier and allowed_file(fichier.filename):
            filename = secure_filename(fichier.filename)
            chemin = os.path.join('static/uploads/fds', filename)
            fichier.save(chemin)
            fds.fichier_pdf = chemin  # mise à jour du chemin

        db.session.commit()
        flash("✅ FDS modifiée avec succès", "success")
        return redirect(url_for('liste_fds'))

    return render_template('modifier_fds.html', fds=fds)

@app.route('/fds/<int:fds_id>/supprimer', methods=['POST'])
@login_required
def supprimer_fds(fds_id):
    fds = FicheDonneesSecurite.query.get_or_404(fds_id)

    if fds.user_id != current_user.id and current_user.role != 'admin':
        abort(403)

    try:
        # Supprimer le fichier PDF du dossier
        if os.path.exists(fds.fichier_pdf):
            os.remove(fds.fichier_pdf)
    except:
        pass  # en cas d'erreur, on ignore

    db.session.delete(fds)
    db.session.commit()
    flash("🗑️ FDS supprimée avec succès", "warning")
    return redirect(url_for('liste_fds'))

@app.route('/fds/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_fds():
    if request.method == 'POST':
        nom_produit = request.form['nom_produit']
        fournisseur = request.form['fournisseur']
        date_fds = request.form['date_fds']
        numero_version = request.form['numero_version']
        dangereux = 'dangereux' in request.form

        fichier = request.files['fichier_pdf']
        if fichier and allowed_file(fichier.filename):
            filename = secure_filename(fichier.filename)
            chemin = os.path.join('static/uploads/fds', filename)
            fichier.save(chemin)

            fds = FicheDonneesSecurite(
                nom_produit=nom_produit,
                fournisseur=fournisseur,
                date_fds=datetime.strptime(date_fds, '%Y-%m-%d'),
                numero_version=numero_version,
                fichier_pdf=chemin,
                dangereux=dangereux,
                user_id=current_user.id
            )
            db.session.add(fds)
            db.session.commit()
            flash("✅ FDS ajoutée avec succès", "success")
            return redirect(url_for('ajouter_fds'))
        else:
            flash("❌ Fichier invalide. Seuls les PDF sont autorisés.", "danger")

    return render_template('ajouter_fds.html')

@app.route('/accidents')
@login_required
def liste_accidents():
    if current_user.role == 'admin':
        accidents = AccidentTravail.query.order_by(AccidentTravail.date_accident.desc()).all()
    else:
        accidents = AccidentTravail.query.filter_by(user_id=current_user.id).order_by(AccidentTravail.date_accident.desc()).all()
    return render_template('liste_accidents.html', accidents=accidents)

@app.route('/accident/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_accident():
    postes = Poste.query.filter_by(user_id=current_user.id).all()
    taches = Tache.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        accident = AccidentTravail(
            user_id=current_user.id,
            poste_id=request.form['poste_id'],
            tache_id=request.form.get('tache_id') or None,
            date_accident=datetime.strptime(request.form['date_accident'], '%Y-%m-%d'),
            lieu=request.form['lieu'],
            description=request.form['description'],
            circonstances=request.form.get('circonstances', ''),
            consequences=request.form.get('consequences', ''),
            actions_correctives=request.form.get('actions_correctives', '')
        )
        db.session.add(accident)
        db.session.commit()
        flash("📌 Accident de travail enregistré.", "success")
        return redirect(url_for('liste_accidents'))

    return render_template('form_accident.html', postes=postes, taches=taches)

@app.route('/accident/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_accident(id):
    accident = AccidentTravail.query.get_or_404(id)
    if accident.user_id != current_user.id and current_user.role != 'admin':
        abort(403)

    postes = Poste.query.filter_by(user_id=current_user.id).all()
    taches = Tache.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        accident.poste_id = request.form['poste_id']
        accident.tache_id = request.form.get('tache_id') or None
        accident.date_accident = datetime.strptime(request.form['date_accident'], '%Y-%m-%d')
        accident.lieu = request.form['lieu']
        accident.description = request.form['description']
        accident.circonstances = request.form.get('circonstances', '')
        accident.consequences = request.form.get('consequences', '')
        accident.actions_correctives = request.form.get('actions_correctives', '')
        db.session.commit()
        flash("✏️ Accident modifié avec succès.", "success")
        return redirect(url_for('liste_accidents'))

    return render_template('form_accident.html', accident=accident, postes=postes, taches=taches)

@app.route('/accident/<int:id>/archiver', methods=['POST'])
@login_required
def archiver_accident(id):
    accident = AccidentTravail.query.get_or_404(id)
    if accident.user_id != current_user.id and current_user.role != 'admin':
        abort(403)

    accident.archivee = True
    db.session.commit()
    flash("📦 Accident archivé.", "info")
    return redirect(url_for('liste_accidents'))

@app.route('/accident/<int:id>/arbre', methods=['GET', 'POST'])
@login_required
def editer_arbre_causes(id):
    accident = AccidentTravail.query.get_or_404(id)

    if request.method == 'POST':
        arbre_json = request.form.get('arbre_json')
        if arbre_json:
            accident.arbre_json = arbre_json
            db.session.commit()
            flash("✅ Arbre des causes enregistré avec succès.", "success")
            return redirect(url_for('liste_accidents'))

    return render_template('editer_arbre_causes.html', accident=accident)

@app.route('/accident/<int:id>/supprimer', methods=['POST'])
@login_required
def supprimer_accident(id):
    accident = AccidentTravail.query.get_or_404(id)
    db.session.delete(accident)
    db.session.commit()
    flash("🗑️ Accident supprimé avec succès.", "success")
    return redirect(url_for('liste_accidents'))

registre_bp = Blueprint('registre', __name__)

@app.route('/testmail')
def testmail():
    try:
        msg = Message("Test de mail", recipients=["lefebvre.flavien2014@gmail.com"])
        msg.body = "Ceci est un e-mail de test envoyé depuis Flask-Mail."
        mail.send(msg)
        return "E-mail envoyé avec succès !"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Erreur lors de l'envoi : {e}"

if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
