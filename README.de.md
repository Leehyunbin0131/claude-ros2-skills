# ROS-2-Entwicklung mit nachgewiesener Funktion

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

Drei Skills für Claude Code und Codex für Ubuntu 24.04 / ROS 2 Jazzy: Pakete entwickeln, Tests und installierte Artefakte prüfen und Laufzeitfehler diagnostizieren. Bestehende Projektkonventionen bleiben maßgeblich; installierte Dokumentation wird gezielt herangezogen.

## Installation

### Installation für Codex

Nach dem Klonen des Repositorys den folgenden Befehl ausführen. Projekt-Skills liegen unter `.agents/skills`; mit `--user` statt `--project` wird `~/.agents/skills` verwendet. Jeder Skill enthält das gemeinsame Prüfprotokoll, das bei seiner Verwendung geladen wird. Bestehende `AGENTS.md`, `CLAUDE.md` und Einstellungen bleiben erhalten. Eine neue Sitzung im Projekt starten. In CLI/IDE ist der explizite Aufruf mit `$ros2-development` möglich. Siehe [Codex-Prüfbericht](evals/CODEX.md). Das Plugin und die folgenden manuellen Standardbefehle gelten für Claude Code.

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

### Claude Code

Wählen Sie eine Methode. Für das Plugin in einer Claude-Code-Sitzung:

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

Manuelle Installation in ein vorhandenes Projekt:

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --project /path/to/your-workspace
# --user: alternative to --project
```

Starten Sie eine neue Sitzung. Das Plugin lädt das Protokoll über SessionStart; die Benutzerebene gilt für alle Projekte. Die manuelle Installation erhält CLAUDE.md und fremde Skills und legt das Protokoll unter .claude/rules/ros2-verification.md ab. Lokale Änderungen werden nicht überschrieben. ROS, colcon und Treiber sind separat erforderlich.

## Skills

- [ros2-development](skills/ros2-development/SKILL.md): Pakete, Nodes, Schnittstellen, launch/config und Tests entwickeln; prüfen, dass jedes Paket tatsächlich Tests ausgeführt hat.
- [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md): Vier ausführbare Diagnosen: QoS, TF, IMU und Odometrierichtung, ergänzt um Referenzen zu Koordinaten und Kalibrierung.
- [ros2-microros](skills/ros2-microros/SKILL.md): Hinweise zu MCU, Agent, rclc und Speicher. Nicht auf einer MCU validiert.

Nennen Sie den Skill im Auftrag: „Nutze ros2-development, um dieses Jazzy-Paket zu ändern, seine Abhängigkeiten zu bauen und den installierten Node sowie die ausgeführten Tests zu prüfen.“

## Validierung und Grenzen

Exit-Codes: 0 PASS, 1 FAIL, 2 INCONCLUSIVE oder ungültige Anfrage. Fehlende Daten, NaN, unbekanntes QoS, fehlende TF oder keine ausgeführten Tests zählen nicht als Erfolg. Die IMU wird in den Basisrahmen transformiert; Gravitation prüft kein Yaw. Der Odometrietest prüft Richtung, nicht Entfernungskalibrierung. Laufzeitdiagnosen senden keine Bewegungsbefehle.

CI prüft Installationsschutz, Entscheidungslogik, echte temporäre Python/CMake-Pakete, synthetische Jazzy-Kommunikation und TF sowie den Evaluator. Opus 5.5 High hat drei Aufgaben sowohl mit Plugin als auch mit manueller Installation abgeschlossen; die Baseline ohne das Paket ebenfalls. Das ist eine Beobachtung pro Methode und Aufgabe, siehe [Abnahmebericht](evals/development/RESULTS.md). Die Tests belegen Werkzeugverhalten, keinen gemessenen Fähigkeitsgewinn des Agenten. Reale Roboter und MCUs benötigen eigene Validierung.

Eine spätere [Vergleichsstudie zur Schnittstellenmigration](evals/workflow_value/RESULTS.md) prüft drei Varianten mit Python/C++-Verbrauchern unter Opus 5.5 High. Alle sechs Ergebnisse mit und ohne Pack bestehen die unabhängige Prüfung. Berichtsgenauigkeit, mehrdeutige Regeln und verbleibende Prozesse werden getrennt dokumentiert. Ein Zuverlässigkeitsgewinn oder kausaler Geschwindigkeitsvorteil ist nicht belegt; die Skills bleiben bei 0.1.2.

Einigen historischen Zahlen fehlen Transkripte oder reproduzierbare Neubewertungen; sie werden nicht als aktuelle Leistung beworben. [CAPABILITIES.md](evals/CAPABILITIES.md).

## Aktualisierung

Bei manueller Installation das Repository aktualisieren und denselben Installer erneut ausführen. Für das Plugin folgenden Befehl verwenden und eine neue Sitzung starten.

```bash
claude plugin update claude-ros2-skills@claude-ros2-skills
```

[Vollständiger Ablauf und Evidenzumfang (English)](README.md) · [Mitwirken](CONTRIBUTING.md) · [Apache-2.0](LICENSE).
