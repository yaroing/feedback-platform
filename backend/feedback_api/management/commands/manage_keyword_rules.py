from django.core.management.base import BaseCommand
from django.utils import timezone
import json
import logging
from feedback_api.models import Category, KeywordRule, Feedback

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Gère les règles de mots-clés pour la classification des feedbacks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['create', 'update', 'list', 'extract'],
            required=True,
            help='Action à effectuer sur les règles de mots-clés'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Nom de la catégorie pour laquelle créer/mettre à jour une règle'
        )
        parser.add_argument(
            '--keywords',
            type=str,
            help='Liste de mots-clés séparés par des virgules'
        )
        parser.add_argument(
            '--priority',
            type=str,
            choices=['low', 'medium', 'high', 'urgent'],
            help='Priorité à associer à cette règle'
        )
        parser.add_argument(
            '--confidence',
            type=float,
            default=0.0,
            help='Boost de confiance pour cette règle (0.0-1.0)'
        )
        parser.add_argument(
            '--min-frequency',
            type=int,
            default=3,
            help='Fréquence minimale pour extraire un mot-clé (mode extract)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Fichier de sortie pour l\'extraction de mots-clés (mode extract)'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'create':
            self._create_rule(options)
        elif action == 'update':
            self._update_rule(options)
        elif action == 'list':
            self._list_rules()
        elif action == 'extract':
            self._extract_keywords(options)
    
    def _create_rule(self, options):
        """Crée une nouvelle règle de mots-clés"""
        category_name = options['category']
        keywords_str = options['keywords']
        priority = options['priority']
        confidence = options['confidence']
        
        if not category_name or not keywords_str:
            self.stdout.write(self.style.ERROR('Le nom de la catégorie et les mots-clés sont requis'))
            return
        
        try:
            category = Category.objects.get(name=category_name)
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Catégorie "{category_name}" non trouvée'))
            return
        
        keywords = [k.strip().lower() for k in keywords_str.split(',')]
        
        rule = KeywordRule.objects.create(
            name=f'Règle pour {category_name}',
            category=category,
            keywords=keywords,
            priority=priority,
            confidence_boost=confidence
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'Règle créée: {rule.name} avec {len(keywords)} mots-clés'
        ))
    
    def _update_rule(self, options):
        """Met à jour une règle de mots-clés existante"""
        category_name = options['category']
        keywords_str = options['keywords']
        priority = options['priority']
        confidence = options['confidence']
        
        if not category_name:
            self.stdout.write(self.style.ERROR('Le nom de la catégorie est requis'))
            return
        
        try:
            category = Category.objects.get(name=category_name)
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Catégorie "{category_name}" non trouvée'))
            return
        
        try:
            rule = KeywordRule.objects.get(category=category)
        except KeywordRule.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Aucune règle trouvée pour la catégorie "{category_name}"'))
            return
        
        if keywords_str:
            keywords = [k.strip().lower() for k in keywords_str.split(',')]
            rule.keywords = keywords
        
        if priority:
            rule.priority = priority
        
        if confidence is not None:
            rule.confidence_boost = confidence
        
        rule.save()
        
        self.stdout.write(self.style.SUCCESS(
            f'Règle mise à jour: {rule.name} avec {len(rule.keywords)} mots-clés'
        ))
    
    def _list_rules(self):
        """Liste toutes les règles de mots-clés"""
        rules = KeywordRule.objects.all().select_related('category')
        
        if not rules.exists():
            self.stdout.write('Aucune règle de mots-clés trouvée')
            return
        
        self.stdout.write(self.style.SUCCESS(f'Règles de mots-clés ({rules.count()}):'))
        
        for rule in rules:
            self.stdout.write(f'\n{rule.name} (Catégorie: {rule.category.name})')
            self.stdout.write(f'  Priorité: {rule.priority or "Non définie"}')
            self.stdout.write(f'  Boost de confiance: {rule.confidence_boost}')
            self.stdout.write(f'  Mots-clés ({len(rule.keywords)}): {", ".join(rule.keywords)}')
    
    def _extract_keywords(self, options):
        """Extrait des mots-clés potentiels à partir des feedbacks existants"""
        from collections import Counter
        import re
        import nltk
        from nltk.corpus import stopwords
        
        # Télécharger les ressources NLTK si nécessaires
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        
        min_frequency = options['min_frequency']
        output_file = options['output']
        
        # Obtenir les stopwords français
        stop_words = set(stopwords.words('french'))
        
        # Ajouter des stopwords supplémentaires spécifiques au domaine
        additional_stopwords = {
            'bonjour', 'merci', 'svp', 'besoin', 'problème', 'urgent', 'aide',
            'demande', 'question', 'information', 'jour', 'semaine', 'mois'
        }
        stop_words.update(additional_stopwords)
        
        # Récupérer tous les feedbacks avec catégorie
        feedbacks = Feedback.objects.filter(category__isnull=False)
        
        if not feedbacks.exists():
            self.stdout.write(self.style.ERROR('Aucun feedback avec catégorie trouvé'))
            return
        
        self.stdout.write(f'Analyse de {feedbacks.count()} feedbacks...')
        
        # Regrouper les feedbacks par catégorie
        category_feedbacks = {}
        for feedback in feedbacks:
            category_name = feedback.category.name
            if category_name not in category_feedbacks:
                category_feedbacks[category_name] = []
            
            category_feedbacks[category_name].append(feedback.content.lower())
        
        # Extraire les mots-clés par catégorie
        keyword_suggestions = {}
        
        for category, texts in category_feedbacks.items():
            self.stdout.write(f'Analyse de la catégorie "{category}" ({len(texts)} feedbacks)...')
            
            # Combiner tous les textes
            combined_text = ' '.join(texts)
            
            # Nettoyer le texte
            combined_text = re.sub(r'[^\w\s]', ' ', combined_text)
            
            # Diviser en mots
            words = combined_text.split()
            
            # Filtrer les stopwords et les mots courts
            filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
            
            # Compter les occurrences
            word_counts = Counter(filtered_words)
            
            # Filtrer par fréquence minimale
            frequent_words = {word: count for word, count in word_counts.items() if count >= min_frequency}
            
            # Trier par fréquence
            sorted_words = sorted(frequent_words.items(), key=lambda x: x[1], reverse=True)
            
            # Stocker les suggestions
            keyword_suggestions[category] = sorted_words
        
        # Afficher les résultats
        self.stdout.write(self.style.SUCCESS('\nSuggestions de mots-clés par catégorie:'))
        
        for category, words in keyword_suggestions.items():
            self.stdout.write(f'\n{category}:')
            for word, count in words[:20]:  # Limiter à 20 mots-clés par catégorie
                self.stdout.write(f'  {word}: {count} occurrences')
        
        # Sauvegarder dans un fichier si demandé
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {cat: dict(words) for cat, words in keyword_suggestions.items()},
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            self.stdout.write(self.style.SUCCESS(f'\nSuggestions sauvegardées dans {output_file}'))
