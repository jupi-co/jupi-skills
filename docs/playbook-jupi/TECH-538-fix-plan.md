# TECH-538 — Plan de fix du feedback bout-en-bout (registre du 28 août)

Ticket : [TECH-538](https://linear.app/jupi-co/issue/TECH-538/feedback-du-test-de-bout-en-bout-registre-28-aout) · Priorité : High
Décisions de design validées par Robin le 28 août (§2) · Ticket Decide associé : [JUPI-604](https://linear.app/jupi-co/issue/JUPI-604/entite-playbook-lien-decision-playbook-linkedplaybook)

Deux écarts relevés pendant le test de bout en bout, à transformer en fixes ciblés :

- **F1** — les rapports des skills sont du charabia pour l'utilisateur (IDs de dossiers, stages, clusters, tripwires) ; il manque la couche « version utilisateur du rapport » que Proactive avait résolue dans son `REPORTING.md`.
- **F2** — les décisions créées ne se lisent pas comme des décisions (titres `[BR] …` au lieu d'une question), et rien ne les rattache au playbook (pas de nom de playbook, pas de lien).

Ce plan couvre le périmètre plugin (`plugins/playbook-jupi/`). Les suites hors repo sont en [§6](#6--suites-hors-périmètre).

---

## 1 · État des lieux (ce que le code fait aujourd'hui)

### F1 — le reporting

- Le rapport d'`act-or-decide` est défini dans [SKILL.md § Reporting](../../plugins/playbook-jupi/skills/act-or-decide/SKILL.md) : une table technique **dossier · stage · next step · verdict (ACT rule_ref / DECIDE link / WAIT / tripwire)**, puis Deferred, la checklist Handoffs, les événements guardrail et un footer `mode · decisionBudget`. Aucune version en langage humain n'est spécifiée.
- Les déclencheurs fins relaient tel quel : [go](../../plugins/playbook-jupi/skills/go/SKILL.md) « return the skills' own reports », [process-reply](../../plugins/playbook-jupi/skills/process-reply/SKILL.md) « return the planner's verdict… the decision link, the draft trace ». Le charabia du planner devient donc la sortie de `/go` et de « traite cette réponse ».
- Les deux prompts de routines ([routine-prompts.md](../../plugins/playbook-jupi/skills/setup-playbook-jupi/reference/routine-prompts.md)) ne disent **rien** du message final : le résumé qu'un run planifié laisse à l'utilisateur est aujourd'hui la concaténation des rapports techniques des trois skills invoqués.
- Le précédent à recréer existe dans ce repo : [proactive REPORTING.md](../../plugins/proactive-jupi/skills/act-or-decide/reference/REPORTING.md), section *« The user's version of this report — yours to define, wherever it's shown »*. Ses règles éprouvées : mêmes blocs que le run log mais dits avec des mots humains, **nommer l'artefact** (« un brouillon prêt dans Gmail »), le conditionnel partout en `--dry-run`, « jamais un rapport plus court pour l'humain que pour le log », les chiffres seulement quand ils changent ce que la personne ferait. Ce fichier a été volontairement laissé de côté au fork — c'est la couche à reconstruire côté playbook, en dossier-centrique.

### F2 — les décisions

- Le préfixe `[BR]` vient de proactive ([act-or-decide SKILL.md:439](../../plugins/proactive-jupi/skills/act-or-decide/SKILL.md) : « the prefix marks it in the log and the poll ») et a été repris par les templates playbook ([decision-templates.md](../../plugins/playbook-jupi/skills/act-or-decide/reference/decision-templates.md)) : template 1 `[BR] <scope value>: <question>`, template 2 `[BR] <parameter>: set the value`, template 5 `[BR] Amend <point>@<scope>`.
- **Le supprimer des titres est mécaniquement sûr** : la détection d'une décision « échelle règle » au settle ne parse jamais le titre. `act-post-decision` et `execute-action` (copies synchronisées de proactive) reconnaissent l'option-action *business-rule-update* **par son champ `tool`**, pas par le préfixe — les mentions « `[BR]`-titled » dans ces copies sont descriptives.
- **L'API Jupi n'a pas de rattachement** — vérifié sur le schéma de `create-decision-tool` : `title`, `description`, `deadline`, `groupSlug`, `ownerId`, `makerId`, `allowWorkspaceContributions`… ni tags ni lien playbook. Le rattachement structurel est le chantier Decide ([JUPI-604](https://linear.app/jupi-co/issue/JUPI-604/entite-playbook-lien-decision-playbook-linkedplaybook)) ; côté plugin, en attendant, le rattachement est **humain** : le contexte de la décision nomme le playbook (§4.1).
- **`playbookName` n'existe nulle part** (grep sur plugins/, evals/, tools/) : ni clé de config, ni entrée, ni question au setup. Le prelude de [setup-playbook-jupi](../../plugins/playbook-jupi/skills/setup-playbook-jupi/SKILL.md) liste `jupiWorkspace · jupiUserId · neonConnString · dossierSource · playbookSources · projectionTarget · inboundStage`.
- Point favorable : le validator ([VALIDATOR.md](../../plugins/playbook-jupi/skills/act-or-decide/reference/VALIDATOR.md), copie synchronisée) exige déjà « plain language, no unexplained jargon » et l'orchestration a déjà une passe « PLAIN-LANGUAGE » — c'est le template playbook qui contredit ces gates en imposant `[BR]`. Le fix supprime une contradiction interne plutôt qu'il n'ajoute une règle.

---

## 2 · Décisions de design — validées le 28 août

> Loggées dans Jupi comme décisions finalisées à la validation de ce plan (règle du repo).

### D1 ✅ — Le nom du playbook vit dans une **entrée réservée `playbook-name`**

Précédent `lifecycle-stages` : `point_id='playbook-name'`, scope `'global'`, `answer` = le nom, `status: 'declared'`, provenance « owner, setup prelude » (ou « titre du doc, confirmé par l'owner »). Raisons : c'est du contenu playbook (règle de vocabulaire du [contrat](../../plugins/playbook-jupi/shared/playbook-contract.md)) ; renommer = un upsert, sans rejouer le scheduling des routines (le nom n'entre pas dans la config portée) ; le planner l'a gratuitement (son boot lit déjà `pb-list-entries` en entier).

Dégradé gracieux : entrée absente (workspace existant pas re-bootstrappé) → le planner écrit « ce playbook » et signale l'entrée manquante dans son rapport — un nom manquant ne bloque jamais un run.

**Volet Decide (validé avec D1)** : les playbooks deviennent une entité côté Jupi — table `playbook` + prop `linkedPlaybook` (ou similaire) sur Decision → ticket [JUPI-604](https://linear.app/jupi-co/issue/JUPI-604/entite-playbook-lien-decision-playbook-linkedplaybook) (créé, lié à TECH-538).

### D2 ✅ — **Pas de convention intérimaire** : lien d'entité direct

L'idée d'une ligne d'origine parsable en tête de description est **abandonnée** (« non surtout pas ») : on implémente directement le lien structurel — `Decision.agentId` / `linkedPlaybook` — côté Decide ([JUPI-604](https://linear.app/jupi-co/issue/JUPI-604/entite-playbook-lien-decision-playbook-linkedplaybook), à articuler avec le chantier §16-B5). Conséquences côté plugin :

- Les templates ne mettent **aucun marqueur machine** dans la description. Le rattachement lisible reste dans le **contexte**, en langage humain : la première sous-section commence par « Dans le cadre du playbook « \<nom\> », … » — c'est le besoin « le contexte ne dit pas qu'on est dans le cadre du playbook » du ticket, couvert dès maintenant.
- Quand `create-decision-tool` exposera le paramètre (sortie de JUPI-604), un **follow-up plugin** le passera à la création — une ligne dans Stage 4 du planner, rien d'autre à re-designer.

### D3 ✅ — On ne touche pas à proactive

Les titres `[BR] When X, always Y` de proactive ont le même défaut UX, mais y toucher entraîne trois fichiers synchronisés à re-copier et trois suites d'évals proactive qui assertent `[BR]`. Le pilote tourne sur playbook : on fixe playbook dans ce ticket ; l'harmonisation proactive est un ticket séparé, à ouvrir quand on y reviendra. D'ici là, les mentions « `[BR]`-titled » dans les copies synchronisées restent — descriptives et sans effet mécanique.

### D4 ✅ — Chaque skill définit sa version utilisateur, l'orchestrateur les coud

Règle proactive conservée (« that version is yours, not the caller's ») : `act-or-decide` et `refresh-backlog` (les deux skills playbook que l'utilisateur lit) définissent chacun leur version utilisateur ; les orchestrateurs (`go`, `process-reply`, les deux routines) **cousent ces versions en un seul récit** — jamais trois rapports empilés — et gardent le détail technique en narration/sur demande. `act-post-decision` (copie synchronisée) n'est pas modifié : son résumé 4–6 lignes est une entrée pour l'orchestrateur, qui le reformule.

### D5 ✅ — Une persona « assistant » porte la version utilisateur

Ajout de Robin : la version utilisateur est écrite depuis une persona d'**assistant qui rend compte à son responsable**. Ce qui compte, dans l'ordre : la **clarté** des réponses, la bonne **communication de ce qui a été fait**, et **éviter d'être trop verbeux**. La persona est spécifiée une fois dans le REPORTING.md playbook (§3.1) et vaut pour toutes les surfaces — c'est elle qui donne le ton, les blocs donnent le contenu.

### D6 ✅ — Un canal technique pour le debugging

Ajout de Robin : prévoir un mécanisme où on communique avec le **vocabulaire technique**. Design (§3.1.D) : le run log technique est **toujours produit** (il précède la version utilisateur dans la narration) ; un flag `--technical` sur les invocations fait du run log le message final ; en conversation, « montre-moi le détail technique » le re-rend à la demande. Les évals et le bench continuent donc de lire les tables exactes.

---

## 3 · Chantier F1 — la couche « version utilisateur du rapport »

### 3.1 Nouveau fichier : `plugins/playbook-jupi/skills/act-or-decide/reference/REPORTING.md`

Fichier **playbook-owned** (pas d'en-tête « synced » — le contenu est dossier-centrique, différent de proactive). Quatre parties :

**A. Le run log** (les blocs techniques actuels, déplacés depuis SKILL.md et gardés tels quels — c'est notre log, celui du bench et des routines) :
la table dossiers · Deferred · ☐ Handoffs · événements guardrail · footer.

**B. La version utilisateur — l'affichage par défaut.** Ouvre sur la persona (D5) :

> Tu rends compte comme un **assistant** à la personne pour qui tu travailles : clair, direct, factuel. La priorité — qu'elle comprenne en une lecture **ce qui a été fait**, **ce qui l'attend**, **ce qui est de son côté**. Peu verbeux : l'essentiel seulement.

Quatre blocs, mêmes contenus que le log, autres mots :

1. **Ce qui a avancé** — une phrase par dossier, **par son label** (« Pour *Alpha*, on a identifié le contact » — jamais d'ID, jamais de stage). Nommer l'artefact : « un brouillon de réponse t'attend dans Gmail ». Vide = le dire en une ligne.
2. **Décisions qui t'attendent** — le titre tel qu'il se lit dans Jupi (une question, cf. F2), **le lien cliquable**, ce que ça débloque (« ça débloque aussi 2 autres comptes »). Jamais compressé en compteur.
3. **À toi de jouer** — la checklist des handoffs, une ligne par item : qui · quoi · ce que Jupi a préparé et où. (Reprend l'exemple du ticket : « Il reste à trouver le contact pour *Beta* — c'est de ton côté. »)
4. **Laissé pour la suite** — les reports/coupes, et **dire si une limite en est la cause** (« je m'arrête à 5 décisions par run ; 6 qualifiaient »).

Règles transverses (héritées du REPORTING.md proactive, adaptées) :

- **Langue de l'utilisateur** — celle des documents du playbook (en pratique : celle de l'owner), pas celle des skills.
- **Vocabulaire interdit** dans la version utilisateur : id de dossier, stage, cluster, tripwire, residue, ACT/DECIDE, rule_ref, entry, point, `[BR]`. Un tripwire se dit « j'ai stoppé net et je te demande » ; un out-of-script « ce mail sort du cadre prévu, voilà la question ».
- **Peu verbeux, l'essentiel seulement** : phrases courtes ; chiffres seulement quand ils changent ce que la personne ferait.
- **`--dry-run` = conditionnel partout** (« ce que je ferais », « les décisions que je te poserais ») — rien n'a été fait, le rapport ne s'attribue rien.
- **Jamais plus court pour l'humain que pour le log** : les blocs 3 et 4 sont obligatoires même vides (une ligne).
- **Clore sur la posture, pas la config** : « Je suis en mode brouillon — rien ne part sans toi. »

**C. La règle de composition pour les orchestrateurs** : coudre les versions utilisateur des skills invoqués en **un seul** récit dans l'ordre 1→4 (dédupliquer les dossiers touchés par plusieurs skills), le message final du run = cette version cousue. Le résumé d'`act-post-decision` (copie synchronisée, non modifiée) est reformulé par l'orchestrateur dans le bloc 1.

**D. Le canal technique (D6)** : le run log précède toujours la version utilisateur dans la narration du run — rien n'est perdu. `--technical` sur l'invocation (accepté par `act-or-decide`, passé à travers par `go`/`process-reply` comme `--dry-run`) → le message final **est** le run log. En conversation, « montre-moi le détail technique » re-rend le run log du run courant. Les routines n'ont pas de switch : debugger une routine = ouvrir son transcript, où le run log est déjà.

### 3.2 Éditions dans les fichiers existants

| Fichier | Édition |
|---|---|
| [act-or-decide/SKILL.md](../../plugins/playbook-jupi/skills/act-or-decide/SKILL.md) | § Reporting réduit à un pointeur vers `reference/REPORTING.md` + la règle « la version utilisateur est le message final par défaut ; le run log la précède en narration ». § Run args : ajouter `--technical`. § Narrate + return aligné. |
| [refresh-backlog/SKILL.md](../../plugins/playbook-jupi/skills/refresh-backlog/SKILL.md) | § Narrate + return : ajouter la version utilisateur (« 2 réponses rattachées : *Alpha* (de X), *Beta* (de Y) ; 1 mail que je n'ai pas su rattacher : expéditeur · objet ») — le résumé technique (curseur, fenêtre, confidences) passe en narration. |
| [go/SKILL.md](../../plugins/playbook-jupi/skills/go/SKILL.md) (étape 4) | « return the skills' own reports » → rendre la **version utilisateur cousue** (REPORTING.md §C), checklist handoffs incluse ; `--technical` passe à travers. |
| [process-reply/SKILL.md](../../plugins/playbook-jupi/skills/process-reply/SKILL.md) (étape 6) | Même bascule : le verdict du dossier en langage humain (la question posée + lien, ou « brouillon prêt », ou la ligne handoff) ; `--technical` passe à travers. La question d'outcome (étape 5) est déjà en langage humain — inchangée. |
| [routine-prompts.md](../../plugins/playbook-jupi/skills/setup-playbook-jupi/reference/routine-prompts.md) | Ajouter aux **deux** templates une consigne finale : « Termine par la version utilisateur du rapport (règles : `reference/REPORTING.md` d'act-or-decide, §version utilisateur — persona assistant), dans la langue de l'utilisateur ; les rapports techniques restent dans la narration du run. » Formulation intemporelle (règle du fichier : un prompt est écrit une fois et lu pour toujours). |

### 3.3 Ce que F1 ne touche pas

`act-post-decision` et `execute-action` (copies synchronisées — fork policy, D3) ; `update-brain` ; le rapport de **setup** (narration ✅/🔧/⚠️ attendue, run attendu avec l'owner — hors du grief « résumés de runs »).

---

## 4 · Chantier F2 — des décisions qui se lisent comme des décisions, rattachées au playbook

### 4.1 `decision-templates.md` — titres = questions, `[BR]` sorti, rattachement dans le contexte

**Mécaniques partagées** (le bloc du haut), ajouter :

- **Règle de titre** : le titre est **la question à trancher**, en langage naturel, dans la langue de l'utilisateur, sans crochet/code/id — le scope dit avec des mots, pas en `clé=valeur`. Une décision d'échelle règle ne se signale **pas** dans le titre : c'est la formulation des options qui le porte (« Toujours faire X (devient la règle) » vs « Juste cette fois »).
- **Rattachement** : la première sous-section du contexte commence par « Dans le cadre du playbook « \<nom\> », … » (le nom vient de l'entrée `playbook-name`, D1). **Aucun marqueur machine** dans la description (D2) — le lien structurel arrivera par l'API ([JUPI-604](https://linear.app/jupi-co/issue/JUPI-604/entite-playbook-lien-decision-playbook-linkedplaybook)).

**Par template** (avant → après ; les exemples pilotes restent des illustrations, pas le vocabulaire) :

| Template | Avant | Après |
|---|---|---|
| 1 · Scoped-rule, 1ʳᵉ instance | `[BR] <scope value>: <question>` | La question du point instanciée au scope, formulée comme une vraie question — ex. « Peut-on contacter directement les interlocuteurs de *<partenaire>* ? » |
| 2 · Parameter | `[BR] <parameter>: set the value` | « Quel(le) <paramètre> retenir ? » — ex. « Combien de temps attendre avant la relance ? » |
| 3 · Asset | *(pas de titre spécifié)* | Expliciter : « Quel <asset> utiliser pour <contexte> ? » — ex. « Quel message envoyer à *<partenaire>* pour la première prise de contact ? » |
| 4 · Out-of-script | *(pas de titre spécifié)* | Expliciter : « Que répondre quand <la situation> ? » — l'exemple du ticket : « Que répondre quand on nous indique que ce n'est pas la bonne personne ? » |
| 5 · Amendment | `[BR] Amend <point>@<scope>` | « La règle « quand X, toujours Y » tient-elle encore pour <scope> ? » (ou « Faut-il amender… ? ») |

**Renommage interne** : dans les fichiers playbook-owned, « `[BR]` » → « décision d'échelle règle » (*rule-scale decision*), avec une note unique « anciennement noté `[BR]` ; le marqueur ne va plus jamais dans un titre ». Occurrences : [decision-templates.md](../../plugins/playbook-jupi/skills/act-or-decide/reference/decision-templates.md) (×3), [act-or-decide/SKILL.md](../../plugins/playbook-jupi/skills/act-or-decide/SKILL.md) Stage 4 (×1), [process-reply/SKILL.md](../../plugins/playbook-jupi/skills/process-reply/SKILL.md) étape 5 (×1), [playbook-contract.md](../../plugins/playbook-jupi/shared/playbook-contract.md) (×2, descriptives). Les copies synchronisées ne bougent pas (D3).

### 4.2 Le nom du playbook (D1) — setup, contrat, projection, planner

| Fichier | Édition |
|---|---|
| [setup-playbook-jupi/SKILL.md](../../plugins/playbook-jupi/skills/setup-playbook-jupi/SKILL.md) | **Prelude** : nouvelle question front-loadée — proposer un nom extrait des `playbookSources` (titre du doc principal), le faire confirmer/corriger par l'owner ; re-run avec entrée existante → afficher le nom courant, confirmer. **Extraction** : écrire l'entrée réservée `playbook-name` (D1) avec sa provenance. **Report** : énoncer le nom. |
| [playbook-contract.md](../../plugins/playbook-jupi/shared/playbook-contract.md) | Documenter l'entrée réservée à côté de `lifecycle-stages` (petite section « entrées réservées » : `lifecycle-stages`, `playbook-name`, familles `tripwire-*`). |
| Projection (section §Projection du setup) | Le nom devient le **H1** du document projeté (« Playbook « \<nom\> » ») — première ligne que l'owner lit. |
| [act-or-decide/SKILL.md](../../plugins/playbook-jupi/skills/act-or-decide/SKILL.md) | Boot : le nom est dans le `pb-list-entries` déjà lu ; Stage 4 : l'utiliser dans le rattachement du contexte (§4.1). Absent → « ce playbook » + signalement dans le rapport, jamais bloquant. |
| [routine-prompts.md](../../plugins/playbook-jupi/skills/setup-playbook-jupi/reference/routine-prompts.md) | Nice-to-have : les champs `description` des deux routines portent le nom (« Jupi fait avancer le playbook « \<nom\> »… »). Les **noms techniques** des routines restent fixes (le reconcile matche dessus). |

Aucun changement `playbook.mjs`/schéma : l'upsert ordinaire suffit (même mécanique que `lifecycle-stages`).

### 4.3 Vérifs de non-régression spécifiques

- Une décision d'échelle règle **sans** `[BR]` au titre se settle toujours correctement : la reconnaissance au settle est par option-action (`tool`), vérifiée dans les copies synchronisées — à re-tester sur le banc (un settle de bout en bout après le fix).
- Le validator (copie synchronisée, intouchée) ne référence pas `[BR]` : ses gates « plain language » passent mieux après le fix, rien à changer.

---

## 5 · Évals et validation

| Suite | Édition |
|---|---|
| [evals/playbook-jupi/act-or-decide/evals.json](../../evals/playbook-jupi/act-or-decide/evals.json) | Cases 1–2 (et toute autre mention) : « exactly 2 [BR] decisions » → « exactly 2 rule-scale decisions » + nouvelles expectations : *titres = questions en langage naturel, aucun crochet/code/id* ; *le contexte rattache au playbook par son nom* ; *aucun marqueur machine dans la description*. Ajouter des expectations de reporting sur les cases dry-run existantes (le rapport se termine par la version utilisateur — ton d'assistant, phrases complètes, brève ; sans id de dossier ni « stage/cluster/tripwire » ni `[BR]` ; handoffs en une ligne par item) — ou une case dédiée si ça surcharge. Une expectation `--technical` : le message final est la table technique. |
| [evals/playbook-jupi/setup-playbook-jupi/evals.json](../../evals/playbook-jupi/setup-playbook-jupi/evals.json) | Case 1 : + « l'entrée `playbook-name` existe (declared, provenance) » et « la projection est titrée par le nom ». Case 3 (idempotence) : le nom n'est pas dupliqué/écrasé silencieusement. |
| [evals/playbook-jupi/refresh-backlog](../../evals/playbook-jupi/refresh-backlog/evals.json) | Vérifier les expectations de résumé ; aligner si elles citent le format technique. |
| Hygiène repo | `claude plugin validate` (catalogue + les plugins) + `tools/validate-plugin.sh` (les descriptions de skills ne changent pas — pas de risque XML/1024). |
| Banc (repo externe) | Rejouer le scénario du 28 août : mêmes actes, vérifier titre + rattachement-contexte des décisions créées et la sortie utilisateur de `/go` et d'un run de routine ; un run `--technical` pour le canal debug. Mettre à jour ce que le banc asserte en `[BR]` le cas échéant. |

---

## 6 · Suites hors périmètre

1. **[JUPI-604](https://linear.app/jupi-co/issue/JUPI-604/entite-playbook-lien-decision-playbook-linkedplaybook)** *(créé le 28 août, lié à TECH-538)* — côté Decide : table `playbook`, prop `linkedPlaybook` (ou similaire, à articuler avec `Decision.agentId` §16-B5), exposition dans `create-decision-tool`, affichage UI. Pas d'intérim côté plugin (D2).
2. **Follow-up plugin** (bloqué par JUPI-604) : passer le lien playbook à la création des décisions dès que `create-decision-tool` expose le paramètre — une ligne dans Stage 4 du planner.
3. **Ticket proactive-jupi** (à ouvrir plus tard, D3) : harmonisation des titres, gate de titre dans VALIDATOR.md upstream, re-copie des trois fichiers synchronisés, évals proactive.
4. **Mise en service pilote** (post-merge, un run attendu) : re-run de setup sur le workspace pilote — le prelude confirme le nom (nouvelle entrée), l'étape scheduling met à jour **en place** les deux routines (nouvelle consigne de rapport + descriptions) ; même geste que la rotation de `neonConnString`, prévu par le design.
5. **Décisions D1–D6 loggées dans Jupi** à la validation du plan (28 août), en deux enregistrements finalisés : [couche rapport (D4+D5+D6)](https://jupi.co/jupi/decision/rapports-playbook-jupi-version-utilisateur-par-skill-persona-assistant-technique-sur-demande-0bab4f2f-e175-4f75-b1af-da4ea4855818) et [nommage/rattachement (D1+D2+D3)](https://jupi.co/jupi/decision/nom-du-playbook-en-entr-e-r-serv-e-rattachement-des-d-cisions-par-entit-decide-pas-d-int-rim-texte-2d9f7377-8e3d-4830-a4b1-c4e51b07df48).

## 7 · Découpage en PR

- **PR-A · F1 — la couche rapport utilisateur** : nouveau `REPORTING.md` (persona assistant + canal `--technical` inclus) + les 5 éditions §3.2 + expectations de reporting. Indépendante, testable en dry-run pur.
- **PR-B · F2 — décisions nommées et rattachées** : templates + renommage `[BR]` + entrée `playbook-name` (setup, contrat, projection, planner, routines-descriptions) + évals §5. Rebase sur A (les deux touchent `act-or-decide/SKILL.md`, sections disjointes).

Ordre indifférent sur le fond ; A d'abord parce que chaque run du pilote la rend visible immédiatement. Les deux sont shippables seules (`main` = shipping).

## 8 · Hors périmètre assumé

- Le câblage exact de l'exécution du *rule write* (`pb-upsert-entry` porté par une option-action) au settle — tension préexistante entre `decision-templates.md` (« executed by act-post-decision ») et les copies synchronisées (routage par `execute-action`) : à instruire au premier settle réel sur le banc, ticket séparé si ça casse. Ce fix n'y touche pas et ne l'aggrave pas.
- L'implémentation de l'entité Playbook / `Decision.agentId` — c'est [JUPI-604](https://linear.app/jupi-co/issue/JUPI-604/entite-playbook-lien-decision-playbook-linkedplaybook), côté Decide.
- Les rapports de `update-brain` et du setup (narration attendue, pas un « résumé de run »).
