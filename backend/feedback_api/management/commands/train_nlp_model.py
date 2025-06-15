from django.core.management.base import BaseCommand
from django.utils import timezone
import logging
import os
import pickle
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from feedback_api.models import Feedback, Category, NLPModel, NLPTrainingData
from feedback_api.nlp import FeedbackClassifier

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Entraîne un modèle NLP pour la classification automatique des feedbacks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-samples',
            type=int,
            default=5,
            help='Nombre minimum d\'échantillons par catégorie pour l\'entraînement'
        )
        parser.add_argument(
            '--test-size',
            type=float,
            default=0.2,
            help='Proportion des données à utiliser pour les tests (0.0-1.0)'
        )
        parser.add_argument(
            '--use-existing',
            action='store_true',
            help='Utiliser les données d\'entraînement existantes en plus des feedbacks'
        )
        parser.add_argument(
            '--name',
            type=str,
            default=f'NLP Model {timezone.now().strftime("%Y-%m-%d")}',
            help='Nom du modèle à créer'
        )

    def handle(self, *args, **options):
        min_samples = options['min_samples']
        test_size = options['test_size']
        use_existing = options['use_existing']
        model_name = options['name']
        
        self.stdout.write(self.style.SUCCESS(f'Début de l\'entraînement du modèle NLP "{model_name}"'))
        
        # Collecter les données d'entraînement
        training_data = self._collect_training_data(min_samples, use_existing)
        
        if not training_data:
            self.stdout.write(self.style.ERROR('Pas assez de données pour entraîner le modèle'))
            return
        
        # Séparer les données en ensembles d'entraînement et de test
        texts = [item['content'] for item in training_data]
        labels = [item['category'] for item in training_data]
        
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=42, stratify=labels
        )
        
        self.stdout.write(f'Données d\'entraînement: {len(X_train)}, Données de test: {len(X_test)}')
        
        # Créer et entraîner le classifieur
        classifier = FeedbackClassifier()
        classifier.train_model(X_train, y_train)
        
        # Évaluer le modèle
        y_pred = [classifier.classify(text)[0] for text in X_test]
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        
        self.stdout.write(f'Précision: {accuracy:.4f}')
        self.stdout.write(f'Precision: {precision:.4f}')
        self.stdout.write(f'Recall: {recall:.4f}')
        self.stdout.write(f'F1 Score: {f1:.4f}')
        
        # Sauvegarder le modèle
        model_file = self._save_model(classifier, model_name, accuracy, precision, recall, f1, len(X_train))
        
        self.stdout.write(self.style.SUCCESS(f'Modèle entraîné et sauvegardé: {model_file}'))
    
    def _collect_training_data(self, min_samples, use_existing):
        """Collecte les données d'entraînement à partir des feedbacks et des données existantes"""
        training_data = []
        
        # Collecter les feedbacks avec une catégorie
        feedbacks = Feedback.objects.filter(category__isnull=False)
        self.stdout.write(f'Feedbacks avec catégorie trouvés: {feedbacks.count()}')
        
        # Regrouper par catégorie
        category_data = {}
        for feedback in feedbacks:
            category_name = feedback.category.name
            if category_name not in category_data:
                category_data[category_name] = []
            
            category_data[category_name].append({
                'content': feedback.content,
                'category': category_name
            })
        
        # Ajouter les données d'entraînement existantes si demandé
        if use_existing:
            training_entries = NLPTrainingData.objects.filter(is_validated=True)
            self.stdout.write(f'Données d\'entraînement validées trouvées: {training_entries.count()}')
            
            for entry in training_entries:
                category_name = entry.category.name
                if category_name not in category_data:
                    category_data[category_name] = []
                
                category_data[category_name].append({
                    'content': entry.content,
                    'category': category_name
                })
        
        # Filtrer les catégories avec trop peu d'échantillons
        valid_categories = {}
        for category, samples in category_data.items():
            if len(samples) >= min_samples:
                valid_categories[category] = len(samples)
                training_data.extend(samples)
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Catégorie "{category}" ignorée: seulement {len(samples)} échantillons (min: {min_samples})'
                    )
                )
        
        self.stdout.write(f'Catégories valides pour l\'entraînement: {len(valid_categories)}')
        for category, count in valid_categories.items():
            self.stdout.write(f'  - {category}: {count} échantillons')
        
        return training_data
    
    def _save_model(self, classifier, name, accuracy, precision, recall, f1, training_size):
        """Sauvegarde le modèle entraîné et crée une entrée dans la base de données"""
        from django.conf import settings
        import os
        
        # Créer le dossier des modèles s'il n'existe pas
        models_dir = os.path.join(settings.MEDIA_ROOT, 'nlp_models')
        os.makedirs(models_dir, exist_ok=True)
        
        # Générer un nom de fichier unique
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'nlp_model_{timestamp}.pkl'
        filepath = os.path.join(models_dir, filename)
        
        # Sauvegarder le modèle sur le disque
        with open(filepath, 'wb') as f:
            pickle.dump(classifier.model, f)
        
        # Désactiver tous les modèles existants
        NLPModel.objects.filter(is_active=True).update(is_active=False)
        
        # Créer une entrée dans la base de données
        model = NLPModel.objects.create(
            name=name,
            description=f'Modèle entraîné le {timezone.now().strftime("%d/%m/%Y à %H:%M")}',
            model_type='TF-IDF + MultinomialNB',
            version='1.0',
            file=f'nlp_models/{filename}',
            is_active=True,
            is_trained=True,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            training_data_size=training_size,
            last_trained=timezone.now()
        )
        
        return filepath
