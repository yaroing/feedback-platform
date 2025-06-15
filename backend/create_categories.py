import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_project.settings')
django.setup()

from feedback_api.models import Category

# Liste des catégories à créer avec leurs descriptions
CATEGORIES = [
    {
        "name": "Commentaire",
        "description": "Retours descriptifs ou observations sur les activités ou services"
    },
    {
        "name": "Suggestion",
        "description": "Propositions d’amélioration ou recommandations opérationnelles"
    },
    {
        "name": "Plainte",
        "description": "Griefs formels ou insatisfactions nécessitant un suivi"
    },
    {
        "name": "Question",
        "description": "Demandes d’informations ou demandes de clarification"
    },
    {
        "name": "Éloge",
        "description": "Retours positifs et remerciements pour les services rendus"
    },
    {
        "name": "Autre",
        "description": "Tout autre type de feedback ne correspondant pas aux catégories ci-dessus"
    },
    {
        "name": "Sécurité alimentaire",
        "description": "Feedbacks relatifs à l’assistance et à la distribution alimentaire"
    },
    {
        "name": "Eau, assainissement et hygiène",
        "description": "Retours concernant l’accès à l’eau potable, latrines et hygiène"
    },
    {
        "name": "Santé",
        "description": "Feedbacks sur les services médicaux et soins de santé"
    },
    {
        "name": "Éducation et psychosocial",
        "description": "Retours portant sur l’éducation, la protection de l’enfance et le soutien psychosocial"
    },
    {
        "name": "Hébergement",
        "description": "Feedbacks liés aux abris temporaires ou permanents"
    },
    {
        "name": "Moyens de subsistance",
        "description": "Retours sur les activités génératrices de revenus et le soutien monétaire"
    },
    {
        "name": "Protection",
        "description": "Feedbacks concernant la sécurité, la protection contre l’exploitation et les abus"
    },
    {
        "name": "Qualité des services",
        "description": "Observations sur l’accessibilité, la couverture et l’efficacité des services"
    },
    {
        "name": "Comportement du personnel",
        "description": "Retours sur l’attitude, l’impartialité et le respect du personnel"
    },
    {
        "name": "Information et participation",
        "description": "Feedbacks sur la clarté des informations et l’implication des communautés"
    },
    {
        "name": "PSEA",
        "description": "Signalements relatifs à la prévention de l’exploitation sexuelle et des abus"
    }
]


# Fonction pour créer les catégories
def create_categories():
    created_count = 0
    already_exists_count = 0

    for category_data in CATEGORIES:
        category, created = Category.objects.get_or_create(
            name=category_data["name"],
            defaults={"description": category_data["description"]}
        )

        if created:
            print(f"✅ Catégorie créée : {category.name}")
            created_count += 1
        else:
            print(f"ℹ️ La catégorie '{category.name}' existe déjà")
            already_exists_count += 1

    print(f"\nRésumé : {created_count} catégories créées, {already_exists_count} catégories existantes")

if __name__ == "__main__":
    print("Création des catégories pour la plateforme de feedback...")
    create_categories()
