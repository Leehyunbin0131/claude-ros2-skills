<div align="center">

<img src="assets/hero.png" alt="claude-ros2-skills — Claude Code skills for ROS 2 Jazzy" width="100%"/>

**Claude Code Skills for ROS 2 Jazzy Jalisco robotics development.**

Des skills qui transforment la façon dont les agents IA abordent le développement ROS 2 : identifier les paramètres inconnus dès le départ, vérifier les configurations par rapport aux packages installés et confirmer l'exécution grâce à des preuves tangibles.

![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?logo=ubuntu&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | **Français** | [Deutsch](README.de.md)

<sub>🌐 Ce document est une traduction automatique. L'original est en [English](README.md).</sub>

| Skills | Protocole chargé en permanence | Liens de doc (vérifiés par CI) | Contrôles sur robot physique | Évals : Gazebo A/B |
| :---: | :---: | :---: | :---: | :---: |
| **11** | **26 lignes** | **38** | **4 scripts** | **objectif atteint vs. abandon au bringup** |

</div>

---

## Sommaire

- [Les échecs qui coûtent cher](#les-échecs-qui-coûtent-cher)
- [Comment ces skills sont conçus](#comment-ces-skills-sont-conçus)
- [Ce qui le différencie](#ce-qui-le-différencie)
- [Évaluations](#évaluations)
- [Démarrage rapide](#démarrage-rapide)
- [Skills](#skills)
- [Scripts de vérification](#scripts-de-vérification)
- [Fonctionnement](#fonctionnement)
- [Mise à jour](#mise-à-jour)
- [Feuille de route](#feuille-de-route)
- [Contribuer](#contribuer)
- [Licence](#licence)

## Les échecs qui coûtent cher

Les erreurs les plus coûteuses dans le code ROS 2 généré par IA sont rarement des fautes de syntaxe. Il s'agit plutôt de problèmes subtils qui semblent corrects à première vue :

| Échec | Ce que vous observez | Pourquoi l'agent rencontre ce problème |
| :--- | :--- | :--- |
| **Échec silencieux** | `ros2 topic hz` indique 30 Hz ; votre callback ne se déclenche jamais | Un subscriber par défaut en RELIABLE tente de se connecter à un publisher en BEST_EFFORT. Le code compile et passe la revue de code, mais échoue au niveau du middleware DDS. |
| **Vérité terrain erronée** | `/cmd_vel` indique une avance et `/odom` signale une avance, mais le robot physique se déplace **vers l'arrière** | Le repère (frame) TF statique est inversé par rapport au montage physique. Les composants en aval calculent correctement *en utilisant la mauvaise transformation*, sans produire d'erreur apparente. |
| **API obsolète** | Le code passe la revue mais échoue à l'exécution lors de l'appel d'une méthode incorrecte | L'agent utilise des méthodes d'API obsolètes de Foxy ou Humble qui ont été renommées ou supprimées dans Jazzy. |
| **Prémisse invalide** | L'agent écrit 200 lignes de code basées sur une hypothèse que vous auriez pu corriger en une seule phrase | Aucun mécanisme n'incite l'agent à vérifier les détails manquants avant de générer le code. |

Ni les compilateurs, ni les linters, ni les analyses de logs ne détectent ces problèmes cachés. La résolution de chaque erreur nécessite un cycle de retour supplémentaire : examiner le résultat, diagnostiquer la cause, expliquer le correctif et régénérer le code.

## Comment ces skills sont conçus

Quatre règles de conception régissent chaque skill de ce dépôt :

**1. Identifier les variables inconnues dès le départ.** Les détails opérationnels clés ne figurent souvent pas dans la documentation — par exemple si l'environnement est du matériel réel ou une simulation, s'il faut étendre un workspace existant ou en créer un nouveau, quel nœud publie déjà une transformation, ou la géométrie précise du robot. [`CLAUDE.md`](./CLAUDE.md) donne pour instruction à l'agent de clarifier ces inconnues avant de générer du code. Les skills spécifiques à un domaine gèrent les paramètres ciblés ; par exemple, `ros2-dev` demande le footprint du robot, la cinématique de transmission et la source de localisation avant de configurer les paramètres Nav2.

**2. Exécuter une boucle structurée avec des critères de sortie clairs.** Chaque skill suit un cycle *vérifier → écrire → prouver* : inspecter les valeurs par défaut du système sur l'environnement installé, appliquer des modifications incrémentales et confirmer l'exécution. Une tâche ne s'achève que lorsqu'elle s'appuie sur des preuves observées — comme un build réussi, des données actives sur `ros2 topic echo` ou le succès d'un script de vérification — et non simplement par la production de fichiers de code.

**3. Privilégier les tableaux d'échecs structurés aux longues descriptions.** Les tableaux structurés associant symptômes → causes racines → actions correctives fournissent des directives claires et durables qui manquent souvent dans la documentation officielle et qui restent fiables au fil des versions :

> `[` est GZ→ROS, `]` est ROS→GZ · `16UC1` est en millimètres, `32FC1` est en mètres · `joint_state_broadcaster` n'est pas lancé automatiquement · `raytrace_max_range` ≤ `obstacle_max_range` signifie que les obstacles ne s'effacent jamais · rclc n'alloue pas automatiquement les champs de message non bornés

**4. Optimiser l'utilisation du contexte avec une architecture à trois couches.** Chaque skill équilibre l'efficacité du contexte : les descriptions de skills restent en contexte, les corps de skills se chargent lors de leur invocation, et les fichiers de référence approfondis dans `references/` ne se chargent qu'à la demande. Les grands catalogues de symboles et les tableaux détaillés d'ajustement de paramètres résident dans `references/`, ce qui préserve le contexte et évite que le débogage de composants ciblés (comme AMCL) ne charge de la documentation inutile (comme les nœuds d'arbres de comportement).

## Ce qui le différencie

La plupart des packs de skills en robotique intègrent directement des connaissances d'API statiques dans les fichiers de skills. Bien que l'utilisation initiale soit simple, cette approche échoue lorsque les packages sous-jacents sont mis à jour — laissant des extraits de code obsolètes qui échouent silencieusement. Ce dépôt adopte une approche dynamique guidée par la documentation :

| Fonctionnalité | Packs de skills à fort contenu | **claude-ros2-skills** |
| :--- | :--- | :--- |
| Emplacement des connaissances | Intégré dans les fichiers de skills (**400–1 800 lignes/skill**) | Lié à la doc officielle (corps de skill de **~60 lignes**) ; références détaillées lues **uniquement si nécessaire** |
| Contexte chargé en permanence | Fichiers `SKILL.md` complets | Protocole cœur de **26 lignes** |
| Gestion des mises à jour d'API Jazzy | Les extraits deviennent obsolètes discrètement ; nécessite des mises à jour manuelles continues des tests | Le risque d'extraits obsolètes est réduit aux liens d'entrée et noms de symboles — **38 liens de documentation** vérifiés chaque semaine via la CI |
| Méthode de vérification | Analyse statique de code ou vérification de logs | **Vérification physique & à l'exécution** : contrôles de gravité IMU, tests d'odométrie directionnelle, alignement des repères TF, compatibilité QoS DDS |
| Portée de support | Prétend supporter plusieurs distributions ROS tout en ne ciblant qu'une seule | **ROS 2 Jazzy uniquement**, explicitement conçu et validé |

Ce dépôt est optimisé pour un objectif unique : minimiser le risque de générer du code d'apparence plausible mais qui échoue à s'exécuter sur ROS 2 Jazzy.

## Évaluations

Chaque résultat ci-dessous provient d'une paire A/B mesurée : le **prompt identique** exécuté dans des sessions Claude Code neuves et sans interface graphique — une fois sans ces skills, une fois avec eux — en utilisant le **même modèle** dans les deux cas. L'évaluation s'est faite en quatre étapes : comparaison symbole par symbole avec les sources Jazzy amont figées, puis avec une installation `/opt/ros/jazzy` en direct, puis en chargeant les deux sorties dans une **simulation Gazebo en direct**, et enfin en **exécutant les nœuds générés face à des publieurs actifs**. Désormais, chaque tâche de la suite dispose d'une mesure sur installation réelle. Les transcriptions complètes, le code généré et les journaux d'exécution sont commités sous [`evals/runs/`](./evals/runs/), et le harnais qui produit les paires se trouve dans [`evals/harness/`](./evals/harness/), afin que chacun puisse réévaluer ou réexécuter sans devoir nous croire sur parole.

La taille d'échantillon est de **n=1 par cellule**, et les exécutions comme la notation ont été réalisées par le projet qui publie ces résultats. La notation est mécanique autant que possible (le symbole existe-t-il dans l'installation ? la commande aboutit-elle ?), afin de pouvoir être vérifiée de façon indépendante.

### Configuration Nav2 MPPI — Haiku, installation Jazzy en direct

*Prompt : configurer Nav2 avec le contrôleur MPPI pour un robot à transmission différentielle sur Jazzy et produire le fichier YAML du controller server.*

| | Sans skills | Avec skills |
| :--- | :--- | :--- |
| Processus | Réponse instantanée de mémoire ; **aucune** vérification bien que les outils soient disponibles | A demandé le footprint, la configuration existante, la localisation et les limites de vitesse **en premier**, puis a lu les valeurs par défaut sous `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml` |
| Chaîne de plugin | `mppi_generic::ControllerServer` — n'existe pas | `nav2_mppi_controller::MPPIController` — correct |
| Liste `critics:` | Totalement absente | Les 8 présents, noms corrects |
| Clés de paramètres inventées | **~16** | **0** — chaque clé comparée mécaniquement aux valeurs par défaut installées |
| **Chargé dans une simulation Gazebo en direct** | **`[FATAL] Failed to create controller … does not exist` — Nav2 s'arrête au bringup ; le robot ne bouge jamais** | **MPPI + les 8 critics se chargent ; le robot roule de (−2.0, −0.5) à (0.5, 0.5) ; `NavigateToPose` renvoie `SUCCEEDED`** |

### Un package qui doit réellement s'exécuter — Haiku, dans le conteneur

*Prompt : créer un package Python `demo_pkg` publiant `std_msgs/msg/String` sur `/greeting` à 1 Hz avec un fichier launch ; le builder et afficher `ros2 topic echo /greeting`.*

| | Sans skills | Avec skills |
| :--- | :--- | :--- |
| `ros2 run` / `ros2 launch` / `topic echo` | **Échec pour les trois** — le package ne s'enregistre jamais dans l'index ament | **Succès pour les trois**, confirmé par des réexécutions indépendantes de chaque commande |
| Coût pour ce résultat | 0,17 $ · 36 tours · 178 s | **0,08 $ · 18 tours · 61 s** — correct du premier coup et **2,2× moins cher** |

### Abonnement à un capteur — Haiku, les deux nœuds exécutés face à un publieur actif

*Prompt : écris un nœud Python Jazzy qui s'abonne à `/scan` et journalise la distance minimale une fois par seconde.* Chaque nœud généré a ensuite été exécuté pendant 6 s face à un publieur `/scan` en BEST_EFFORT.

| | Sans skills | Avec skills |
| :--- | :--- | :--- |
| QoS de l'abonnement | `create_subscription(..., 10)` → RELIABLE | `qos_profile_sensor_data` |
| **Messages réellement reçus à l'exécution** | **Zéro.** rclpy a lui-même signalé `offering incompatible QoS. No messages will be received from it. Last incompatible policy: RELIABILITY` | **Reçoit à 5 Hz** |
| Minimum rapporté (bonne réponse : 0,45 m) | n'en a jamais reçu | `0,020 m` — **également faux** : aucun des deux nœuds ne filtre selon `range_min`/`range_max` |

L'écart de connectivité est celui qui détermine si le pipeline capteur existe tout court, et il est reproductible. L'erreur numérique, elle, est un défaut réel des deux conditions : elle est donc consignée comme chantier à venir pour `ros2-core`, et non comme un succès.

### Poser la question avant d'écrire — Haiku, LiDAR monté à l'envers

*Prompt : mon LiDAR est monté à l'envers à l'arrière du châssis, tourné vers l'arrière ; écris la TF statique et dis-moi comment confirmer la correction.*

| | Sans skills | Avec skills |
| :--- | :--- | :--- |
| Établit d'abord le montage physique | A répondu en un seul tour | **S'est arrêté pour demander la distance arrière et les décalages** avant d'émettre la transformation |
| Justesse de la transformation | roll≈180° + yaw≈180°, relation parent/enfant conforme à REP 105 — correct | correct ; les deux sorties ont été publiées et signalées par `check_tf_tree.py` exactement comme prévu |
| Conseil de vérification | RViz avec un affichage **PointCloud2** — mauvais type de message pour un LiDAR | `tf2_echo` plus un affichage **LaserScan** |

### Ce que ces skills ne corrigent pas

Consigné ici, car l'omettre rendrait le reste moins digne de confiance :

- **L'hallucination se déplace, elle ne disparaît pas.** Sur les trois tâches les plus récentes, la sortie avec skills a encore inventé `ros2_troubleshooting_helpers` (package inexistant — et ce, en décrivant *le propre script de ce dépôt*) ainsi qu'une valeur de durability par défaut erronée. Router vers la documentation relève le plancher ; cela ne rend pas le modèle exact.
- **Sur les problèmes que le modèle maîtrise déjà, les skills coûtent plus et apportent peu.** Pour le diagnostic classique d'incompatibilité QoS, les deux conditions ont eu juste en un tour, et la version avec skills a ajouté une erreur factuelle pour environ 1,4× le coût.
- **Les skills changent ce que l'agent *demande* plus fiablement que ce qu'il *vérifie*.** Avec une reproduction en direct active et `Bash` autorisé, les deux cellules ont recommandé `ros2 topic info -v` et aucune ne l'a exécuté.
- **Aucune des deux conditions n'a obtenu les bons chiffres sur la tâche 1.** Les deux nœuds générés omettent le filtrage `range_min`/`range_max` et rapporteraient une mesure sous le minimum comme l'obstacle le plus proche.

### La tendance sur chaque paire

Aucune cellule de référence, dans aucun essai, n'a vérifié les packages installés ou la documentation **avant** d'écrire, même avec WebFetch, Read et Bash explicitement autorisés — et l'une d'elles a signalé un build pleinement fonctionnel pour un package que `ros2 run` ne parvient même pas à trouver. Les cellules avec skills ont posé les questions préalables à l'écriture dans tous les essais où la tâche comportait des inconnues, et leurs affirmations correspondaient aux réexécutions indépendantes. Les scripts de vérification ont désormais été éprouvés sur données réelles dans les deux sens : `check_qos_compat.py` a produit son premier `[FAIL]` réel face à une véritable incompatibilité BEST_EFFORT/RELIABLE, et `check_tf_tree.py` a signalé un capteur inversé sans marquer celui qui était correctement monté.

Consultez les tableaux d'évaluation complets, les environnements de test et les analyses de chaque essai dans [`evals/RESULTS.md`](./evals/RESULTS.md). Pour plus de détails sur le protocole d'évaluation, les listes de contrôle des tâches et la configuration du conteneur, voir [`evals/README.md`](./evals/README.md). Les pull requests contenant des transcriptions évaluées supplémentaires sont les bienvenues.

## Démarrage rapide

**Option A — Plugin Marketplace (Recommandé) :**

```
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

Mettez à jour les plugins installés à tout moment avec `/plugin marketplace update`.

**Option B — Installation manuelle :**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git

# Installation au niveau du projet (s'applique uniquement au projet actuel)
mkdir -p your-project/.claude/skills
cp -r claude-ros2-skills/skills/* your-project/.claude/skills/
cp claude-ros2-skills/CLAUDE.md your-project/

# Installation au niveau de l'utilisateur (s'applique à tous les projets)
mkdir -p ~/.claude/skills
cp -r claude-ros2-skills/skills/* ~/.claude/skills/
```

Redémarrez Claude Code (ou démarrez une nouvelle session) pour appliquer les skills installés.

## Skills

| Skill | Chemin | Couverture |
| :--- | :--- | :--- |
| **ros2-core** | `skills/ros2-core/SKILL.md` | rclcpp, rclpy, TF2, odométrie EKF, profils QoS, paramètres |
| **ros2-package** | `skills/ros2-package/SKILL.md` | `ros2 pkg create`, configuration CMakeLists/setup.py, build & source colcon, interfaces personnalisées |
| **ros2-dev** | `skills/ros2-dev/SKILL.md` | Nav2 (AMCL, costmaps, MPPI/Smac), SLAM Toolbox, RTAB-Map, Isaac ROS |
| **gazebo-sim** | `skills/gazebo-sim/SKILL.md` | Gazebo Harmonic, ros_gz_bridge, ros_gz_sim, modélisation SDFormat |
| **ros2-control** | `skills/ros2-control/SKILL.md` | Abstraction matérielle ros2_control, controller manager, balises URDF |
| **ros2-moveit** | `skills/ros2-moveit/SKILL.md` | MoveIt 2, API C++/Python MoveGroup, solveurs IK, OMPL, MoveIt Servo |
| **ros2-perception** | `skills/ros2-perception/SKILL.md` | image_transport, cv_bridge, vision_msgs, depth_image_proc, PCL |
| **ros2-testing** | `skills/ros2-testing/SKILL.md` | launch_testing, gtest/pytest, API C++/Python rosbag2, ros2trace |
| **ros2-microros** | `skills/ros2-microros/SKILL.md` | Agent micro-ROS, API client rclc, transports personnalisés, mémoire statique |
| **ros2-security** | `skills/ros2-security/SKILL.md` | SROS2, génération de keystore PKI, contrôle d'accès, sécurité DDS |
| **ros2-troubleshooting** | `skills/ros2-troubleshooting/SKILL.md` | Arbre TF de vérité terrain REP 103/105, alignement LiDAR/IMU, vérification physique |

## Scripts de vérification

Ces scripts de vérification sont intégrés au skill `ros2-troubleshooting` (`skills/ros2-troubleshooting/scripts/`) et sont inclus avec chaque installation. Ils transforment les contrôles matériels physiques en étapes de vérification exécutables de type succès/échec (nécessite un environnement ROS 2 sourcé ; codes de retour : 0 = SUCCÈS, 1 = ÉCHEC, 2 = AUCUNE DONNÉE) :

| Script | Vérifie |
| :--- | :--- |
| `check_imu_gravity.py` | Valide qu'un robot au repos mesure la gravité à environ +9,81 m/s² le long de l'axe **+Z** (REP 103). Détecte les montages d'IMU inversés ou mal alignés. |
| `check_odom_direction.py` | Valide que le fait de pousser le robot vers l'avant produit un déplacement d'odométrie positif le long de son cap. Détecte les directions de moteur inversées, les problèmes de polarité d'encodeur ou les configurations TF inversées. |
| `check_tf_tree.py` | Vérifie que `map→odom→base_link` se résout correctement ; affiche chaque décalage de montage de capteur en degrés RPY et met en évidence les erreurs d'orientation potentielles de 180°. |
| `check_qos_compat.py` | Vérifie la compatibilité QoS sur toutes les paires publisher/subscriber d'un topic à l'aide des règles DDS. Prévient les échecs silencieux (comme un publisher BEST_EFFORT associé à un subscriber RELIABLE, ou des incompatibilités de durabilité, d'échéance et de réactivité). |

La logique de décision principale est testée unitairement indépendamment de ROS (`python3 skills/ros2-troubleshooting/scripts/test_checks.py`) et s'exécute via l'intégration continue (CI) à chaque push.

## Fonctionnement

```mermaid
flowchart LR
    A["votre requête"] --> B["CLAUDE.md<br/>protocole + critères,<br/>aucun détail d'API"]
    B --> C["skills/&lt;nom&gt;/SKILL.md<br/>critères, boucle,<br/>tableaux d'échecs"]
    C --> D["/opt/ros/jazzy/<br/>ou doc officielle Jazzy"]
    C -.uniquement si nécessaire.-> R["references/<br/>catalogues de symboles,<br/>tables d'ajustement"]
    D --> E["code, puis preuve d'exécution"]
    R --> E
```

`CLAUDE.md` ne contient aucun détail d'API spécifique. À la place, il établit le protocole opérationnel et exige que des questions de clarification soient répondues avant d'écrire du code. Chaque fichier `SKILL.md` gère les décisions spécifiques à son domaine : identifier les variables inconnues, exécuter la boucle vérifier-écrire-prouver et se référer aux tableaux d'échecs. Les documents de référence détaillés sont stockés séparément dans le répertoire `references/`. Consultez [`CLAUDE.md`](./CLAUDE.md) pour plus de détails.

## Mise à jour

```bash
cd claude-ros2-skills
git pull
cp -r skills/* ~/.claude/skills/   # ou dans le répertoire .claude/skills/ de votre projet
```

## Feuille de route

1. ~~Automatiser les paires d'évaluation au sein de conteneurs `ros:jazzy`~~ — **terminé (2026-07-25) :** réexécution de la tâche 4 sur une installation en direct sous `/opt/ros/jazzy` ; résultats dans [`evals/RESULTS.md`](./evals/RESULTS.md).
2. ~~Publier les résultats d'évaluation de la tâche 5~~ — **terminé (2026-07-25) :** résultat binaire build/run/echo mesuré dans le conteneur ; résultats dans [`evals/RESULTS.md`](./evals/RESULTS.md).
3. ~~Étendre les évaluations sur installation en direct aux tâches 1 à 3~~ — **terminé (2026-07-26) :** exécuté sur une installation native `ros-jazzy-ros-base`, les deux nœuds générés étant lancés face à des publieurs actifs ; harnais dans [`evals/harness/`](./evals/harness/), résultats dans [`evals/RESULTS.md`](./evals/RESULTS.md).
4. ~~Corriger les défauts révélés par ces essais~~ — **terminé (2026-07-26) :** `ros2-troubleshooting` indique désormais l'invocation littérale du script (le modèle inventait un package) et précise que `check_tf_tree.py` signale toujours un montage à ~180° pour confirmation physique ; `ros2-core` a reçu la règle de bornes `range_min`/`range_max` et un motif d'arrêt propre. **Les tableaux d'évaluation mesurent les skills tels qu'ils étaient avant ces correctifs.**
5. **Réexécuter les tâches 1 à 3 avec les skills corrigés**, afin de savoir si les correctifs changent réellement la sortie — c'est la raison pour laquelle les tableaux ci-dessus décrivent encore la version antérieure.
6. **Rendre la tâche 3 discriminante** — les deux conditions répondant aujourd'hui correctement de mémoire, exiger que le diagnostic QoS soit *démontré* face à des endpoints réels, et non simplement recommandé.
7. **Suivre les « corrections jusqu'à finalisation » comme métrique principale** — mesurer le nombre d'itérations de retour nécessaires avant que le code ne s'exécute avec succès.
8. **Implémenter des recherches déterministes dans `references/`** pour garantir que les documents de référence détaillés se chargent chaque fois que cela est pertinent.
9. **Étendre la séparation corps/`references`** à `ros2-core` et `gazebo-sim`, en optimisant l'efficacité du contexte pour les skills à haute fréquence disposant d'une documentation de référence importante.

## Contribuer

Résumé : les fichiers de skills doivent se concentrer sur la logique de décision (critères de validation, étapes de boucle et tableaux d'échecs), tandis que la documentation détaillée reste dans `references/`. Chaque symbole d'API doit être vérifié par rapport à la documentation officielle de Jazzy ou aux installations sous `/opt/ros/jazzy/`. Les scripts de vérification doivent conserver une logique pure pouvant être testée unitairement sans dépendances ROS. Pour obtenir l'ensemble des directives, les listes de contrôle des skills et des scripts, ainsi que les modèles de ticket, consultez [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Licence

Apache-2.0 — voir [LICENSE](./LICENSE).
