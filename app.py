from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import os
from models import db, User, Section, Message as MessageModel
from flask_mail import Message as MailMessage
from flask_mail import Mail, Message  # Mets ceci au-dessus de mail = Mail(app)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'cle_secrete'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'videos')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Email config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'lefebvre.flavien2018@gmail.com'
app.config['MAIL_PASSWORD'] = 'dcstvxgftayrxohe'
app.config['MAIL_DEFAULT_SENDER'] = 'lefebvre.flavien2018@gmail.com'
mail = Mail(app)

# Sécurité des tokens
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Initialise l'instance db
db.init_app(app)

from flask_migrate import Migrate
migrate = Migrate(app, db)

# Authentification
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = None
login_manager.login_message_category = "info"

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
        return redirect(url_for('dashboard'))  # Redirige vers le tableau de bord classique
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
    # Si l'utilisateur est déjà connecté, on le redirige
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard' if current_user.role == 'admin' else 'dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            if not user.confirmed:
                flash("Veuillez confirmer votre adresse e-mail avant de vous connecter.", "warning")
                return redirect(url_for('login'))

            login_user(user)
            return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'dashboard'))

        flash('Identifiants incorrects', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']

        # Vérifie si l’email est déjà utilisé
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Cet email est déjà utilisé.")
            return redirect(url_for('register'))

        # Vérifie si le nom d’utilisateur est déjà utilisé
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash("Ce nom d'utilisateur est déjà utilisé.")
            return redirect(url_for('register'))

        # Hachage du mot de passe
        hashed_pw = generate_password_hash(request.form['password'])

        # Créer l'utilisateur non confirmé
        new_user = User(username=username, email=email, password=hashed_pw, confirmed=False)
        db.session.add(new_user)
        db.session.commit()

        # Envoie de l'e-mail de confirmation
        token = s.dumps(email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)

        msg = MailMessage('Confirmez votre adresse e-mail', recipients=[email])
        msg.body = f"Cliquez ici pour confirmer votre compte : {confirm_url}"
        mail.send(msg)

        flash("Un e-mail de confirmation vous a été envoyé.")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    themes = ['securite', 'qualite', 'environnement']
    theme_content = {}

    for theme in themes:
        if getattr(current_user, theme):
            sections = Section.query.filter_by(theme=theme).all()
            theme_content[theme] = sections

    return render_template("dashboard.html", theme_content=theme_content)

from models import Message as MessageModel  # Assurez-vous de l'importer ainsi si conflit

@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    if request.method == 'POST':
        sujet = request.form.get('sujet')
        contenu = request.form.get('message')  # Renommé pour éviter le conflit

        # Enregistrement dans la base de données
        sujet = request.form['sujet']
        contenu = request.form['message']
        nouveau_message = Message(subject=sujet, content=contenu, user_id=current_user.id)
        db.session.add(nouveau_message)
        db.session.commit()

        flash("Message enregistré avec succès !", "success")
        return redirect(url_for('dashboard'))

    return render_template("contact.html")


@app.route('/contenu')
@login_required
def contenu():
    return render_template('contenu.html')

@app.route('/admin/upload', methods=['GET', 'POST'])
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
        email = s.loads(token, salt='email-confirm', max_age=3600)  # 1h de validité
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

        # Génération du token et envoi de l'e-mail
        token = s.dumps(email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        msg = MailMessage('Confirmez votre adresse e-mail', recipients=[email])
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

from flask import jsonify

from flask import jsonify, request

@app.route('/admin/users/search')
@login_required
def search_users():
    if current_user.role != 'admin':
        return jsonify([]), 403

    keyword = request.args.get('keyword', '').lower()
    role = request.args.get('role', '')
    confirmed = request.args.get('confirmed', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    query = User.query

    if keyword:
        query = query.filter((User.username.ilike(f"%{keyword}%")) | (User.email.ilike(f"%{keyword}%")))

    if role:
        query = query.filter_by(role=role)

    if confirmed:
        if confirmed == "oui":
            query = query.filter_by(confirmed=True)
        elif confirmed == "non":
            query = query.filter_by(confirmed=False)

    total = query.count()
    users = query.order_by(User.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "confirmed": "Oui" if u.confirmed else "Non",
                "securite": u.securite,
                "qualite": u.qualite,
                "environnement": u.environnement
            } for u in users.items
        ]
    })

@app.route('/admin/edit_sections', methods=['GET'])
@login_required
def edit_sections():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    data = {}
    for theme in ['securite', 'qualite', 'environnement']:
        content = Section.query.filter_by(theme=theme).all()
        if not content:
            content = Section(
                theme=theme,
                title="Titre par défaut",
                content="Contenu par défaut"
            )
            db.session.add(content)
            db.session.commit()

        data[theme] = content

    return render_template("admin_edit_sections.html", data=data)


    return render_template("admin_edit_sections.html", data=data)

from collections import defaultdict

