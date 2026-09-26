<div align="center">

<img src="assets/hero.png" alt="ROS 2 Jazzy skills for Claude Code and Codex" width="100%"/>

**Conditionnement contextuel d’outils de vérification, de flux de travail et de preuves de transfert pour ROS 2.**

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | **Français** | [Deutsch](README.de.md)

</div>

Trois skills pour **Claude Code et Codex** ciblant **Ubuntu 24.04 / ROS 2 Jazzy** : développer des paquets, vérifier les tests et les artefacts installés, et diagnostiquer les pannes à l’exécution.

Ce dépôt regroupe des connaissances de domaine, des flux de travail ciblés et des outils de diagnostic exécutables selon le standard [Agent Skills](https://agentskills.io/home). Plutôt que de revendiquer une amélioration des capacités intrinsèques de génération de code des modèles de pointe, ce projet explore une hypothèse d'ingénierie : **le conditionnement de vérifications de preuves spécifiques à l'environnement et d'enregistrements structurés de transfert (handoff) peut réduire l'ambiguïté de vérification et le coût de transfert de contexte entre sessions ou collaborateurs.** Bien que la fonctionnalité individuelle des outils soit validée sur des bancs d’essai, **la réduction du coût de transfert et les gains globaux de productivité restent des hypothèses non prouvées.**

## Démarrage rapide

La détection automatique des skills (skill discovery) est prise en charge dans tous les environnements.

**Codex — Installation dans un projet :**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# Installation globale pour l'utilisateur :
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

Les skills s'installent dans `<projet>/.agents/skills` ou `~/.agents/skills`, en intégrant le [protocole de vérification](CLAUDE.md) commun. Les configurations existantes et les autres skills sont préservés.

**Claude Code — Installation du plugin :**

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

## Skills disponibles

| Skill | Quand l'utiliser | Ce qu'il apporte |
| :--- | :--- | :--- |
| [ros2-development](skills/ros2-development/SKILL.md) | Créer ou modifier paquets, nœuds, interfaces, launch, configurations et tests | Compilations tenant compte des dépendances, vérification des artefacts installés, détection des exécutions sans tests, et outil optionnel de suivi des preuves pour les transferts |
| [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md) | Pannes d'exécution des publications, callbacks, TF, IMU ou odométrie | Quatre diagnostics exécutables et références directes sur les repères (REP 103/105), la QoS et l'étalonnage |
| [ros2-microros](skills/ros2-microros/SKILL.md) | Transport MCU, agent, rclc, gestion mémoire | Points d'entrée et guides de diagnostic ; **non validé sur matériel MCU** |

## Outils exécutables de vérification et de preuve

Les scripts sont inclus dans chaque skill. Dans les exemples, `ROS2_SKILL_DIR` est une variable illustrative définie en interne par l'agent vers le répertoire du skill chargé ; elle ne nécessite aucune intervention de l'utilisateur.

| Script | Rôle et preuve vérifiée |
| :--- | :--- |
| `ros2-development/scripts/check_test_results.py` | Vérifie les tests exécutés et réussis dans les rapports récents colcon (rejette les tests vides) |
| `ros2-development/scripts/evidence.py begin / finish / inspect` | **Flux optionnel (opt-in)** : Enregistre les métadonnées déclarées par l'appelant et compare les hachages de fichiers ainsi que les valeurs d'environnement sélectionnées pour faciliter le transfert |
| `ros2-troubleshooting/scripts/check_qos_compat.py --topic /scan` | Compatibilité QoS Jazzy native entre paires de publication/abonnement |
| `ros2-troubleshooting/scripts/check_tf_tree.py --sensors laser_frame,imu_link` | Connectivité TF et angles RPY pour comparaison physique |
| `ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data` | Gravité au repos sur sol plat projetée dans `--base base_link` |
| `ros2-troubleshooting/scripts/check_odom_direction.py --topic /odom` | Direction de l'odométrie récente avant et après un mouvement observé |

**Codes de sortie de diagnostic : 0 SUCCÈS, 1 ÉCHEC, 2 NON CONCLUSIF ou requête invalide.**
**Codes de sortie de l'inspection de preuve : 0 Cohérent (Consistent), 1 Modifié (Changed), 2 Incomplet (Incomplete).**
L'outil de preuve sépare strictement les résultats déclarés par l'appelant des hachages observés par l'outil. Il n'exécute ni ne réexécute les commandes, ne garantit pas la fraîcheur ni l'absence de modifications intermédiaires, et ne prouve pas l'état global du robot. Voir [docs/DESIGN.md](docs/DESIGN.md).

## Limites de validation

Dans les évaluations historiques avec Claude Code Opus 5.5 High, les sessions avec skills et les sessions de référence ont réussi les mêmes tâches. Dans l'étude de migration d'interfaces ([RESULTS.md](evals/workflow_value/RESULTS.md)), les sessions avec skills ont été plus rapides, mais les effets d'échantillon et de cache **n'établissent pas de façon causale un gain de vitesse, de fiabilité ou de capacité de codage**.

Les robots réels, les micrologiciels MCU et les applications Nav2/MoveIt complètes restent non vérifiés.

## Contribution et licence

[CONTRIBUTING.md](CONTRIBUTING.md) · [evals/AUTHORING.md](evals/AUTHORING.md) · [Apache-2.0](LICENSE).
