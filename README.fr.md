# Développer en ROS 2 avec des preuves de fonctionnement

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

Trois skills Claude Code pour Ubuntu 24.04 / ROS 2 Jazzy : développer des paquets, vérifier les tests et les artefacts installés, diagnostiquer les défauts à l’exécution. Ils respectent les conventions du projet et s’appuient sur la documentation installée.

## Installation

Choisissez une méthode. Dans une session Claude Code, installez le plugin :

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

Installation manuelle dans un projet existant :

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --project /path/to/your-workspace
# --user: alternative to --project
```

Démarrez une nouvelle session. Le plugin charge le protocole via SessionStart ; la portée utilisateur concerne tous les projets. L’installation manuelle préserve CLAUDE.md et les autres skills et place le protocole dans .claude/rules/ros2-verification.md. Les modifications locales ne sont pas écrasées. ROS, colcon et les pilotes sont à installer séparément.

## Skills

- [ros2-development](skills/ros2-development/SKILL.md): Développement de paquets, nœuds, interfaces, launch/config et tests ; contrôle que chaque paquet a réellement exécuté des tests.
- [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md): Quatre diagnostics exécutables : QoS, TF, IMU et direction de l’odométrie, avec références de repères et d’étalonnage.
- [ros2-microros](skills/ros2-microros/SKILL.md): Conseils MCU, agent, rclc et mémoire. Non validés sur MCU.

Mentionnez le skill dans la demande : « Utilise ros2-development pour modifier ce paquet Jazzy, compiler ses dépendances et vérifier le nœud installé ainsi que les tests exécutés. »

## Validation et limites

Codes : 0 PASS, 1 FAIL, 2 INCONCLUSIVE ou demande invalide. Données absentes, NaN, QoS indéterminée, TF manquante ou aucun test exécuté ne constituent pas un succès. L’IMU est transformée dans le repère de base ; la gravité ne vérifie pas le yaw. L’odométrie vérifie la direction, pas l’échelle des distances. Les diagnostics ne publient pas de commande de mouvement.

CI vérifie la préservation des installations, la logique, de vrais paquets temporaires Python/CMake, les communications et TF synthétiques Jazzy et l’évaluateur. Opus 5.5 High a terminé trois tâches avec le plugin et avec l’installation manuelle ; la référence sans le pack a aussi terminé les trois. Il s’agit d’une observation par méthode et tâche : voir le [rapport de validation](evals/development/RESULTS.md). Ces essais valident les outils, pas un gain mesuré du modèle. Robots physiques et MCU demandent une validation distincte.

Certains scores historiques manquent de transcriptions ou de nouvelles notations reproductibles ; ils ne sont pas présentés comme les performances actuelles. [CAPABILITIES.md](evals/CAPABILITIES.md).

## Mise à jour

En installation manuelle, mettez le dépôt à jour et relancez le même installateur. Pour le plugin, utilisez la commande suivante puis ouvrez une nouvelle session.

```bash
claude plugin update claude-ros2-skills@claude-ros2-skills
```

[Parcours complet et portée des preuves (English)](README.md) · [Contribuer](CONTRIBUTING.md) · [Apache-2.0](LICENSE).
