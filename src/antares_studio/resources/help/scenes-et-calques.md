# Scènes, calques et groupes

## Les scènes

Une vidéo se découpe en **scènes** : introduction, explication, conclusion, crédits… Chaque scène a sa durée, son fond, ses objets, ses sons et ses sous-titres.

Panneau **Scènes et objets**, partie haute :

- **Clic** sur une scène : l'affiche dans le canevas et la Timeline.
- **+ Scène** : ajoute une scène vide de 10 secondes.
- **Double-clic** : renomme la scène.
- **Supprimer** : supprime la scène et ses objets, après confirmation ; Ctrl+Z la rétablit. Un projet garde toujours au moins une scène.

Ajouter un **modèle** depuis la Bibliothèque crée aussi une nouvelle scène (voir [Modèles](modeles.md)). La durée et le fond se règlent dans l'[Inspecteur](inspecteur.md) quand rien n'est sélectionné.

À l'export, la case « Toutes les scènes à la suite » les enchaîne dans l'ordre de la liste.

### Transitions

Une scène peut **entrer** par une transition, réglée dans l'[Inspecteur](inspecteur.md) quand rien n'est sélectionné : fondu enchaîné, fondu au noir, glissement vers la gauche ou vers le haut, volet. La transition part de la dernière image de la scène précédente (du noir pour la première) et occupe les premières images de la scène : la durée totale ne change pas. Elle est visible dans l'éditeur et identique à l'export.

### Caméra

**Objet > Caméra (cadrage animé)** ajoute une caméra : sa **position** est le point visé, son **zoom** (1 = cadre entier) et sa **rotation** (inclinaison) s'animent comme toute propriété. La vidéo montre ce que voit la caméra.

**Affichage > Voir à travers la caméra**, décoché, montre toute la scène avec le cadre de la caméra dessiné par-dessus : pratique pour la placer. Seule la première caméra visible filme.

## Les objets (calques)

Partie basse : l'arbre des objets de la scène, du premier plan à l'arrière-plan.

- **Clic** sur un nom : sélectionne l'objet.
- **Double-clic** sur un nom : le renomme.
- Case **œil** : visible ou masqué. Un objet masqué n'apparaît pas non plus dans la vidéo.
- Case **cadenas** : verrouillé, insensible aux clics sur le canevas.
- **▲ Monter / ▼ Descendre** : change l'ordre de superposition.

## Les groupes

- **Édition > Grouper** (Ctrl+G) : réunit la sélection dans un groupe. Déplacer, tourner ou animer le groupe agit sur tout son contenu.
- **Édition > Dégrouper** (Ctrl+Maj+G) : défait le groupe ; chaque objet reprend sa place. Attention : la rotation et l'échelle propres au groupe ne sont pas reportées sur les objets.

Exemple : groupez la Terre et la Lune, puis faites tourner le groupe autour du Soleil.
