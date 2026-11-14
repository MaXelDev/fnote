# Ce que les utilisateurs détestent et réclament : pièges à éviter pour Plume

**Échantillon : 52 avis réels, 4 sources** (`reviews.csv`, classement brut dans `feedback.md`).
- 23 tickets GitHub de Rnote, 19 de Xournal++ (les plus votés sur la fluidité, le stylet, le PDF, le surligneur, la gomme et les formes) ;
- 8 commentaires Hacker News (via l'API Algolia) ;
- 2 messages de la communauté Samsung.

**Limites, à dire franchement :**
- **Samsung Notes est peu couvert.** Les avis du Play Store et du Microsoft Store ne se lisent pas par une API autorisée, et deux des trois fils de la communauté Samsung ne se chargent pas (contenu tronqué). Les complaintes sur Samsung Notes viennent donc surtout de ton propre cahier des charges (§1).
- **AirNote est introuvable.** Je n'en ai trouvé aucun avis exploitable : seule une fiche AlternativeTo existe, et elle le décrit comme un outil appuyé sur l'API Gemini, donc en ligne. Il n'est pas analysé.
- **Les tickets GitHub n'ont pas d'étoiles.** Les votes 👍 servent d'indicateur de demande.

Les citations sont en version originale et exacte, avec leur lien.

---

## 1. Ce qu'ils détestent

1. **Encre lente ou saccadée.** 11 avis, 4 sources. C'est le cœur de ton critère n°1.
   - « writing with pen became very slow, making it impossible to take quick notes. » ([Samsung](https://community.samsung.com/us/conversations/Tablets/ISSUE-LAG-ON-SAMSUNG-NOTE-WHILE-WRITING-AFTER-UPDATE/us_3067297))
   - « When drawing fast with a high latency device, we can see the line segments forming the stroke » ([Xournal++ #2578](https://github.com/xournalpp/xournalpp/issues/2578))
   - « Pen input (Apple Pencil) is quite choppy, because browsers tend to coalesce multiple pen events together, effectively reducing the pen's polling rate. » ([HN](https://news.ycombinator.com/item?id=43884012)). C'est exactement ce que corrige `AA_CompressTabletEvents = False`.
2. **Zoom lent dès qu'il y a beaucoup de traits.** Thème mince : 1 avis, 1 source, mais le mécanisme est connu.
   - « It should probably scale the canvas itself without redrawing the picture until the gesture is done » ([Rnote #7](https://github.com/flxzt/rnote/issues/7))
3. **Curseur et pointeur.** 8 avis, 3 sources.
   - « Instead of a tiny pointer/eraser/other tool showing as the pointer, it continues to show the OS mouse pointer. » ([HN](https://news.ycombinator.com/item?id=38105971))
   - « Sometimes random lines from stylus position to last position mouse pointer appear. » ([Rnote #1440](https://github.com/flxzt/rnote/issues/1440))
   - « When scaling is set to 200%, the cursor is offset from where the mouse actually is. » ([Rnote #338](https://github.com/flxzt/rnote/issues/338))
4. **Stylet, pression ou tactile mal reconnus.** 22 avis, 4 sources. C'est le thème le plus cité.
   - « Unable to draw when using tablet stylus, despite pen-{down,up} events being detected » ([Rnote #1543](https://github.com/flxzt/rnote/issues/1543))
   - « Tablet pressure information seems to be ignored. » ([Rnote #194](https://github.com/flxzt/rnote/issues/194))
   - « Pinch-to-zoom on the screen itself causes sudden jumps. » ([Rnote #1738](https://github.com/flxzt/rnote/issues/1738), GNOME)
5. **Surligneur dont l'opacité n'est pas uniforme.** 2 avis, 1 source, donc mince, mais très visible à l'usage.
   - « Currently using translucent brush leaves weird circles that can be very close or very far from each other making line opacity very inconsistent and ugly. » ([Rnote #106](https://github.com/flxzt/rnote/issues/106))
   - « it isn't homogenously transparent, but rather leaves little circles where its less transparent. » ([Rnote #891](https://github.com/flxzt/rnote/issues/891))
6. **Gomme qui rate des traits quand on va vite.**
   - « Erasing faster skips some strokes. » ([Rnote #1247](https://github.com/flxzt/rnote/issues/1247))
7. **Outils éparpillés dans plusieurs barres.**
   - « There are three different bars (top, bottom, and side), and you often need to move your mouse/hand to all of them » ([HN](https://news.ycombinator.com/item?id=41351806))

## 2. Ce qui manque (demandé nommément)

| Demande | Votes / sources | Citation |
|---|---|---|
| Règle et rapporteur | Rnote #147 (20 👍) | « a ruler to draw straight lines (like in Onenote) » ([lien](https://github.com/flxzt/rnote/issues/147)) |
| Reconnaissance de formes / redressement en maintenant le stylet | Rnote #384 (12 👍), [Rnote #120](https://github.com/flxzt/rnote/issues/120) (22 👍) | « after ~1s a straight stroke is drawn from the stroke starting point » ([lien](https://github.com/flxzt/rnote/issues/384)) |
| Surligneur droit | Xournal++ #1771 (25 👍) | « I would like to draw straight lines with the highlighter to reduce visual clutter. » ([lien](https://github.com/xournalpp/xournalpp/issues/1771)) |
| Surligneur qui marche sur le PDF de fond | Rnote #449 (53 👍) | « it doesn't work well on PDFs. » ([lien](https://github.com/flxzt/rnote/issues/449)) |
| Annotation de PDF | Rnote #153 (60 👍) | ([lien](https://github.com/flxzt/rnote/issues/153)) |
| Garder le texte du PDF sélectionnable | Xournal++ #1745 (78 👍) | « select text from the PDF, copy it, and paste it into another program » ([lien](https://github.com/xournalpp/xournalpp/issues/1745)) |
| Ajouter de l'espace sous un passage du PDF | Xournal++ #1698 (26 👍) | « there is not enough space for my notes in the PDF » ([lien](https://github.com/xournalpp/xournalpp/issues/1698)) |
| Recadrer et pivoter les images | Xournal++ (37 + 31 👍) | ([recadrage](https://github.com/xournalpp/xournalpp/issues/1842), [rotation](https://github.com/xournalpp/xournalpp/issues/918)) |
| Export PDF automatique à côté de la note | Rnote #1312 (8 👍) | « autosave in multiple formats, for example in both rnote and PDF » ([lien](https://github.com/flxzt/rnote/issues/1312)) |
| Outil temporaire en maintenant un bouton | Xournal++ #2310 (32 👍) | « switching tools for common operations (panning and zooming) breaks the flow » ([lien](https://github.com/xournalpp/xournalpp/issues/2310)) |
| Lissage du trait | Xournal++ #2320 | « I have a very shaky hand, even more on a tablet than on paper. » ([lien](https://github.com/xournalpp/xournalpp/issues/2320)) |

## 3. Ce qui n'est pas résolu (besoins entiers que les applis ignorent)

- **L'étudiant sous Linux avec un PC convertible et stylet**, comme toi. Les alternatives libres fonctionnent (« Xournalpp works ok », [HN](https://news.ycombinator.com/item?id=50279903)) mais demandent des contournements (un bug de mutter à patcher), et aucune n'est pensée d'abord pour ce matériel sous GNOME/Wayland. Thème mince : 2 avis.
- **Le lien avec un vault de notes (Obsidian).** Personne ne le demande nommément, mais l'export PDF automatique (Rnote #1312) en est le besoin sous-jacent.

---

## 4. Plan de correctifs (intégré à `features.csv`, avec `original` = `no`)

| # | Correctif | Taille | Phase / skill | Preuve |
|---|---|---|---|---|
| 1 | Pendant le pincement ou le zoom, on affiche le cache bitmap mis à l'échelle et on ne redessine net qu'à la fin du geste | S | 1 · replica-build | Rnote #7 |
| 2 | Une fois le stylet en proximité, la position de la souris est ignorée, et un trait commence toujours à la position du stylet | S | 1 · replica-build | Rnote #1440 |
| 3 | Coordonnées correctes à 125, 150 et 200 % de mise à l'échelle Wayland : positions en flottant, pas d'arrondi en pixels logiques | S | 1 · replica-build | Rnote #338 |
| 4 | Gomme : on teste le **segment** entre deux échantillons, pas seulement les points, pour qu'aucun trait ne soit sauté | S | 2 · replica-build | Rnote #1247 |
| 5 | Surligneur dessiné comme **un seul chemin**, rempli une fois puis composé en multiply, donc sans « petits cercles » | S | 2 · replica-build | Rnote #106, #891 |
| 6 | Tous les outils et réglages dans **une seule barre** en haut ; les réglages s'ouvrent dans un popover sous l'outil | M | 2 · replica-design | HN 41351806, 38105971 |
| 7 | La fenêtre `--debug-tablet` affiche aussi l'échelle de l'écran et le décalage pointeur/stylet, pour diagnostiquer avant de coder | S | 0 · replica-build | Rnote #1543, #338 |
| 8 | Le surligneur reste au-dessus du fond PDF mais sous l'encre, et le texte du PDF reste sélectionnable à l'export | — | déjà must, 2 et 5 | Rnote #449, Xournal++ #1745 |

**Priorités ajustées dans la matrice :**
- « Surligneur droit » passe de should à **must** (25 👍, et le surligneur est ton outil principal) ;
- « Images : recadrage simple » passe de could à **should** (37 👍) ;
- « Lasso : pivoter » reste should.

**Hors périmètre, confirmé :** reconnaissance d'écriture (16 à 25 👍 côté Xournal++ et Rnote, mais exclue par §7.12), collaboration, appli mobile.

## 5. Pièges à éviter (résumé)

1. **Ne pas redessiner toute la scène** au zoom ni pendant le tracé.
2. **Ne jamais laisser la souris « voler » le point de départ** d'un trait au stylet.
3. **Ne pas peindre le surligneur point par point**, sinon l'opacité s'accumule.
4. **Gomme : intersection de segments**, pas de simples distances entre points.
5. **Ne pas présupposer que Wayland transmet pression et proximité.** On vérifie d'abord avec `--debug-tablet`, sur ta machine.
6. **Ne pas éparpiller les outils** : une barre, gros boutons, réglages en popover.

## Angle

Le positionnement commercial est ignoré, comme demandé. Phrase directrice du projet :

> Pour l'étudiant qui écrit ses cours au stylet sous Fedora/Wayland et qui fuit les applis où l'encre traîne et où le curseur reste affiché, Plume écrit comme sur une feuille, annote ses PDF de cours et range tout dans son vault Obsidian.
