#!/usr/bin/env python
"""
Script de démarrage pour le webhook JSON SMS
Ce script charge les variables d'environnement depuis config.env et démarre le webhook
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

def main():
    """Fonction principale pour démarrer le webhook"""
    print("Démarrage du webhook JSON SMS pour la plateforme de feedback...")
    
    # Charger les variables d'environnement depuis config.env si le fichier existe
    if os.path.exists('config.env'):
        print("Chargement de la configuration depuis config.env...")
        load_dotenv('config.env')
        print("Configuration chargée avec succès.")
    else:
        print("Fichier config.env non trouvé. Utilisation des valeurs par défaut ou des variables d'environnement système.")
    
    # Construire la commande avec les arguments
    cmd = [sys.executable, 'app.py']
    
    # Ajouter les arguments supplémentaires passés au script
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    # Afficher la commande
    print(f"Exécution de la commande: {' '.join(cmd)}")
    
    # Exécuter la commande
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du démarrage du webhook: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nArrêt du webhook...")
        sys.exit(0)

if __name__ == '__main__':
    main()
