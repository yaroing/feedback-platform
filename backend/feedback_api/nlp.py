import logging
import re
import pickle
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Définir les catégories et mots-clés pour la classification simple
CATEGORY_KEYWORDS = {
    'Eau & Assainissement': ['eau', 'hygiène', 'sanitaire', 'toilette', 'latrine', 'assainissement', 'lavage', 
             'savon', 'propre', 'sale', 'déchet', 'ordure', 'pollution', 'douche', 'robinet'],
    'Sécurité Alimentaire': ['nourriture', 'aliment', 'repas', 'faim', 'distribution', 'ration', 'manger', 
                  'cuisine', 'famine', 'nutrition', 'cantine', 'stock', 'approvisionnement'],
    'Assistance Médicale': ['santé', 'maladie', 'médical', 'médecin', 'hôpital', 'clinique', 'traitement', 
              'symptôme', 'médicament', 'douleur', 'consultation', 'patient', 'ambulance', 'urgence'],
    'Abri & Logement': ['abri', 'logement', 'tente', 'maison', 'hébergement', 'refuge', 'toit', 'habitation', 
            'camp', 'construction', 'bâtiment', 'réparation', 'matériel'],
    'Sûreté & Sécurité': ['sécurité', 'danger', 'menace', 'protection', 'violence', 'vol', 'agression', 
                'attaque', 'conflit', 'peur', 'police', 'armée', 'militaire', 'arme', 'crime'],
    'Protection de l\'Enfance': ['enfant', 'mineur', 'jeune', 'protection', 'abus', 'maltraitance', 'exploitation', 
                'vulnérable', 'famille', 'parent', 'orphelin', 'éducation', 'école'],
    'Violence Basée sur le Genre': ['genre', 'femme', 'violence', 'abus', 'sexuel', 'harcèlement', 'discrimination', 
                'égalité', 'protection', 'victime', 'traumatisme', 'soutien'],
    'Assistance Juridique': ['droit', 'juridique', 'légal', 'loi', 'avocat', 'conseil', 'document', 
                'papier', 'identité', 'statut', 'réfugié', 'asile', 'procédure'],
    'Qualité de l\'Aide': ['qualité', 'aide', 'assistance', 'service', 'satisfaction', 'insatisfaction', 
                'amélioration', 'problème', 'plainte', 'suggestion', 'feedback'],
    'Équité de Distribution': ['équité', 'distribution', 'partage', 'juste', 'injuste', 'favoritisme', 
                'discrimination', 'accès', 'égalité', 'inégalité', 'exclusion'],
    'Barrières d\'Accès': ['barrière', 'accès', 'obstacle', 'difficulté', 'empêchement', 'limitation', 
                'restriction', 'blocage', 'distance', 'transport'],
    'Articles Manquants': ['manque', 'manquant', 'insuffisant', 'rupture', 'stock', 'disponibilité', 
                'besoin', 'nécessité', 'essentiel', 'fourniture'],
}

# Chemin du modèle entraîné par défaut
DEFAULT_MODEL_PATH = os.path.join(settings.BASE_DIR, 'feedback_api', 'nlp_model.pkl')

# Dossier pour les modèles personnalisés
CUSTOM_MODELS_DIR = os.path.join(settings.MEDIA_ROOT, 'nlp_models')

