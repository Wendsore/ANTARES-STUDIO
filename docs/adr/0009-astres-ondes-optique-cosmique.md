# ADR-0009 — Astres réels, cartes, ciel, ondes, optique et phénomènes cosmiques

**Date :** 2026-10-30 — **Statut :** accepté — **Phase :** 13 — **Branche :** `feat/phase-13-astres-ondes-optique` (empilée sur la PR #14)

## Contexte

Demande du porteur : « qu'en est-il des assets […] rajouter pas mal d'assets disponibles, notamment les
modèles 3D des planètes connues, des étoiles connues. J'ai besoin d'assets existants […] 3D ou 2D, des
planisphères, des continents, la lune, ses phases. Est-ce qu'il y a aussi un mode d'éclairage […] simuler
des ondes ? […] l'effet Doppler […] les effets de marée avec des déformations exagérées […] un rayon
lumineux sous différentes formes […] les expériences du français […] sur la dualité onde corpuscule
[…] la vie d'une étoile qui se termine par une supernova […] qui peut se terminer par un trou noir […]
la supernova qu'on peut trouver dans Outer Wilds ».

**État avant** : aucune ressource visuelle livrée. Seuls existaient un CSV d'exemple (périodes et distances
des planètes, NASA) et le script Blender facultatif de planète (phase 7). Pas d'objet astre, de carte, de
ciel, d'onde, de rayon ni de lumière. L'éclairage était limité à la lumière fixe des modèles glTF et des
solides 3D. Le physicien est **Alain Aspect** (prix Nobel 2022). L'expérience photon par photon
correspondante est Grangier, Roger et Aspect, *Europhys. Lett.* 1, 173 (1986), DOI 10.1209/0295-5075/1/4/004.

Contraintes inchangées : hors ligne ; un seul dessin pour l'éditeur et l'export (ADR-0001) ; schéma
additif ; provenance et licence de toute ressource livrée (ADR-0003) ; **données réelles seulement**.
L'implémentation a été menée en autonomie ; chaque arbitrage est consigné ci-dessous.

## Décisions

