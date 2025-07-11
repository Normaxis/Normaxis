from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    user = User.query.filter_by(email="lefebvre.flavien2018@gmail.com").first()
    if user:
        user.password = generate_password_hash("Stevecandice24")
        user.role = "admin"
        db.session.commit()
        print("✅ Mise à jour réussie : mot de passe & rôle admin.")
    else:
        print("❌ Utilisateur non trouvé.")
