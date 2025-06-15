import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_project.settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.db import IntegrityError

# Créer un superutilisateur
try:
    superuser = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpassword'
    )
    print(f"Superutilisateur '{superuser.username}' créé avec succès!")
except IntegrityError:
    print("Le superutilisateur existe déjà.")

# Créer un groupe de modérateurs
try:
    moderators_group, created = Group.objects.get_or_create(name='Moderators')
    if created:
        print("Groupe 'Moderators' créé avec succès!")
    else:
        print("Le groupe 'Moderators' existe déjà.")
    
    # Ajouter le superutilisateur au groupe des modérateurs
    superuser = User.objects.get(username='admin')
    moderators_group.user_set.add(superuser)
    print(f"Utilisateur '{superuser.username}' ajouté au groupe 'Moderators'!")
except Exception as e:
    print(f"Erreur lors de la création du groupe: {e}")
