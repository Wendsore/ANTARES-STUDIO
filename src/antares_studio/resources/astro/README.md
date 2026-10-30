# Données astronomiques et géographiques livrées

Ressources réelles utilisées par les objets *Astre*, *Carte du monde* et *Ciel étoilé* (ADR-0009),
téléchargées le 2026-10-30. Catalogue et crédits utilisés par le logiciel : `resources/astro.py`
(`DATASETS`), repris automatiquement dans le générique des vidéos qui les affichent.

## Textures des astres — `astro/textures/`

Solar System Scope (INOVE), https://www.solarsystemscope.com/textures/, fichiers « 2K » (2 048 × 1 024,
projection équirectangulaire) d'après les données de la NASA. Licence **Creative Commons Attribution 4.0
International** (https://creativecommons.org/licenses/by/4.0/). Fichiers **non modifiés** : seul le
préfixe `2k_` du nom a été retiré (empreintes identiques à celles des fichiers téléchargés).

| Fichier | Licence | SHA-256 |
|---|---|---|
| `textures/earth_clouds.jpg` | CC-BY-4.0 | `fffd7f68d41b37274822150e54a6ef605af1d3ec35624d9f628c3b896bfa42ed` |
| `textures/earth_daymap.jpg` | CC-BY-4.0 | `767ee1dc6eb3802699bfccf6f264880f8acd0b80de3191cd24984fe279b07b7c` |
| `textures/earth_nightmap.jpg` | CC-BY-4.0 | `c16fd1bc096ab91a5c5265c6ff9847c43f489f2e2ee790ccdbcbd03251cf3a5a` |
| `textures/jupiter.jpg` | CC-BY-4.0 | `b0f04d005350252636b0e3396fc592548cbd9e9126b269d32d5c6abd4b0e4f2b` |
| `textures/mars.jpg` | CC-BY-4.0 | `2d187f3e77a98eaa8cea5f4cc722f633c122ef170b9e94ace6b5fb6cbc3f8e01` |
| `textures/mercury.jpg` | CC-BY-4.0 | `5a5c80607f643496bac9a631e71957def35ed788895f18b678ac849c2b38e48a` |
| `textures/moon.jpg` | CC-BY-4.0 | `2764ba6535ea0481a062846ee033cc7a909dae05b31a8fd13f3e98f3a7fd92bd` |
| `textures/neptune.jpg` | CC-BY-4.0 | `cb42ea82709741d28b0af44d8b283cbc6dbd0c521a7f0e1e1e010ade00977df6` |
| `textures/saturn.jpg` | CC-BY-4.0 | `54a900ca9bf7ab62e70f862852759abdf342e6d6436a95a2fe9ebdb6bcd3bbac` |
| `textures/saturn_ring_alpha.png` | CC-BY-4.0 | `4b0644b2f3ef259fd0bfaedd9dc52f9e7d9738f65f50363e8c4dd19f650d7334` |
| `textures/stars_milky_way.jpg` | CC-BY-4.0 | `ec2240e6f3784d962ab81609b228bfd470e87c86d1fed5e99134d4cd3de24239` |
| `textures/sun.jpg` | CC-BY-4.0 | `ff0f076ba65e03b5ab518451bc96699325be38e3ccbdd5869ee1c00f3a0c8816` |
| `textures/uranus.jpg` | CC-BY-4.0 | `d15239d46f82d3ea13d2b260b5b29b2a382f42f2916dae0694d0387b1204a09d` |
| `textures/venus_atmosphere.jpg` | CC-BY-4.0 | `225012ad4911730605c4e189ca2a3bf674fce50cc48aab4102b936b47d6991ac` |
| `textures/venus_surface.jpg` | CC-BY-4.0 | `dbe5db1c794a8ab4cbf7dd6bf193540c400fc833ce1e6cc399318aa68026278b` |

## Cartes du monde — `geo/`

Natural Earth, https://www.naturalearthdata.com/, *Admin 0 – Countries* aux échelles 1:50 m et 1:110 m,
depuis https://github.com/nvkelso/natural-earth-vector (`geojson/ne_50m_admin_0_countries.geojson` et
`ne_110m_…`). **Domaine public**. Fichiers **dérivés** : seuls sont gardés le nom français (`NAME_FR`), le
nom anglais, le code ISO, le continent et le type ; les coordonnées sont arrondies au centième de degré
(≈ 1 km).

| Fichier | Licence | SHA-256 |
|---|---|---|
| `geo/countries_110m.json` | domaine public | `0623bf65472c8ceffbcfefd46fd5f2c10cf49f5b3de15d34267c8db2c3e8eb31` |
| `geo/countries_50m.json` | domaine public | `0a0348a1157c2badb5b5c9eb409f7d09f359bc31681099c97938c445a9db65b2` |

## Étoiles et constellations — `sky/`

d3-celestial d'Olaf Frohn, https://github.com/ofrohn/d3-celestial (`data/stars.6.json`,
`data/starnames.json`, `data/constellations.json`, `data/constellations.lines.json`), licence **BSD 3
clauses** (texte complet : `sky/LICENSE-d3-celestial.txt`) ; positions, magnitudes et indices B−V issus du
catalogue Hipparcos (ESA, 1997). Fichiers **dérivés** : 5 044 étoiles de magnitude ≤ 6 réduites à
`[numéro Hipparcos, ascension droite °, déclinaison °, magnitude, B−V]` avec leurs noms usuels ; 88
constellations (sigle UAI, nom français et nom latin fournis par d3-celestial, point d'étiquette,
tracés). Les noms d'étoiles sont les noms anglais du catalogue, remplacés par leur graphie française
d'usage quand elle diffère (Bételgeuse, Véga, Antarès… : table `STAR_NAMES_FR` de `resources/astro.py`).

| Fichier | Licence | SHA-256 |
|---|---|---|
| `sky/constellations.json` | BSD-3-Clause | `5eb6284a5042308531c892132dca9066e84263a63d11a41c7db87fbb1547786a` |
| `sky/stars.json` | BSD-3-Clause | `929499c13075aec75eec6ac89fa4aabee82f7a540604a57d427579fce4e4d213` |

## Valeurs numériques (dans `resources/astro.py`)

- Planètes et Lune : NASA NSSDCA, *Planetary Fact Sheet*, https://nssdc.gsfc.nasa.gov/planetary/factsheet/
  (domaine public) ; Soleil : valeurs nominales de l'UAI (résolution B3, 2015).
- Étoiles connues : Wikidata (CC0), propriétés température effective, rayon, masse et distance, consultées
  le 2026-10-30 ; quand plusieurs mesures divergent, la moyenne est retenue et indiquée en note.