import os
from flask import request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi'}
ALLOWED_FILE_EXTENSIONS = {'pdf', 'docx', 'txt'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/admin/edit_section/<theme>/<int:section_id>', methods=['GET', 'POST'])
@login_required
def edit_section_form(theme, section_id):
    section = Section.query.get_or_404(section_id)
    if request.method == 'POST':
        section.title = request.form['title']
        section.content = request.form['content']
        
        # Gestion vidéo
        video = request.files.get('video')
        if video and video.filename:
            filename = secure_filename(video.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video.save(video_path)
            section.video_url = f'/static/videos/{filename}'
        
        # Gestion fichier
        file = request.files.get('file')
        if file and file.filename:
            file_filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_filename)
            file.save(file_path)
            section.file_path = f'/static/files/{file_filename}'

        db.session.commit()
        flash("Section mise à jour avec succès !", "success")
        return redirect(url_for('edit_sections', theme=theme))

    return render_template('edit_section_form.html', section=section, theme=theme)

@app.route('/admin/update_section/<theme>', methods=['POST'])
@login_required
def update_section_post(theme):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    content = Section.query.filter_by(theme=theme).all()
    is_new = False
    if not content:
        content = Section(theme=theme)
        is_new = True

    content.title = request.form.get('title')
    content.content = request.form.get('content')

    # Sauvegarde de la vidéo
    video_file = request.files.get('video')
    if video_file and video_file.filename:
        filename = secure_filename(video_file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        video_file.save(video_path)
        content.video_url = filename  # ✅ Corrigé

    # Sauvegarde du fichier téléchargeable
    doc_file = request.files.get('file')
    if doc_file and doc_file.filename:
        filename = secure_filename(doc_file.filename)
        doc_path = os.path.join('static/documents', filename)
        os.makedirs('static/documents', exist_ok=True)
        doc_file.save(doc_path)
        content.file_path = filename  # ✅ Corrigé

    if is_new:
        db.session.add(content)

    db.session.commit()

    flash(f"Contenu mis à jour pour le thème : {theme.capitalize()}", "success")
    return redirect(url_for('edit_sections'))

@app.route('/admin/delete_section/<theme>/<int:section_id>', methods=['POST'])
@login_required
def delete_section(theme, section_id):
    if current_user.role != 'admin':
        flash("Accès refusé.", "danger")
        return redirect(url_for('dashboard'))

    section = Section.query.get_or_404(section_id)
    db.session.delete(section)
    db.session.commit()

    flash(f"Section supprimée pour le thème : {theme.capitalize()}", "warning")
    return redirect(url_for('edit_sections'))

@app.route('/admin/add_section/<theme>', methods=['GET', 'POST'])
@login_required
def add_section_form(theme):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        video_url = request.form.get('video_url')
        file = request.files.get('file')
        file_path = None

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        new_section = Section(title=title, content=content, video_url=video_url,
                              file_path=file_path, theme=theme)
        db.session.add(new_section)
        db.session.commit()
        flash('Section ajoutée avec succès', 'success')
        return redirect(url_for('edit_sections', theme=theme))  # Assurez-vous que cette route existe

    return render_template('add_section.html', theme=theme)  # Ne pas passer `section`

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
    setattr(user, theme, not current_value)  # Toggle le booléen
    db.session.commit()

    return jsonify(success=True)

from models import Message  # correspond bien au nom de ta classe

@app.route('/admin/messages')
@login_required
def admin_messages():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    messages = Message.query.order_by(Message.timestamp.desc()).all()
    return render_template('admin_messages.html', messages=messages)

@app.route('/admin/repondre/<int:message_id>', methods=['GET', 'POST'])
@login_required
def repondre_message(message_id):
    if current_user.role != 'admin':
        flash("Accès refusé.", "danger")
        return redirect(url_for('dashboard'))

    msg_recu = Message.query.get_or_404(message_id)
    user_destinataire = msg_recu.user

    if request.method == 'POST':
        reponse = request.form.get('reponse')
        if reponse:
            try:
                msg = Message(
                    subject=f"Réponse à votre message : {msg_recu.subject}",
                    recipients=[user_destinataire.email],
                    body=reponse
                )
                mail.send(msg)
                flash("Réponse envoyée avec succès par e-mail.", "success")
            except Exception as e:
                flash(f"Erreur lors de l'envoi : {e}", "danger")
            return redirect(url_for('admin_messages'))

    return render_template('repondre_message.html', msg=msg_recu)

from flask_mail import Message as MailMessage  # Assure-toi que c’est bien importé en haut

@app.route('/testmail')
def testmail():
    try:
        msg = MailMessage("Test de mail", recipients=["lefebvre.flavien2014@gmail.com"])
        msg.body = "Ceci est un e-mail de test envoyé depuis Flask-Mail."
        mail.send(msg)
        return "E-mail envoyé avec succès !"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Erreur lors de l'envoi : {e}"


from flask.cli import with_appcontext
import click

@click.command(name='create_tables')
@with_appcontext
def create_tables():
    db.create_all()

app.cli.add_command(create_tables)

# ← Tout ce qui précède doit être au-dessus de ceci

if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)