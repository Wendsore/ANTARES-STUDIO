# Équations

L'objet **Équation (formule)** affiche des formules mathématiques **sans installer LaTeX**. ANTARES lit une écriture proche de LaTeX et dessine lui-même fractions, racines, exposants et indices.

## Ajouter une équation

1. Bibliothèque, catégorie **Maths**, double-clic sur **Équation (formule)**.
2. Modifiez le champ **Formule** dans l'Inspecteur, ou double-cliquez sur l'équation.
3. Réglez la taille, la police, l'italique des variables et les couleurs.

## Transformer une formule en une autre

Dans l'Inspecteur, le champ **Transformer en** reçoit une formule cible. L'animation **Transformer la formule** (Bibliothèque, onglet Animations) fait passer de l'une à l'autre : les symboles communs **glissent** jusqu'à leur nouvelle place, les autres disparaissent ou apparaissent en fondu. La progression **Transformation (0 → 1)** s'anime aussi à la main avec le losange ◆.

Exemple : `E = mc^{2}` → `m = \frac{E}{c^{2}}`.

## Syntaxe

| Écrire | Pour obtenir |
|---|---|
| `x^{2}` | exposant |
| `a_{n}` | indice |
| `\frac{a}{b}` | fraction |
| `\sqrt{x}` | racine carrée |
| `\vec{v}` | vecteur (flèche au-dessus) |
| `\hat{x}`, `\bar{x}` | chapeau, barre au-dessus |
| `\text{vitesse}` | texte droit, non italique |
| `{ … }` | groupe |
| `\,` `\;` `\:` | espace fine |
| `\!` | rien (accepté pour compatibilité) |
| `\{` `\}` `\\` | accolade ou barre oblique inverse littérale |

Un seul caractère n'a pas besoin d'accolades : `x^2` et `a_n` fonctionnent.

### Exemples

| Formule | Écriture |
|---|---|
| Gravitation universelle | `F = \frac{G m_{1} m_{2}}{r^{2}}` |
| Vitesse orbitale circulaire | `v = \sqrt{\frac{G M}{r}}` |
| Troisième loi de Kepler | `T^{2} = \frac{4 \pi^{2}}{G M} a^{3}` |
| Énergie de masse | `E = m c^{2}` |
| Approximation | `c \approx 3,00 \cdot 10^{8} \text{ m/s}` |

## Symboles reconnus

<!-- auto:symboles -->

## Sécurité et erreurs

La formule n'est **jamais exécutée** : c'est du texte mis en forme. Une commande inconnue, par exemple `\foo`, reste affichée telle quelle. Une accolade oubliée est fermée automatiquement. Si le rendu surprend, vérifiez l'orthographe des commandes et les accolades.

Les tableaux et matrices ne sont pas encore disponibles. Une formule peut **s'écrire progressivement** (animation **Écrire**, voir [Écriture progressive](ecriture-et-craie.md)) ou se transformer en une autre (voir plus haut).
