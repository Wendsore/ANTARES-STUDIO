# ADR-0010 — Personnages chibis en 2D (images fixes changeables)

**Date :** 2026-10-30 — **Statut :** accepté — **Phase :** 14 — **Branche :** `feat/phase-14-personnages-chibi` (empilée sur la PR #15)

## Contexte

Demande du porteur : un chibi qui présente, reflet d'un jeune Africain, qui parle, avec des mouvements
standards, toutes les émotions, des vêtements différents, et plusieurs personnages (un ironique, un
hyper scientifique qui explique, un qui doute, un toujours énervé). Une proposition 3D (VRM, caméra,
Blender) a été faite ; le porteur a choisi de **commencer par des chibis 2D en images fixes, que l'on
peut changer pendant une présentation**.

**État avant** : aucun personnage. Seul l'objet **Image** permettait de poser un dessin importé, sans
émotion ni pose. L'implémentation a été menée en autonomie ; chaque arbitrage est consigné ci-dessous.

## Décisions

| # | Question | Retenu | Écarté, et pourquoi |
|---|---|---|---|
| 1 | D'où viennent les dessins ? | **Dessins originaux composés par le code** en SVG (`rendering/chibi.py`) : silhouette, tenue, coiffure, barbe, accessoires, yeux, sourcils, bouche, bras ; rendu par `QSvgRenderer` | Banques d'images de chibis : licences hétérogènes, un seul style par banque, impossible d'obtenir toutes les combinaisons émotion × tenue × coiffure ; images générées par IA : provenance juridique incertaine (ADR-0003) |
| 2 | Image fixe ou animation ? | **Images fixes** : l'émotion, la pose, le regard, la tenue, les lunettes, le couvre-chef et le sens sont des **listes animables en palier** (une chaîne non couleur n'est pas interpolée par l'évaluateur, ADR-0002) | Morphing des traits entre émotions : non demandé, plus tard si besoin |
| 3 | Combien d'émotions ? | **22** (neutre, explique, joie, fou rire, enthousiasme, émerveillé, fier, ironique, clin d'œil, surprise, peur, doute, réflexion, confusion, agacement, colère, fureur, tristesse, déception, gêne, dégoût, ennui) : les six émotions de base d'Ekman et les attitudes utiles à un présentateur | Liste minimale (6) : ne couvre ni l'ironie ni le doute, demandés |
| 4 | Mouvements standards | **10 poses** de bras : repos, explique, montre, index levé, salue, main au menton, bras croisés, poings sur les hanches, haussement d'épaules, victoire ; **regard** (public, gauche, droite, haut, bas) ; **miroir** pour se tourner vers l'autre personnage | Squelette articulé libre : relève de l'animation 3D proposée pour plus tard |
| 5 | Apparence africaine | **6 teints** de peau noire et métisse ; coiffures **courts, afro, tresses collées, locks, macarons (afro puffs), tresses longues (box braids), rasé** ; tenues **t-shirt, chemise, blouse, sweat, dashiki brodé, costume, maillot de foot** ; barbe, bouc, moustache ; lunettes ; casquette, **kufi** | Un seul personnage figé : le porteur veut plusieurs personnages |
| 6 | Plusieurs personnages | **Fiches de jeu** (variantes de Bibliothèque) : présentateur, présentatrice, scientifique, ironique, sceptique, râleur ; chacune est un point de départ entièrement réglable | Type d'objet par personnage : multiplierait le code pour une simple différence de réglages |
| 7 | Où vit le catalogue ? | `domain/characters.py`, **sans Qt** (le domaine en tire ses listes de choix) ; le dessin reste dans `rendering/` | Tout dans le module de rendu : le domaine aurait importé Qt (AGENTS.md) |
| 8 | Signes de bande dessinée | « ? », « ! », gouttes, veine de colère, étincelles, vapeur, bulles de pensée dessinés **hors du groupe retourné** : ils restent lisibles quand le personnage regarde à gauche | Retourner toute l'image : « ? » écrit à l'envers |
| 9 | Couleurs | Couleurs de tenue lues par `parse_color` (`#RRGGBBAA`) | `QColor(str)` lit 8 chiffres comme `#AARRGGBB` (bug corrigé en phase 13) |
| 10 | Export | Rendus SVG mis en cache **par thread** (l'export tourne dans un thread secondaire) ; vectoriel, donc net en 4K | Cache partagé entre threads : objets Qt non partagés sans précaution |
| 11 | Démonstration | Modèle **Dialogue de personnages** : le scientifique et le sceptique expliquent pourquoi on voit toujours la même face de la Lune (rotation synchrone, environ 27 jours, source NASA *Earth's Moon — Facts*, lue le 2026-10-30) | Dialogue sans contenu scientifique : contraire à l'esprit du logiciel |
| 12 | « Trop enfantin » : le personnage du porteur | Réglage **Proportions** : *Chibi* (inchangé) ou **Adulte stylisé** ; l'adulte réutilise la tête, la coiffure, la barbe, les couvre-chefs et les signes du chibi, réduits par une transformation SVG, mais a son propre corps (épaules larges, jambes longues), ses bras, ses poses et ses traits (yeux en amande sans reflets d'anime, nez large, lèvres pleines, pas de rose aux joues) | Second module de dessin complet : doublerait les coiffures et les tenues ; supprimer le chibi : le porteur demande de le garder |
| 13 | Ressemblance avec le porteur | D'après ses photos : peau brun foncé, cheveux courts, front dégagé, visage rond, barbe courte avec bouc et moustache, lunettes à fine monture, carrure solide. Tenues tirées de ses photos : **doudoune sans manches sur sweat**, **gilet haute visibilité** sur maillot sombre, **veste en jean doublée sur sweat**, **polo** ; **casque de chantier**, **lunettes de protection**, monture **fine** ; trois fiches *ingénieur*, la première en tête de la Bibliothèque | Logo de son employeur sur les vêtements : marque d'une entreprise réelle, non reproduite ; portrait photographique : hors du style dessiné |
| 14 | Couleur du couvre-chef | Couleur propre (`hat_color`) au lieu de la couleur d'accent : casque blanc et sweat rouge ensemble | Couleur d'accent partagée : impossible d'avoir un casque blanc sur un sweat rouge |
| 15 | « Trop cartoonesque » (retour du porteur sur l'adulte stylisé, 2026-10-31) | Troisième choix de **Proportions** : **Réaliste (illustration)**, dessiné par un module séparé (`rendering/realiste.py`) : aucun trait de contour, volumes par dégradés (lumière en haut à gauche), proportions d'adulte (environ sept têtes), visage anatomique (amande avec paupières et plis, iris, nez large avec ailes et narines, lèvres en deux tons, barbe et cheveux crépus texturés), mains à doigts, membres effilés ; **aucun signe de bande dessinée**, seules les larmes et la sueur, réelles, sont dessinées. Même catalogue (22 émotions, 10 poses, 11 tenues, coiffures, barbes, lunettes, couvre-chefs, regard, miroir) et même repère 400 × 560 : rien ne change pour l'Inspecteur, les images clés ni l'export. Les trois fiches *ingénieur* passent en réaliste ; le modèle *Dialogue* met ses deux interlocuteurs dans ce style | Retoucher l'adulte stylisé : il garde les contours épais et la tête du chibi, cause de l'effet « dessin animé » ; portrait photographique ou IA générative : hors du dessin vectoriel déterministe et sans provenance garantie ; supprimer chibi et adulte stylisé : d'autres fiches les utilisent et le porteur a demandé de garder les chibis |
| 16 | `clipPath` | Non géré par QtSvg : les paupières sont des masques remplis du dégradé de peau (en coordonnées du repère, donc raccord avec le visage) et l'intérieur de la bouche est borné par les courbes des lèvres | `clipPath` : les dents et les iris débordaient à l'écran |

## Conséquences

- Nouveau type **Personnage** (`character`), 9 variantes, trois styles de dessin (chibi, adulte stylisé, réaliste), 1 modèle, 1 rubrique d'aide ; schéma additif (un ancien projet n'a aucun personnage).
- Limites écrites dans l'aide : pas de synchronisation labiale automatique, pas de suivi caméra, pas de 3D, pas d'import d'un personnage découpé en pièces.
- Suite possible, déjà proposée au porteur : bouche synchronisée sur la voix (Rhubarb Lip Sync, MIT), puis personnages 3D VRM et suivi caméra (MediaPipe).
