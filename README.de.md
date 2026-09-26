<div align="center">

<img src="assets/hero.png" alt="ROS 2 Jazzy skills for Claude Code and Codex" width="100%"/>

**Kontextbezogene Bündelung von ROS-2-Verifikationswerkzeugen, Workflows und Übergabenachweisen.**

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | **Deutsch**

</div>

Drei Skills für **Claude Code und Codex** für **Ubuntu 24.04 / ROS 2 Jazzy**: Pakete entwickeln, Tests und installierte Artefakte prüfen und Laufzeitfehler diagnostizieren.

Dieses Repository bündelt Domänenwissen, Arbeitsabläufe und ausführbare Diagnosewerkzeuge gemäß dem [Agent Skills Standard](https://agentskills.io/home). Anstatt eine Steigerung der inhärenten Codegenerierungsfähigkeiten von Spitzenmodellen zu behaupten, untersucht dieses Projekt eine technische Hypothese: **Die Bündelung umgebungsspezifischer Nachweisprüfungen und strukturierter Übergabeprotokolle (Handoffs) kann Verifikationsunklarheiten und Kontextübertragungskosten zwischen Sitzungen oder Beteiligten reduzieren.** Während die Funktion einzelner Werkzeuge in Testszenarien bestätigt wurde, **bleiben geringere Übergabekosten und allgemeine Produktivitätsgewinne unbewiesene Hypothesen.**

## Schnellstart

Die automatische Skill-Erkennung (Skill Discovery) wird in allen Umgebungen unterstützt.

**Codex — Installation in einem Projekt:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# Benutzerweite Installation:
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

Die Skills werden unter `<Projekt>/.agents/skills` oder `~/.agents/skills` installiert und laden das gemeinsame [Prüfprotokoll](CLAUDE.md). Bestehende Konfigurationen und andere Skills bleiben erhalten.

**Claude Code — Plugin-Installation:**

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

## Verfügbare Skills

| Skill | Einsatzbereich | Funktion |
| :--- | :--- | :--- |
| [ros2-development](skills/ros2-development/SKILL.md) | Pakete, Knoten, Schnittstellen, Launch, Konfiguration und Tests entwickeln | Abhängigkeitsbewusste Builds, Prüfung installierter Artefakte, Erkennung von Testläufen ohne Tests und optionales Nachweis-Tracking für Übergaben |
| [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md) | Laufzeitfehler bei Publishern, Callbacks, TF, IMU oder Odometrie | Vier ausführbare Diagnosen und direkte Referenzen zu Koordinatenrahmen (REP 103/105), QoS und Kalibrierung |
| [ros2-microros](skills/ros2-microros/SKILL.md) | MCU-Transport, Agent, rclc, Nachrichtenspeicher | Einstiegspunkte und Diagnoseleitfaden; **nicht auf MCU-Hardware validiert** |

## Ausführbare Verifikations- und Nachweiswerkzeuge

Die Skripte sind den jeweiligen Skills beigelegt. In den Beispielen ist `ROS2_SKILL_DIR` eine vom Agenten intern gesetzte Beispielvariable auf das geladene Skill-Verzeichnis; sie erfordert keine Benutzereingabe.

| Skript | Zweck und geprüfter Nachweis |
| :--- | :--- |
| `ros2-development/scripts/check_test_results.py` | Prüft tatsächlich ausgeführte und bestandene Tests in frischen colcon-Berichten (schließt leere Läufe aus) |
| `ros2-development/scripts/evidence.py begin / finish / inspect` | **Opt-in-Workflow**: Erfasst vom Aufrufer deklarierte Metadaten und vergleicht Datei-Hashes sowie ausgewählte Umgebungswerte zur Unterstützung von Übergaben |
| `ros2-troubleshooting/scripts/check_qos_compat.py --topic /scan` | Native Jazzy-QoS-Kompatibilität zwischen Publisher- und Subscriber-Endpunkten |
| `ros2-troubleshooting/scripts/check_tf_tree.py --sensors laser_frame,imu_link` | TF-Konnektivität und RPY-Montagewinkel für den physischen Abgleich |
| `ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data` | Erdbeschleunigung in Ruhelage auf ebener Fläche transformiert in `--base base_link` |
| `ros2-troubleshooting/scripts/check_odom_direction.py --topic /odom` | Frische Odometrie-Richtung vor und nach einer beobachteten Bewegung |

**Diagnose-Rückgabewerte: 0 BESTANDEN, 1 FEHLER, 2 NICHT EINDEUTIG oder ungültige Anfrage.**
**Nachweisprüfungs-Rückgabewerte: 0 Konsistent (Consistent), 1 Geändert (Changed), 2 Unvollständig (Incomplete).**
Das Nachweiswerkzeug trennt strikt zwischen den vom Aufrufer deklarierten Ausgaben und den vom Werkzeug beobachteten Hashes. Es führt keine Benutzerbefehle aus, garantiert weder Frische noch das Fehlen von Zwischenänderungen und belegt nicht die Gesamtkorrektheit des Roboters. Siehe [docs/DESIGN.md](docs/DESIGN.md).

## Validierungsgrenzen

Exit-Codes: 0 PASS, 1 FAIL, 2 INCONCLUSIVE oder ungültige Anfrage. Fehlende Daten, NaN, unbekanntes QoS, fehlende TF, <2 Messungen, übermäßige Messwertvariation (>1,5 m/s², anpassbar über --max-variation) oder keine ausgeführten Tests zählen nicht als Erfolg. PASS betrifft die gemessene +Z-Gravitation im horizontalen Basisrahmen nach deklariertem TF oder expliziter Ausrichtungsannahme (--assume-aligned); keines davon beweist physischen Stillstand, und Gravitation prüft kein Yaw. Der Odometrietest prüft Richtung, nicht Entfernungskalibrierung. Laufzeitdiagnosen senden keine Bewegungsbefehle.

CI prüft Installationserhalt, Code-Gültigkeit, reale Python/CMake- und ament-Tests sowie synthetische Jazzy-Kommunikation.

In früheren Evaluierungen mit Claude Code Opus 5.5 High bestanden sowohl Sessions mit Skills als auch die Baseline dieselben Aufgaben. In einer Schnittstellen-Migrationsstudie ([RESULTS.md](evals/workflow_value/RESULTS.md)) waren Skill-Sessions in den beobachteten Läufen schneller; Stichproben- und Cache-Einflüsse **begründen jedoch keinen kausalen Nachweis für Geschwindigkeits-, Zuverlässigkeits- oder Programmierfähigkeitsverbesserungen**. Die historische 0.1.2-Studie bewertet nicht die neuen Übergabewerkzeuge von Version 0.2.0.

Reale Roboter, MCU-Firmware und vollständige Nav2/MoveIt-Anwendungen bleiben ungeprüft.

## Mitwirken & Lizenz

[CONTRIBUTING.md](CONTRIBUTING.md) · [evals/AUTHORING.md](evals/AUTHORING.md) · [Apache-2.0](LICENSE).
