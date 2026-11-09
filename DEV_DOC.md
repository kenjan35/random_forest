
##  Traitement des données
### 1. Réception du fichier
L’analyse commence généralement avec :
```
analyze_file(csv_path)
```
dans *analysis.py*.

Cette fonction orchestre toute l’analyse.

Le fichier peut être lancé depuis :

* *single_file_tab.py*, avec run_analysis() ;
* *batch_scan_tab.py*, avec BatchScanWorker.run() ;
* *workers.py*, avec SingleFileWorker.run() ou BatchScanWorker.run().

### 2. Lecture et vérification du CSV

*analyze_file()* appelle :
```
    _read_input(csv_path)
```

dans **analysis.py**.

Cette fonction :

1. vérifie que le fichier existe ;
2. utilise *pd.read_csv()* pour le lire ;
3. vérifie les colonnes obligatoires ;
4. nettoie la colonne carburant avec *clean_fuel()* ;
5. récupère les valeurs de statut et les dates.
Les colonnes principales sont définies dans **config.py** :

* *FUEL_COLUMN* : niveau de carburant ;
* *STATUS_COLUMN* : état du générateur ou du capteur ;
* *TIMESTAMP_COLUMN* : date et heure.
Si le fichier est invalide, *_read_input()* lève *AnalysisError*.

### 3. Nettoyage du carburant
La fonction utilisée est :
```
    clean_fuel(...)
```

dans **preprocess.py**.

Elle prépare les valeurs de carburant avant leur envoi au modèle. Cela permet d’éviter qu’une valeur manquante ou incorrecte perturbe toute l’analyse.

### 4. Analyse par le modèle
*analyze_file()* appelle ensuite :
```
    _predict(csv_path, fuel, status)
```

Cette fonction appelle :
```
    predict_arrays(fuel, status)
```

dans **predict_pipeline_utils.py**.

*predict_arrays()* réalise les principales étapes de prédiction :

1. charge le modèle avec *load_model()* ;
2. convertit les données en valeurs numériques ;
3. calcule le nombre de fenêtres à analyser ;
4. prépare le contexte avec *_prediction_context()* ;
5. calcule les prédictions avec *_predict_components()* ;
6. combine les résultats avec *_combine_predictions()* ;
7. applique le traitement spécial des pertes masquées avec *_apply_bridged_losses()*.

### 5. Création des fenêtres d’analyse
Dans *_predict_components()*, le programme appelle :
```
    create_features(fuel)
```

puis :
```
    create_windows(..., WINDOW_SIZE)
```

Les données ne sont donc pas analysées uniquement ligne par ligne.

Elles sont regroupées en fenêtres successives, par exemple :
```
    lignes 1 à 20
    lignes 2 à 21
    lignes 3 à 22
```

Chaque fenêtre reçoit une prédiction :

* 0 : aucune anomalie détectée ;
* 1 : comportement pouvant correspondre à un vol.

### 6. Utilisation du modèle et des règles
Dans *_predict_components()*, le modèle calcule une probabilité avec :
```
    model.predict_proba(X)
```

Cette probabilité est comparée à un seuil.

La fonction *_magnitude_gate()* vérifie également que la baisse de carburant est suffisamment importante par rapport au bruit normal attendu.

En parallèle, le programme applique des règles métier avec :
```
    _rule_based_flags(...)
```

Le résultat du modèle et celui des règles sont ensuite combinés par :
```
    _combine_predictions(...)
```

Cela évite de dépendre uniquement du modèle machine learning.

### 7. Détection des problèmes de capteur
Dans *analyze_file()*, le programme appelle :
```
    detect_sensor_glitches(fuel)
```

dans **analysis_utils.py**.

Cette fonction recherche les périodes où les données semblent peu fiables, par exemple :

* valeurs incohérentes ;
* coupures ;
* décrochages du capteur ;
* séquences anormales.

Le programme traite aussi les pertes qui passent temporairement par zéro avec :
```
    zero_bridged_losses_for(fuel, status)
```

Cette fonction permet de ne pas perdre complètement un événement réel simplement parce que le capteur a enregistré une valeur zéro pendant la baisse.

### 8. Regroupement des fenêtres détectées
Les prédictions sont d’abord produites fenêtre par fenêtre.

Ensuite, *analyze_file()* appelle :
```
    classify_events(
    prediction,
    glitch_mask,
    bridged,
    fuel,
    timestamps,
)
```

dans **analysis_utils_1.py**.

*classify_events()* :

1. cherche les fenêtres où *prediction == 1* ;
2. regroupe les fenêtres consécutives avec *group_consecutive()* ;
3. transforme chaque groupe en événement ;
4. calcule le début et la fin ;
5. calcule la quantité perdue ;
6. vérifie si l’événement chevauche un problème de capteur.
Par exemple :
```
    Fenêtres détectées : 10, 11, 12, 13
```

deviennent :
```
    Un seul événement de la ligne 10 à la ligne 32
```

La taille finale dépend de *WINDOW_SIZE*.

### 9. Création d’un événement
La fonction utilisée est :
```
    make_event(...)
```

dans **analysis_utils_1.py**.

Elle construit un dictionnaire contenant notamment :
```
    {
    "row_start": ...,
    "row_end": ...,
    "ts_start": ...,
    "ts_end": ...,
    "glitch_ratio": ...,
    "fuel_drop": ...
}
```

La quantité perdue est calculée avec :
```
    event_loss(...)
```

dans **fuel_math.py**.

### 10. Classification finale
Dans *classify_events()* :

* si l’événement correspond à une perte avec passage à zéro, il est conservé comme événement réel ;
* si le taux de données perturbées dépasse *GLITCH_OVERLAP_THRESHOLD*, il est placé dans *events_ignored* ;
* sinon, il est placé dans *events*.

La fonction *append_unreported_glitches()* ajoute aussi les problèmes de capteur qui n’ont pas déjà été associés à un événement.

### 11. Construction du résultat final
Après la classification, *analyze_file()* appelle :
```
    _build_result(...)
```

dans **analysis.py**.

Cette fonction prépare le résultat final, notamment :

* *events* : événements considérés comme vols ;
* *events_ignored* : événements écartés à cause des données ;
* *has_theft* : indique si un vol a été retenu ;
* *has_sensor_glitch* : indique si un problème capteur existe ;
* *fuel* : données nettoyées ;
* *timestamps* : dates ;
* *n_events* : nombre de vols retenus.

### 12. Affichage dans l’interface
Pour une analyse individuelle, *on_success(result)* dans **single_file_tab_utils_1.py** :

1. récupère le résultat ;
2. affiche le statut ;
3. utilise *tagged_events(result)* ;
4. affiche les événements dans la liste ;
5. transmet les données au graphique avec :
    self.chart.plot(result)

Les fonctions d’export sont ensuite disponibles avec :
```
    export_csv(...)
```

et :
```
    write_events_csv(...)
```

dans **export.py**.