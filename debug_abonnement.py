# debug_abonnement.py

from app import app, db
from models import User
from datetime import date

def debug_user_access(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ Utilisateur '{username}' non trouvé.")
            return

        print(f"🔎 Debug de l'utilisateur : {user.username}")
        print(f"Confirmé : {user.confirmed}")
        print("---")

        for theme in ['securite', 'qualite', 'environnement']:
            flag = getattr(user, theme)
            active = user.has_active_abonnement(theme)
            print(f"Titre : {theme.capitalize()}")
            print(f"  → Droit (flag): {flag}")
            print(f"  → Abonnement actif : {active}")
        
        print("---")
        print("📦 Abonnements enregistrés :")
        for ab in user.abonnements:
            print(f"  - {ab.theme} : {ab.date_debut} → {ab.date_fin}")

if __name__ == "__main__":
    username_input = input("Nom d'utilisateur à vérifier : ").strip()
    debug_user_access(username_input)
