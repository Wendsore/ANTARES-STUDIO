# Graphiques de données (CSV)

Tracez des **données réelles** : mesures d'une expérience, valeurs publiées par une agence scientifique, résultats d'un tableur.

## Préparer le fichier

Un fichier **CSV** : texte, une ligne d'en-tête, puis une ligne par mesure. Depuis un tableur : *Enregistrer sous… > CSV*.

```
distance moyenne au Soleil (10^6 km);période orbitale (jours)
57,9;88,0
108,2;224,7
149,6;365,2
```

- **Unités dans l'en-tête**, entre parenthèses ou crochets : `t (s)`, `hauteur [m]`. Elles s'affichent sur les axes.
- **Séparateur** : point-virgule, virgule ou tabulation, détecté automatiquement.
- **Décimales** : virgule française ou point.
- **Encodage** : UTF-8 de préférence ; les fichiers Windows (cp1252, latin-1) sont acceptés.
- Une cellule vide ou non numérique est ignorée et signalée.
- Limites : 200 000 lignes et 32 Mo.

## Importer

1. Enregistrez le projet : le CSV est copié dans son dossier `assets/`.
2. **Objet > Importer des données (CSV) en graphique…**
3. Un graphique est créé avec les **deux premières colonnes numériques** en X et en Y.
4. La fiche de provenance s'ouvre : indiquez la source des données.

Les anomalies du fichier (cellules ignorées, colonnes sans nombre, noms en double) s'affichent dans la barre d'état.

## Régler le graphique

Dans l'Inspecteur :

- **Données (CSV)**, **Colonne X**, **Colonne Y** : choix parmi les colonnes du fichier ;
- **Titre**, **Largeur**, **Hauteur** ;
- bornes **X min / X max / Y min / Y max** (0 = automatique, avec des graduations « rondes ») ;
- **Afficher les points**, **Grille**, épaisseur de la courbe, taille des libellés ;
- couleurs de la courbe, du fond, des axes et du texte.

## Animer le tracé

Appliquez l'animation **Tracer la courbe** : la propriété *Progression du tracé* passe de 0 à 1 et la courbe se dessine de gauche à droite. Elle s'anime aussi à la main avec des [images clés](images-cles.md).

## Exemple fourni

Le [tutoriel 5](tutoriels.md) importe `planetes-periode-distance.csv` : distances et périodes des huit planètes selon la NASA. Le graphique montre que la période croît plus vite que la distance. C'est la troisième loi de Kepler : le carré de la période est proportionnel au cube de la distance.

Échelles logarithmiques, histogrammes et plusieurs courbes sur un même graphique ne sont pas encore disponibles.
