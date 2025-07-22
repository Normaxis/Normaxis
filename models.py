from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date
from sqlalchemy.dialects.sqlite import JSON

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), default='user')
    confirmed = db.Column(db.Boolean, default=False)
    entreprise = db.Column(db.String(100))
    adresse = db.Column(db.String(200))
    logo = db.Column(db.String(200))  # nom du fichier dans /static/uploads
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    fonction = db.Column(db.String(100))
    telephone = db.Column(db.String(20))    

    # Relations
    taches = db.relationship('Tache', backref='user', lazy='dynamic')
    risques = db.relationship('Risque', backref='user', lazy=True)
    sections = db.relationship('Section', backref='user', lazy=True)
    abonnements = db.relationship('Abonnement', back_populates='user', lazy='dynamic')
    messages = db.relationship('Message', backref='user', lazy='dynamic')

    def has_active_abonnement(self, theme):
        today = date.today()
        return self.abonnements.filter(
            Abonnement.theme == theme,
            Abonnement.date_debut <= today,
            Abonnement.date_fin >= today
        ).count() > 0


class Section(db.Model):
    __tablename__ = 'section'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(300), nullable=True)
    file_path = db.Column(db.String(200), nullable=True)
    theme = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Abonnement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    theme = db.Column(db.String(20), nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)

    user = db.relationship('User', back_populates='abonnements')

    def to_dict(self):
        return {
            'id': self.id,
            'theme': self.theme,
            'date_debut': self.date_debut.isoformat(),
            'date_fin': self.date_fin.isoformat()
        }


class Poste(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    taches = db.relationship('Tache', backref='poste', cascade="all, delete", lazy='dynamic')
    photo = db.Column(db.String(200))  # Nom du fichier image du poste
    photo_poste = db.Column(db.String(200))  # nom du fichier image dans /static/uploads
    risques = db.relationship('Risque', backref='poste', lazy=True)
    user = db.relationship('User', foreign_keys=[user_id], backref='postes_crees')


class Tache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    poste_id = db.Column(db.Integer, db.ForeignKey('poste.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    risques = db.relationship('Risque', backref='tache', cascade="all, delete", lazy=True)


class Risque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    frequence = db.Column(db.Integer, nullable=False)
    gravite = db.Column(db.Integer, nullable=False)
    maitrise = db.Column(db.Float, nullable=False)
    score = db.Column(db.Float, nullable=False)
    tache_id = db.Column(db.Integer, db.ForeignKey('tache.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    poste_id = db.Column(db.Integer, db.ForeignKey('poste.id'), nullable=False)  # ✅ AJOUT CLÉ ÉTRANGÈRE
    dommages = db.Column(db.Text)
    mesures_prevention = db.Column(db.Text)
    famille_danger = db.Column(db.String(255), nullable=False, default="Non précisé")
    etat_action = db.Column(db.Boolean, default=False)
    cout_action = db.Column(db.Float, nullable=True)
    epis = db.Column(JSON)

    # Champs pour PAPRIPACT
    actions_a_mener = db.Column(db.Text)
    responsable_action = db.Column(db.String(120))
    delai_mise_en_oeuvre = db.Column(db.String(100))
    date_realisation = db.Column(db.Date)

association_fsp_fds = db.Table('association_fsp_fds',
    db.Column('fsp_id', db.Integer, db.ForeignKey('fiche_securite.id'), primary_key=True),
    db.Column('fds_id', db.Integer, db.ForeignKey('fiche_donnees_securite.id'), primary_key=True)
)
class FicheSecurite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(260), nullable=False)
    contenu = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    photo_poste = db.Column(db.String(255))

    user = db.relationship('User', backref='fiches_securite')

    # 🔗 Relation vers les FDS
    fds_associees = db.relationship('FicheDonneesSecurite',
        secondary=association_fsp_fds,
        backref='fiches_securite_poste')

class DUERPArchive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_archivage = db.Column(db.DateTime, default=datetime.utcnow)
    contenu_html = db.Column(db.Text, nullable=False)
    commentaire = db.Column(db.String(255), default='Archivage manuel')

    user = db.relationship('User', backref='archives_duerp')

class FicheDonneesSecurite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_produit = db.Column(db.String(255), nullable=False)
    fournisseur = db.Column(db.String(255))
    date_fds = db.Column(db.Date)
    numero_version = db.Column(db.String(50))
    fichier_pdf = db.Column(db.String(255), nullable=False)
    dangereux = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # uploader

    user = db.relationship('User', backref='fds_uploads')

class AccidentTravail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    poste_id = db.Column(db.Integer, db.ForeignKey('poste.id'))
    tache_id = db.Column(db.Integer, db.ForeignKey('tache.id'), nullable=True)
    date_accident = db.Column(db.Date, nullable=False)
    lieu = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    circonstances = db.Column(db.Text)
    consequences = db.Column(db.Text)
    actions_correctives = db.Column(db.Text)
    archivee = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='accidents')
    poste = db.relationship('Poste')
    tache = db.relationship('Tache')
    arbre_json = db.Column(db.Text)  # pour stocker l’arbre des causes en JSON
