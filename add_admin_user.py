from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    email = "lefebvre.flavien2018@gmail.com"
    username = "AdminFlavien"
    password = "Stevecandice24"

    # Vérifie s'il existe déjà
    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        print("❌ L'utilisateur existe déjà.")
    else:
        new_user = User(
            email=email,
            username=username,
            password=generate_password_hash(password),
            role="admin",
            confirmed=True,
            securite=True,
            qualite=True,
            environnement=True
        )
        db.session.add(new_user)
        db.session.commit()
        print("✅ Utilisateur admin ajouté avec succès.")