class FeedbackClassifier:
    """Classe pour la classification automatique des feedbacks"""
    
    def __init__(self, model_path=None):
        """Initialise le classifieur, charge le modèle s'il existe ou en crée un nouveau"""
        self.model = None
        self.categories = list(CATEGORY_KEYWORDS.keys())
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.active_custom_model_id = None
        
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info(f"Modèle NLP chargé avec succès depuis {self.model_path}")
            else:
                logger.warning("Aucun modèle NLP trouvé, utilisation de la classification par mots-clés")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle NLP: {str(e)}")
    
    def preprocess_text(self, text):
        """Prétraite le texte pour la classification"""
        if not text:
            return ""
        
        # Convertir en minuscules
        text = text.lower()
        
        # Supprimer les caractères spéciaux et la ponctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Supprimer les chiffres
        text = re.sub(r'\d+', '', text)
        
        # Supprimer les espaces multiples
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def classify_by_keywords(self, text):
        """Classifie le texte en utilisant des mots-clés simples"""
        if not text:
            return None, 0.0
        
        text = self.preprocess_text(text)
        scores = {}
        
        # Calculer le score pour chaque catégorie
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            keyword_matches = 0
            
            # Donner plus de poids aux mots-clés qui apparaissent plusieurs fois
            for keyword in keywords:
                count = text.count(keyword)
                if count > 0:
                    keyword_matches += 1
                    # Ajouter le nombre d'occurrences avec un bonus pour les occurrences multiples
                    score += count * 1.5
            
            if score > 0:
                # Normaliser le score mais avec un facteur de boost pour les correspondances multiples
                base_score = score / (len(keywords) * 1.5)  # Normalisation de base
                # Boost pour le pourcentage de mots-clés correspondants
                match_ratio = keyword_matches / len(keywords)
                # Score final avec boost
                scores[category] = base_score * (1 + match_ratio)
                
                # Log pour débogage
                logger.debug(f"Catégorie: {category}, Score: {scores[category]:.4f}, Mots-clés trouvés: {keyword_matches}/{len(keywords)}")
        
        if not scores:
            return None, 0.0
        
        # Trouver la catégorie avec le score le plus élevé
        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]
        
        # Log pour débogage
        logger.info(f"Meilleure catégorie: {best_category}, Confiance: {confidence:.4f}")
        
        return best_category, confidence
    
    def classify_by_model(self, text):
        """Classifie le texte en utilisant le modèle ML entraîné"""
        if not self.model or not text:
            return None, 0.0
        
        try:
            text = self.preprocess_text(text)
            
            # Prédire la catégorie
            category_idx = self.model.predict([text])[0]
            category = self.categories[category_idx]
            
            # Obtenir la probabilité (confiance)
            proba = max(self.model.predict_proba([text])[0])
            
            return category, proba
        except Exception as e:
            logger.error(f"Erreur lors de la classification par modèle: {str(e)}")
            return None, 0.0
    
    def classify(self, text):
        """Classifie le texte en utilisant le modèle ML ou les mots-clés si le modèle n'est pas disponible"""
        if self.model:
            category, confidence = self.classify_by_model(text)
            if category and confidence > 0.3:  # Seuil de confiance
                return category, confidence
        
        # Fallback sur la classification par mots-clés
        return self.classify_by_keywords(text)
    
    def train_model(self, texts, labels):
        """Entraîne un nouveau modèle ML avec les données fournies"""
        try:
            # Créer un pipeline avec TF-IDF et Naive Bayes
            self.model = Pipeline([
                ('vectorizer', TfidfVectorizer(max_features=5000)),
                ('classifier', MultinomialNB())
            ])
            
            # Prétraiter les textes
            processed_texts = [self.preprocess_text(text) for text in texts]
            
            # Convertir les étiquettes en indices
            label_indices = [self.categories.index(label) for label in labels]
            
            # Entraîner le modèle
            self.model.fit(processed_texts, label_indices)
            
            # Sauvegarder le modèle
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump(self.model, f)
            
            logger.info("Modèle NLP entraîné et sauvegardé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement du modèle NLP: {str(e)}")
            return False
    
    def suggest_priority(self, text):
        """Suggère une priorité basée sur le contenu du texte"""
        text = self.preprocess_text(text)
        
        # Mots-clés pour chaque niveau de priorité
        urgent_keywords = ['urgent', 'immédiat', 'critique', 'grave', 'danger', 'vie', 'mort', 'catastrophe', 'urgence']
        high_keywords = ['important', 'sérieux', 'majeur', 'significatif', 'préoccupant', 'inquiétant']
        medium_keywords = ['modéré', 'moyen', 'normal', 'standard', 'habituel']
        low_keywords = ['mineur', 'faible', 'léger', 'petit', 'minimal']
        
        # Compter les occurrences de mots-clés
        urgent_count = sum(1 for keyword in urgent_keywords if keyword in text)
        high_count = sum(1 for keyword in high_keywords if keyword in text)
        medium_count = sum(1 for keyword in medium_keywords if keyword in text)
        low_count = sum(1 for keyword in low_keywords if keyword in text)
        
        # Déterminer la priorité
        if urgent_count > 0:
            return 'urgent'
        elif high_count > low_count and high_count > medium_count:
            return 'high'
        elif medium_count > low_count:
            return 'medium'
        else:
            return 'low'

# Instance globale du classifieur par défaut
default_classifier = FeedbackClassifier()

# Dictionnaire pour stocker les instances de classifieurs personnalisés
custom_classifiers = {}

def get_active_model_classifier():
    """Récupère le classifieur du modèle NLP actif"""
    from .models import NLPModel
    
    try:
        # Récupérer le modèle actif
        active_model = NLPModel.objects.filter(is_active=True).first()
        
        if active_model and active_model.file:
            model_path = active_model.file.path
            
            # Vérifier si le classifieur est déjà chargé
            if active_model.id not in custom_classifiers:
                # Créer une nouvelle instance de classifieur avec ce modèle
                custom_classifiers[active_model.id] = FeedbackClassifier(model_path=model_path)
                custom_classifiers[active_model.id].active_custom_model_id = active_model.id
                logger.info(f"Classifieur personnalisé chargé pour le modèle {active_model.id}")
            
            return custom_classifiers[active_model.id]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du modèle NLP actif: {str(e)}")
    
    # Utiliser le classifieur par défaut si aucun modèle personnalisé n'est actif
    return default_classifier

def classify_feedback(text):
    """Fonction utilitaire pour classifier un feedback"""
    if not text:
        return {'category': None, 'confidence': 0, 'priority': 'medium'}
    
    # Récupérer le classifieur du modèle actif
    classifier = get_active_model_classifier()
    
    # Utiliser le modèle ML si disponible, sinon utiliser la classification par mots-clés
    if classifier.model:
        category, confidence = classifier.classify_by_model(text)
    else:
        category, confidence = classifier.classify_by_keywords(text)
    
    # Déterminer la priorité en fonction du contenu
    priority = classifier.suggest_priority(text)
    
    # Enregistrer les statistiques d'utilisation du modèle si c'est un modèle personnalisé
    if hasattr(classifier, 'active_custom_model_id') and classifier.active_custom_model_id:
        try:
            from .models import NLPModel
            model = NLPModel.objects.get(id=classifier.active_custom_model_id)
            model.usage_count += 1
            model.last_used = timezone.now()
            model.save(update_fields=['usage_count', 'last_used'])
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statistiques du modèle NLP: {str(e)}")
    
    return {'category': category, 'confidence': confidence, 'priority': priority}