| # | Question | Retenu | Écarté, et pourquoi |
|---|---|---|---|
| 1 | « Modèles 3D des planètes » | **Sphère texturée calculée** (NumPy, à la résolution de sortie, mise en cache) par un nouveau type **Astre** : rotation, inclinaison de l'axe, point de vue, lumière directionnelle animable (Lambert, terminateur adouci), côté nuit, nuages et lumières des villes pour la Terre, liseré d'atmosphère, anneaux de Saturne avec ombre de la planète et ordre avant/arrière, assombrissement centre-bord des étoiles | Fichiers glTF de planètes : le moteur glTF ne dessine pas les textures (limite de la phase 10) ; une sphère maillée texturée ne montrerait rien de plus qu'une sphère calculée |
| 2 | Quelles textures ? | **Solar System Scope**, 15 fichiers 2K (Soleil, 8 planètes, Lune, Vénus surface et atmosphère, Terre jour/nuit/nuages, anneau de Saturne, Voie lactée), **CC BY 4.0**, non modifiés, 7,3 Mo ; attribution ajoutée **automatiquement** au générique des vidéos qui les affichent | NASA (domaine public) : cartes hétérogènes, pas de jeu complet et homogène ; 8K : 10 fois plus lourd ; textures générées : contraire à « assets existants » |
| 3 | Caractéristiques des astres | NASA *Planetary Fact Sheet* (diamètre, rotation, inclinaison de l'axe, distance, période, lunes) ; Soleil : valeurs nominales UAI 2015 ; la variante de chaque planète prend sa **vraie inclinaison d'axe** | Valeurs arrondies de mémoire : contraire à la règle des données réelles |
| 4 | Étoiles connues | **16 étoiles** (Soleil, Sirius A, Véga, Rigel, Bételgeuse, Antarès, Aldébaran, Deneb, Achernar, Altaïr, Polaire, Arcturus, Pollux, Bellatrix, Spica, Canopus) : température, rayon, masse, distance depuis **Wikidata** (CC0, identifiant Q noté) ; couleur = **corps noir** à la température effective (Planck intégré sur les fonctions CIE 1931, ajustement de Wyman, Sloan et Shirley 2013, vers sRGB) | Alpha du Centaure A/B : températures incohérentes sur Wikidata, retirées plutôt qu'inventées ; couleurs choisies à l'œil : non reproductibles |
| 5 | Phases de la Lune | La phase est la **direction de la lumière** (0° = pleine lune, 180° = nouvelle lune), animée par le preset **Phases (lumière qui tourne)** ; modèle avec l'orbite vue de dessus et la Lune vue de la Terre synchronisées | Images de phases : pas animable, pas de phase intermédiaire |
| 6 | Marées | Enveloppe **r = R(1 + a·P₂(cos(θ − φ)))** (forme du potentiel de marée au 2ᵉ ordre), amplitude exagérée réglable ; deux rendus : bourrelet océanique translucide ou astre entier étiré ; preset **Marées qui suivent un astre** calé sur le preset *Orbite* (même angle, signe de l'axe y écran) ; avance des bourrelets réglable | Simulation hydrodynamique : sans rapport avec une vidéo pédagogique ; amplitude réelle (< 1 m) : invisible, d'où la légende « exagérée » |
| 7 | Cartes | **Natural Earth** (domaine public), pays 1:50 m et 1:110 m réduits à nom français, ISO, continent (1,7 Mo) ; projections **Equal Earth** (Šavrič et al. 2018, aires respectées, par défaut), équirectangulaire, Mercator (±82°) ; styles continents, pays, contours, satellite (texture de la Terre reprojetée), nuit ; tracé progressif d'ouest en est | Images de planisphères : une seule projection, pas de mise en valeur ni de tracé animé |
| 8 | Ciel | **d3-celestial** (BSD-3) : 5 044 étoiles Hipparcos jusqu'à la magnitude 6, 88 constellations (tracés, noms français et latins) ; projection **stéréographique** (est à gauche, comme une carte du ciel), taille selon la magnitude, couleur selon B−V (Ballesteros 2012 → corps noir, adoucie vers le blanc comme à l'œil) | Calcul du ciel local (heure, lieu, horizon) : utile mais non demandé, noté dans « Limites » |
| 9 | Ondes et Doppler | Type **Ondes**, piloté par `time_s` : **fronts** émis à τₖ = k/f centrés sur la position de la source à τₖ (Doppler exact, cône de Mach si v > c) ; **champ** Re Σ e^{i(kr − ωt)}/√r ou intensité moyenne (Young) ; **corde** progressive ou stationnaire ; fonctions de contrôle `doppler_classical`, `doppler_relativistic`, `mach_angle_deg` | Ondes dessinées à la main : pas de garantie physique ; résolution d'équation d'onde : coûteux, sans gain visible pour ces cas |
| 10 | Le temps | Paramètre **`time_s`** animé par un preset **Faire avancer le temps** (le temps de l'objet suit celui de la scène) | Lire le temps de la scène dans le moteur : les objets ne seraient plus des fonctions de leurs seuls paramètres (ADR-0002) |
| 11 | Rayons lumineux | Type **Rayon** sur un chemin de points : faisceau avec lueur, onde le long du chemin, paquets d'onde, photons, pointillés, flèches ; **couleur de la longueur d'onde** (Bruton 1996) ; propagation animable | Calcul de réfraction et de réflexion : un moteur de tracé de rayons sort du périmètre ; l'utilisateur place le chemin |
| 12 | Éléments d'optique | Type **Élément d'optique** : laser, lampe, miroir, lame séparatrice, lentilles convergente et divergente, une et deux fentes, écran, détecteur, prisme, polariseur ; état **allumé / déclenché** animable (preset **Déclic du détecteur**) | Images d'appareils : style hétérogène, pas d'état animable |
| 13 | Dualité onde-corpuscule | Type **Écran de détection** : impacts tirés **par rejet** selon cos²·sinc² (deux fentes), sinc² (une fente), somme incohérente (chemin mesuré : pas de franges) ; tirage à graine fixe, reproductible ; preset **Impacts qui s'accumulent** ; modèle **Photons et fentes de Young** citant Grangier–Roger–Aspect 1986 et Tonomura 1989 | Points placés à la main : la figure doit émerger de la statistique, c'est le cœur de l'expérience |
| 14 | Supernova (« façon Outer Wilds ») | Type **Particules** : explosion avec freinage, **coquille** brillante sur son bord, **nébuleuse** (densité accumulée puis floutée, filaments), **disque d'accrétion** (ω ∝ r^−3/2, chute lente) ; mélange additif ; modèle **Vie et mort d'une étoile** : supergéante qui gonfle, effondrement, éclair, coquille, nébuleuse, trou noir. Seul le principe visuel du jeu est repris (onde de choc lumineuse qui s'étend), aucun élément du jeu | Reprendre des images du jeu : droits d'auteur ; simulation hydrodynamique : hors de portée et sans gain pédagogique |
| 15 | Trou noir | Type **Trou noir** : horizon noir, anneau de photons, disque incliné ; la partie arrière du disque est **redessinée au-dessus et au-dessous de l'horizon** (apparence classique de la lentille gravitationnelle) ; effet de phare réglable ; **dit « illustration »** dans l'aide | Tracé de géodésiques de Schwarzschild : coûteux à chaque image ; l'approximation est écrite |
| 16 | Éclairage | Type **Lumière** (halo, projecteur, pénombre avec un cercle éclairé, rayons) ; direction et hauteur de lumière animables sur **Astre** et **Solide 3D** ; pour le solide, le défaut reproduit **exactement** la lumière fixe d'origine (écart nul, test) et un ancien projet sans ces champs garde la lumière d'origine | Moteur d'éclairage global (ombres portées entre objets) : demande un moteur 3D (ADR-0008, décision 12) |
| 17 | Bibliothèque | 6 catégories : **Astres**, **Étoiles connues**, **Cartes et ciel**, **Ondes**, **Lumière et optique**, **Phénomènes cosmiques** ; 76 nouvelles variantes (90 en tout) ; clés `style_…` d'une variante appliquées au style de l'objet (`split_style`) | Un seul objet par type, à régler ensuite : le porteur demande des ressources prêtes à l'emploi |
| 18 | Modèles | 8 nouveaux : phases de la Lune, effet Doppler, marées, vie et mort d'une étoile, photons et fentes de Young, Système solaire, planisphère, ciel d'Orion ; avertissement d'échelle quand les tailles ne sont pas à l'échelle | — |
| 19 | Couleurs à 8 chiffres | Toute couleur de projet passe par `parse_color` (#RRGGBBAA). `QColor("#FFFFFF00")` lit #AARRGGBB, ce qui donnait du **jaune opaque** et teintait tous les astres ; test de non-régression qui échoue sur l'ancien code | — |
| 20 | Halo des astres | Le halo (`corona`, défaut 0,6) ne s'applique qu'aux astres lumineux : sinon toute planète ajoutée depuis la Bibliothèque recevait le halo du Soleil ; test qui échoue sur l'ancien code | Défaut à 0 pour tous : les étoiles de la Bibliothèque perdraient leur éclat |

## Non fait (et pourquoi)

- Modèles maillés en relief (cratères, montagnes) : voir décision 1.
- Réfraction et réflexion calculées : voir décision 11.
- Ciel local (heure, lieu, horizon) et cartes régionales : non demandés, notés dans « Limites ».
- Lentille gravitationnelle exacte : voir décision 15.
- `rendering/effects.py` lit encore des couleurs d'effet avec `QColor(str)` (code antérieur, hors du
  périmètre de cette phase) : sans conséquence pour les couleurs à 6 chiffres des préréglages, mais une
  couleur à 8 chiffres y serait mal lue. Signalé ici pour une phase ultérieure.

## Conséquences et preuves

- Schéma : uniquement additif (10 nouveaux types ; `light_az_deg`, `light_el_deg`, `ambient` sur le solide) ;
  un ancien projet s'ouvre et se dessine à l'identique.
- Ressources : 9,1 Mo dans `resources/astro`, `resources/geo`, `resources/sky`, déjà inclus par
  `resources/**/*` (spec PyInstaller et `package-data`) ; empreintes et licences dans
  `resources/astro/README.md` ; notices dans `packaging/THIRD_PARTY_NOTICES.md` et « Aide > À propos ».
- Tests : voir `docs/session-logs/2026-10-30-astres-ondes-optique.md`.
- **NON TESTÉ sur Windows 11 réel** : chargement des textures et rendu des nouveaux objets sous Windows
  (vérifié sur Linux uniquement ; la CI Windows exécute la suite automatisée).
