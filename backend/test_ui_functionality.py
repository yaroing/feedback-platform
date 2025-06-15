"""
Script de test pour vérifier les fonctionnalités principales de l'interface utilisateur
"""
import os
import sys
import django
import random
from datetime import datetime

# Configurer l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_project.settings')
django.setup()

# Importer les modèles après la configuration de Django
from django.contrib.auth.models import User
from feedback_api.models import Feedback, Category, Response

def create_test_feedback():
    """Crée un nouveau feedback de test"""
    print("\n=== Création d'un nouveau feedback de test ===")
    
    # Récupérer une catégorie aléatoire
    categories = list(Category.objects.all())
    category = random.choice(categories) if categories else None
    
    # Récupérer un modérateur
    moderator = User.objects.filter(groups__name='Moderators').first()
    
    # Créer le feedback
    feedback = Feedback.objects.create(
        content=f"Feedback de test créé le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        channel="web",
        status="new",
        priority="medium",
        category=category,
        contact_email="test@example.com",
        assigned_to=moderator
    )
    
    print(f"Feedback créé avec succès ! ID: {feedback.id}")
    print(f"Contenu: {feedback.content}")
    print(f"Catégorie: {category.name if category else 'Non classé'}")
    
    return feedback

def update_existing_feedback():
    """Met à jour un feedback existant"""
    print("\n=== Mise à jour d'un feedback existant ===")
    
    # Récupérer un feedback existant
    feedback = Feedback.objects.filter(status="new").first()
    
    if not feedback:
        print("Aucun feedback 'nouveau' trouvé. Création d'un nouveau feedback...")
        feedback = create_test_feedback()
    
    # Récupérer une catégorie différente
    current_category_id = feedback.category.id if feedback.category else None
    new_category = Category.objects.exclude(id=current_category_id).first()
    
    # Sauvegarder l'état actuel pour comparaison
    old_status = feedback.status
    old_priority = feedback.priority
    old_category = feedback.category
    
    # Mettre à jour le feedback
    feedback.status = "in_progress"
    feedback.priority = "high"
    feedback.category = new_category
    feedback.save()
    
    print(f"Feedback #{feedback.id} mis à jour avec succès !")
    print(f"Statut: {old_status} -> {feedback.status}")
    print(f"Priorité: {old_priority} -> {feedback.priority}")
    print(f"Catégorie: {old_category.name if old_category else 'Non classé'} -> {new_category.name if new_category else 'Non classé'}")
    
    return feedback

def add_response_to_feedback():
    """Ajoute une réponse à un feedback"""
    print("\n=== Ajout d'une réponse à un feedback ===")
    
    # Récupérer un feedback en cours
    feedback = Feedback.objects.filter(status="in_progress").first()
    
    if not feedback:
        print("Aucun feedback 'en cours' trouvé. Mise à jour d'un feedback...")
        feedback = update_existing_feedback()
    
    # Récupérer un modérateur
    moderator = User.objects.filter(groups__name='Moderators').first()
    
    # Créer une réponse
    response = Response.objects.create(
        feedback=feedback,
        content=f"Réponse de test créée le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        responder=moderator,
        sent=True
    )
    
    print(f"Réponse ajoutée au feedback #{feedback.id} avec succès !")
    print(f"Contenu de la réponse: {response.content}")
    print(f"Répondeur: {moderator.username}")
    
    return response

def main():
    """Fonction principale exécutant tous les tests"""
    print("=== DÉBUT DES TESTS DE FONCTIONNALITÉ ===")
    
    try:
        # Vérifier si les utilisateurs et catégories existent
        users_count = User.objects.count()
        categories_count = Category.objects.count()
        feedbacks_count = Feedback.objects.count()
        
        print(f"État initial de la base de données:")
        print(f"- {users_count} utilisateurs")
        print(f"- {categories_count} catégories")
        print(f"- {feedbacks_count} feedbacks")
        
        # Exécuter les tests
        new_feedback = create_test_feedback()
        updated_feedback = update_existing_feedback()
        new_response = add_response_to_feedback()
        
        print("\n=== TESTS TERMINÉS AVEC SUCCÈS ===")
        
    except Exception as e:
        print(f"\n!!! ERREUR PENDANT LES TESTS: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
