from app import app, db
from models import Section

with app.app_context():
    # Définir les sections à ajouter
    sections = [
        {"title": "Introduction à la sécurité", "content": "Contenu sur la sécurité", "theme": "securite"},
        {"title": "Politique qualité", "content": "Contenu sur la qualité", "theme": "qualite"},
        {"title": "Environnement durable", "content": "Contenu sur l'environnement", "theme": "environnement"},
    ]

    for s in sections:
        exists = Section.query.filter_by(title=s["title"], theme=s["theme"]).first()
        if not exists:
            new_section = Section(title=s["title"], content=s["content"], theme=s["theme"])
            db.session.add(new_section)
            print(f"✅ Section ajoutée : {s['title']} ({s['theme']})")
        else:
            print(f"ℹ️ Section déjà existante : {s['title']} ({s['theme']})")

    db.session.commit()
    print("✔️ Terminé.")
