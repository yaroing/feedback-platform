from django.core.management.base import BaseCommand
from feedback_api.models import Category
from django.db import transaction

class Command(BaseCommand):
    help = 'Creates categories for humanitarian emergency feedback'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        # Define humanitarian emergency categories
        categories = [
            # Urgent Needs
            {
                'name': 'Eau & Assainissement',
                'description': 'Accès à l\'eau potable, installations sanitaires, hygiène'
            },
            {
                'name': 'Sécurité Alimentaire',
                'description': 'Distribution de nourriture, qualité des aliments, besoins nutritionnels'
            },
            {
                'name': 'Assistance Médicale',
                'description': 'Soins médicaux, médicaments, services de santé'
            },
            {
                'name': 'Abri & Logement',
                'description': 'Abris d\'urgence, matériaux de construction, conditions de logement'
            },
            
            # Protection Issues
            {
                'name': 'Sûreté & Sécurité',
                'description': 'Menaces, violence, protection des civils'
            },
            {
                'name': 'Protection de l\'Enfance',
                'description': 'Sécurité des enfants, éducation, besoins spécifiques des enfants'
            },
            {
                'name': 'Violence Basée sur le Genre',
                'description': 'Signalements, prévention, assistance aux survivants'
            },
            {
                'name': 'Assistance Juridique',
                'description': 'Documentation, droits légaux, résolution de conflits'
            },
            
            # Aid Distribution
            {
                'name': 'Qualité de l\'Aide',
                'description': 'Pertinence et qualité des articles d\'assistance fournis'
            },
            {
                'name': 'Équité de Distribution',
                'description': 'Processus de distribution, inclusion, transparence'
            },
            {
                'name': 'Barrières d\'Accès',
                'description': 'Obstacles à l\'accès aux services et à l\'aide'
            },
            {
                'name': 'Articles Manquants',
                'description': 'Signalements d\'articles promis mais non reçus'
            },
            
            # Information Needs
            {
                'name': 'Disponibilité des Services',
                'description': 'Information sur les services disponibles et comment y accéder'
            },
            {
                'name': 'Procédures d\'Enregistrement',
                'description': 'Clarification sur les processus d\'enregistrement et documentation'
            },
            {
                'name': 'Droits & Prestations',
                'description': 'Information sur les droits et les prestations disponibles'
            },
            {
                'name': 'Mises à Jour Communautaires',
                'description': 'Information sur la situation générale et les développements'
            },
            
            # Infrastructure
            {
                'name': 'État des Routes',
                'description': 'Accessibilité, dommages, besoins de réparation'
            },
            {
                'name': 'Électricité & Énergie',
                'description': 'Accès à l\'électricité, sources d\'énergie alternatives'
            },
            {
                'name': 'Réseaux de Communication',
                'description': 'Téléphonie mobile, internet, radio'
            },
            {
                'name': 'Installations Publiques',
                'description': 'Écoles, centres de santé, marchés, espaces communautaires'
            },
            
            # Program Feedback
            {
                'name': 'Conduite du Personnel',
                'description': 'Comportement du personnel humanitaire, professionnalisme'
            },
            {
                'name': 'Qualité des Services',
                'description': 'Évaluation de la qualité des services fournis'
            },
            {
                'name': 'Corruption/Détournement',
                'description': 'Signalements de corruption ou de détournement d\'aide'
            },
            {
                'name': 'Suggestions d\'Amélioration',
                'description': 'Idées pour améliorer les programmes et services'
            },
            
            # Community Relations
            {
                'name': 'Problèmes avec Communauté Hôte',
                'description': 'Tensions ou problèmes avec les communautés locales'
            },
            {
                'name': 'Cohésion Sociale',
                'description': 'Relations entre différents groupes, intégration'
            },
            {
                'name': 'Préoccupations Culturelles',
                'description': 'Questions liées aux pratiques culturelles et religieuses'
            },
            {
                'name': 'Résolution de Conflits',
                'description': 'Médiation, résolution pacifique des différends'
            },
            
            # Special Needs
            {
                'name': 'Soutien aux Personnes Handicapées',
                'description': 'Services adaptés, accessibilité, inclusion'
            },
            {
                'name': 'Soins aux Personnes Âgées',
                'description': 'Besoins spécifiques des personnes âgées'
            },
            {
                'name': 'Santé Maternelle & Infantile',
                'description': 'Soins prénatals, postnatals, pédiatriques'
            },
            {
                'name': 'Santé Mentale & Soutien Psychosocial',
                'description': 'Services de santé mentale, soutien psychologique, traumatisme'
            },
        ]
        
        # Count existing and new categories
        existing_count = 0
        created_count = 0
        
        # Create categories
        for category_data in categories:
            category, created = Category.objects.get_or_create(
                name=category_data['name'],
                defaults={'description': category_data['description']}
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
            else:
                existing_count += 1
                self.stdout.write(self.style.WARNING(f'Category already exists: {category.name}'))
        
        # Summary message
        self.stdout.write(self.style.SUCCESS(
            f'Categories created successfully! Created: {created_count}, Already existed: {existing_count}'
        ))
