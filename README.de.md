<div align="center">

<img src="assets/hero.png" alt="claude-ros2-skills — Claude Code skills for ROS 2 Jazzy" width="100%"/>

**Claude Code Skills for ROS 2 Jazzy Jalisco robotics development.**

Skills, die die ROS 2-Entwicklung mit KI-Agenten grundlegend verändern: Unbekannte Parameter im Voraus identifizieren, Einstellungen anhand installierter Pakete verifizieren und die Ausführung durch funktionierende Nachweise bestätigen.

![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?logo=ubuntu&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | **Deutsch**

<sub>🌐 Dieses Dokument ist eine maschinelle Übersetzung. Das Original ist auf [English](README.md).</sub>

| Skills | Immer geladenes Protokoll | Doku-Links (CI-geprüft) | Physikalische Roboter-Prüfungen | Evals: Gazebo A/B |
| :---: | :---: | :---: | :---: | :---: |
| **11** | **26 Zeilen** | **38** | **4 Skripte** | **Ziel erreicht vs. Bringup-Abbruch** |

</div>

---

## Inhalt

- [Die teuren Fehlermuster](#die-teuren-fehlermuster)
- [Wie diese Skills aufgebaut sind](#wie-diese-skills-aufgebaut-sind)
- [Was es anders macht](#was-es-anders-macht)
- [Evaluationen](#evaluationen)
- [Schnellstart](#schnellstart)
- [Skills](#skills)
- [Verifikationsskripte](#verifikationsskripte)
- [Funktionsweise](#funktionsweise)
- [Aktualisierung](#aktualisierung)
- [Roadmap](#roadmap)
- [Mitwirken](#mitwirken)
- [Lizenz](#lizenz)

## Die teuren Fehlermuster

Die kostenintensivsten Fehler in KI-generiertem ROS 2-Code sind selten Syntaxfehler. Stattdessen handelt es sich um subtile Probleme, die auf den ersten Blick korrekt wirken:

| Fehlermuster | Was Sie sehen | Warum der Agent auf das Problem stößt |
| :--- | :--- | :--- |
| **Stiller Fehlschlag** | `ros2 topic hz` zeigt 30 Hz an; Ihr Callback wird jedoch nie ausgelöst | Ein Standard-Subscriber mit RELIABLE versucht sich mit einem BEST_EFFORT-Publisher zu verbinden. Der Code kompiliert und besteht das Code-Review, schlägt aber auf DDS-Middleware-Ebene fehl. |
| **Falsche Ground Truth** | `/cmd_vel` zeigt Vorwärtsbewegung an und `/odom` meldet Vorwärtsbewegung, aber der physische Roboter bewegt sich **rückwärts** | Der statische TF-Frame ist relativ zur physischen Montage invertiert. Nachgelagerte Komponenten rechnen korrekt *unter Verwendung der falschen Transformation*, ohne offensichtliche Fehler zu erzeugen. |
| **Veraltete API** | Der Code besteht das Review, schlägt aber zur Laufzeit beim Aufruf einer falschen Methode fehl | Der Agent verwendet veraltete Foxy- oder Humble-API-Methoden, die in Jazzy umbenannt oder entfernt wurden. |
| **Ungültige Prämisse** | Der Agent schreibt 200 Zeilen Code basierend auf einer Annahme, die Sie in einem einzigen Satz hätten korrigieren können | Kein Mechanismus fordert den Agenten auf, fehlende Details vor der Codegenerierung zu verifizieren. |

Weder Compiler, Linter noch Log-Analysen erkennen diese versteckten Probleme. Die Behebung jedes Fehlers erfordert einen zusätzlichen Feedback-Zyklus: Ausgabe überprüfen, Ursache diagnostizieren, Korrektur erklären und den Code erneut generieren.

## Wie diese Skills aufgebaut sind

Vier Entwurfsregeln bestimmen jeden Skill in diesem Repository:

**1. Unbekannte Variablen im Voraus identifizieren.** Wichtige betriebliche Details sind in der Dokumentation oft nicht vorhanden – etwa ob die Umgebung reale Hardware oder Simulation ist, ob ein bestehender Workspace erweitert oder ein neuer erstellt werden soll, welcher Node bereits eine Transformation publiziert oder die genaue Geometrie des Roboters. [`CLAUDE.md`](./CLAUDE.md) weist den Agenten an, diese Unbekannten vor der Codegenerierung zu klären. Domänenspezifische Skills verwalten gezielte Parameter; beispielsweise fordert `ros2-dev` die Footprint-Geometrie des Roboters, die Antriebskinematik und die Lokalisierungsquelle an, bevor Nav2-Parameter konfiguriert werden.

**2. Eine strukturierte Schleife mit klaren Abbruchkriterien ausführen.** Jeder Skill folgt einem *Verifizieren → Schreiben → Beweisen*-Zyklus: Systemstandards in der installierten Umgebung prüfen, inkrementelle Änderungen anwenden und die Ausführung bestätigen. Eine Aufgabe ist erst dann abgeschlossen, wenn sie durch beobachtbare Nachweise gestützt wird – wie etwa einen erfolgreichen Build, aktive Daten auf `ros2 topic echo` oder ein bestandenes Verifikationsskript – anstatt einfach nur Codedateien zu erzeugen.

**3. Strukturierte Fehlertabellen gegenüber langen Beschreibungen bevorzugen.** Strukturierte Tabellen, die Symptome → Ursachen → Korrekturmaßnahmen zuordnen, bieten eine klare, dauerhafte Orientierung, die in offiziellen Dokumentationen oft fehlt und über Release-Versionen hinweg zuverlässig bleibt:

> `[` ist GZ→ROS, `]` ist ROS→GZ · `16UC1` ist Millimeter, `32FC1` ist Meter · `joint_state_broadcaster` wird nicht automatisch gestartet · `raytrace_max_range` ≤ `obstacle_max_range` bedeutet, dass Hindernisse nie gelöscht werden · rclc alloziert unbegrenzte Nachrichtenfelder nicht automatisch

**4. Kontextnutzung mit einer Drei-Schichten-Architektur optimieren.** Jeder Skill balanciert die Kontexteffizienz: Skill-Beschreibungen bleiben im Kontext, Skill-Rümpfe laden bei Aufruf und tiefer gehende Referenzdateien in `references/` laden erst bei Bedarf. Große Symbolkataloge und detaillierte Parameter-Tuning-Tabellen befinden sich in `references/`, wodurch der Kontext geschont wird und beim Debuggen gezielter Komponenten (wie AMCL) keine unnötige Dokumentation (wie Behavior-Tree-Nodes) geladen wird.

## Was es anders macht

Die meisten Robotik-Skill-Pakete betten statisches API-Wissen direkt in Skill-Dateien ein. Während die erste Nutzung einfach ist, bricht dieser Ansatz zusammen, sobald die zugrunde liegenden Pakete aktualisiert werden – zurück bleiben veraltete Code-Snippets, die stillschweigend fehlschlagen. Dieses Repository verfolgt einen dynamischen, dokumentationsgesteuerten Ansatz:

| Merkmal | Inhaltslastige Skill-Pakete | **claude-ros2-skills** |
| :--- | :--- | :--- |
| Speicherort des Wissens | In Skill-Dateien eingebettet (**400–1.800 Zeilen/Skill**) | Verlinkt auf offizielle Doku (**~60-Zeilen** Skill-Rümpfe); detaillierte Referenzen **nur bei Bedarf** gelesen |
| Immer geladener Kontext | Vollständige `SKILL.md`-Dateien | **26-Zeilen** Kernprotokoll |
| Umgang mit Jazzy-API-Updates | Snippets veralten stillschweigend; erfordert kontinuierliche manuelle Test-Updates | Risiko veralteter Snippets auf Einstiegspunkt-Links und Symbolnamen minimiert — **38 Dokumentationslinks** wöchentlich per CI verifiziert |
| Verifikationsmethode | Statische Codeanalyse oder Log-Prüfung | **Physikalische & Laufzeit-Verifikation**: IMU-Gravitationsprüfungen, Richtungs-Odometrietests, TF-Frame-Ausrichtung, DDS-QoS-Kompatibilität |
| Unterstützungsbereich | Behauptet Unterstützung für mehrere ROS-Distros, zielt aber nur auf eine ab | **Nur ROS 2 Jazzy**, explizit entwickelt und validiert |

Dieses Repository ist auf ein einziges Ziel hin optimiert: das Risiko zu minimieren, plausibel aussehenden Code zu generieren, der auf ROS 2 Jazzy nicht ausgeführt werden kann.

## Evaluationen

Jedes unten stehende Ergebnis stammt aus einem gemessenen A/B-Paar: Der **identische Prompt** wurde in frischen, headless Claude Code-Sitzungen ausgeführt – einmal ohne diese Skills, einmal mit ihnen – unter Verwendung desselben **gleichen Modells** in beiden Durchläufen. Die Ausgaben wurden Symbol für Symbol gegen gepinnte Upstream-Jazzy-Quellen abgeglichen, anschließend gegen die Live-Installation unter `/opt/ros/jazzy` in einem `ros:jazzy` Docker-Container und schließlich durch Laden beider Ausgaben in eine **Live-Gazebo-Simulation**. Vollständige Transkripte und Artefakte sind unter [`evals/runs/`](./evals/runs/) hinterlegt, sodass jeder die Ergebnisse unabhängig nachprüfen kann.

### Nav2 MPPI-Konfiguration — Haiku, Live-Jazzy-Installation

*Prompt: richte Nav2 mit dem MPPI-Controller für einen Differentialantrieb-Roboter auf Jazzy ein und erstelle die YAML-Datei für den Controller Server.*

| | Ohne Skills | Mit Skills |
| :--- | :--- | :--- |
| Prozess | Sofort aus dem Gedächtnis beantwortet; **null** Verifikation, obwohl Werkzeuge verfügbar waren | Fragte **zuerst** nach Footprint, bestehender Konfiguration, Lokalisierung und Geschwindigkeitsgrenzen, las dann die mitgelieferten Standardwerte unter `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml` |
| Plugin-String | `mppi_generic::ControllerServer` — existiert nicht | `nav2_mppi_controller::MPPIController` — korrekt |
| `critics:`-Liste | Fehlt vollständig | Alle 8 vorhanden, korrekte Namen |
| Erfundene Parameter-Keys | **~16** | **0** — jeder Schlüssel mechanisch gegen die installierten Standardwerte verglichen |
| **In eine Live-Gazebo-Simulation geladen** | **`[FATAL] Failed to create controller … does not exist` — Nav2 bricht beim Bringup ab; der Roboter bewegt sich nie** | **MPPI + alle 8 Critics werden geladen; Roboter fährt (−2,0, −0,5) → (0,5, 0,5); `NavigateToPose` gibt `SUCCEEDED` zurück** |

### Ein Paket, das tatsächlich laufen muss — Haiku, im Container

*Prompt: erstelle ein Python-Paket `demo_pkg`, das `std_msgs/msg/String` auf `/greeting` mit 1 Hz über eine Launch-Datei publiziert; baue es und zeige `ros2 topic echo /greeting`.*

| | Ohne Skills | Mit Skills |
| :--- | :--- | :--- |
| `ros2 run` / `ros2 launch` / `topic echo` | **Alle drei schlagen fehl** — das Paket wird nie im ament index registriert | **Alle drei erfolgreich**, bestätigt durch unabhängige erneute Ausführung jedes Befehls |
| Kosten für dieses Ergebnis | 0,17 $ · 36 Aufrufe · 178 s | **0,08 $ · 18 Aufrufe · 61 s** — im ersten Anlauf korrekt und **2,2-mal günstiger** |

### Sensor-Abonnement — Sonnet

| | Ohne Skills | Mit Skills |
| :--- | :--- | :--- |
| `/scan`-Callback auf einem physischen BEST_EFFORT LiDAR | **Wird nie ausgelöst** — Standard RELIABLE QoS weicht auf DDS-Ebene stillschweigend ab | **Funktioniert** — `qos_profile_sensor_data`, plus Bereichsfilterung |

### Das Muster über jedes Paar hinweg

Baseline-Sitzungen nutzten in jedem Durchlauf **keinerlei** Verifikationswerkzeuge, selbst wenn WebFetch, Read und Bash explizit erlaubt waren – und eine Baseline meldete einen voll funktionsfähigen Build für ein Paket, das `ros2 run` gar nicht finden kann. Sitzungen mit diesen Skills verifizierten in **jedem** Durchlauf vor dem Schreiben, und ihre Aussagen stimmten mit der unabhängigen erneuten Ausführung überein. Die Verifikationsskripte der Skills wurden selbst an der Live-Simulation validiert: TF-Tree-, QoS-Kompatibilitäts- und Odometrie-Richtungsprüfungen wurden alle auf echten Daten bestanden, und das Szenario mit einem umgedrehten LiDAR wurde exakt wie vorgesehen erkannt.

Lesen Sie die vollständigen Evaluationstabellen, Testumgebungen und einzelnen Laufanalysen in [`evals/RESULTS.md`](./evals/RESULTS.md). Details zum Evaluationsprotokoll, Checklisten für Aufgaben und Container-Setup finden Sie unter [`evals/README.md`](./evals/README.md). Pull-Requests mit weiteren bewerteten Transkripten sind willkommen.

## Schnellstart

**Option A — Plugin Marketplace (Empfohlen):**

```
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

Aktualisieren Sie installierte Plugins jederzeit mit `/plugin marketplace update`.

**Option B — Manuelle Installation:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git

# Projektbasierte Installation (gilt nur für das aktuelle Projekt)
mkdir -p your-project/.claude/skills
cp -r claude-ros2-skills/skills/* your-project/.claude/skills/
cp claude-ros2-skills/CLAUDE.md your-project/

# Benutzerweite Installation (gilt für alle Projekte)
mkdir -p ~/.claude/skills
cp -r claude-ros2-skills/skills/* ~/.claude/skills/
```

Starten Sie Claude Code neu (oder beginnen Sie eine neue Sitzung), um die installierten Skills anzuwenden.

## Skills

| Skill | Pfad | Abdeckung |
| :--- | :--- | :--- |
| **ros2-core** | `skills/ros2-core/SKILL.md` | rclcpp, rclpy, TF2, EKF-Odometrie, QoS-Profile, Parameter |
| **ros2-package** | `skills/ros2-package/SKILL.md` | `ros2 pkg create`, CMakeLists/setup.py-Einbindung, colcon build & source, benutzerdefinierte Interfaces |
| **ros2-dev** | `skills/ros2-dev/SKILL.md` | Nav2 (AMCL, Costmaps, MPPI/Smac), SLAM Toolbox, RTAB-Map, Isaac ROS |
| **gazebo-sim** | `skills/gazebo-sim/SKILL.md` | Gazebo Harmonic, ros_gz_bridge, ros_gz_sim, SDFormat-Modellierung |
| **ros2-control** | `skills/ros2-control/SKILL.md` | ros2_control Hardware-Abstraktion, Controller Manager, URDF-Tags |
| **ros2-moveit** | `skills/ros2-moveit/SKILL.md` | MoveIt 2, MoveGroup C++/Python-API, IK-Solver, OMPL, MoveIt Servo |
| **ros2-perception** | `skills/ros2-perception/SKILL.md` | image_transport, cv_bridge, vision_msgs, depth_image_proc, PCL |
| **ros2-testing** | `skills/ros2-testing/SKILL.md` | launch_testing, gtest/pytest, rosbag2 C++/Python-APIs, ros2trace |
| **ros2-microros** | `skills/ros2-microros/SKILL.md` | micro-ROS Agent, rclc Client-API, benutzerdefinierte Transporte, statischer Speicher |
| **ros2-security** | `skills/ros2-security/SKILL.md` | SROS2, PKI-Keystore-Erstellung, Zugriffskontrolle, DDS-Sicherheit |
| **ros2-troubleshooting** | `skills/ros2-troubleshooting/SKILL.md` | REP 103/105 Ground-Truth-TF-Baum, LiDAR/IMU-Ausrichtung, physikalische Verifikation |

## Verifikationsskripte

Diese Verifikationsskripte sind im `ros2-troubleshooting`-Skill (`skills/ros2-troubleshooting/scripts/`) gebündelt und bei jeder Installation enthalten. Sie wandeln physikalische Hardware-Prüfungen in ausführbare Erfolgs-/Fehlerschritte (PASS/FAIL) um (erfordert eine gesourcte ROS 2-Umgebung; Rückgabecodes: 0 = PASS, 1 = FAIL, 2 = NO DATA):

| Skript | Verifiziert |
| :--- | :--- |
| `check_imu_gravity.py` | Validiert, dass ein ruhender Roboter die Schwerkraft mit ~+9,81 m/s² entlang der **+Z**-Achse misst (REP 103). Erkennt invertierte oder fehlausgerichtete IMU-Montagen. |
| `check_odom_direction.py` | Validiert, dass das Vorwärtsschieben des Roboters eine positive Odometrieverschiebung in Ausrichtungsrichtung erzeugt. Erkennt invertierte Drehrichtungen der Motoren, Polaritätsprobleme der Encoder oder invertierte TF-Setups. |
| `check_tf_tree.py` | Verifiziert, dass `map→odom→base_link` korrekt aufgelöst wird; zeigt jeden Sensormontage-Offset in RPY-Grad an und hebt potenzielle 180°-Orientierungsfehler hervor. |
| `check_qos_compat.py` | Verifiziert die QoS-Kompatibilität über alle Publisher/Subscriber-Paare auf einem Topic unter Verwendung von DDS-Regeln. Verhindert stille Fehlschläge (z. B. ein BEST_EFFORT-Publisher gepaart mit einem RELIABLE-Subscriber oder Abweichungen bei Durability, Deadline und Liveliness). |

Die Kern-Entscheidungslogik wird unabhängig von ROS per Unit-Test geprüft (`python3 skills/ros2-troubleshooting/scripts/test_checks.py`) und läuft bei jedem Push über Continuous Integration (CI).

## Funktionsweise

```mermaid
flowchart LR
    A["Ihre Anfrage"] --> B["CLAUDE.md<br/>Protokoll + Schranken,<br/>keine API-Details"]
    B --> C["skills/&lt;name&gt;/SKILL.md<br/>Schranken, Schleife,<br/>Fehlertabellen"]
    C --> D["/opt/ros/jazzy/<br/>oder offizielle Jazzy-Doku"]
    C -.nur bei Bedarf.-> R["references/<br/>Symbolkataloge,<br/>Tuning-Tabellen"]
    D --> E["Code, dann Nachweis der Ausführung"]
    R --> E
```

`CLAUDE.md` enthält keine spezifischen API-Details. Stattdessen etabliert es das Betriebsprotokoll und fordert, dass klärende Fragen vor dem Schreiben von Code beantwortet werden. Jede `SKILL.md`-Datei verwaltet domänenspezifische Entscheidungen: Unbekannte Variablen identifizieren, die Schleife aus Verifizieren-Schreiben-Beweisen ausführen und auf Fehlertabellen verweisen. Detaillierte Referenzmaterialien werden separat im Verzeichnis `references/` gespeichert. Siehe [`CLAUDE.md`](./CLAUDE.md) für Details.

## Aktualisierung

```bash
cd claude-ros2-skills
git pull
cp -r skills/* ~/.claude/skills/   # oder das .claude/skills/-Verzeichnis Ihres Projekts
```

## Roadmap

1. ~~Evaluationspaare innerhalb von `ros:jazzy`-Containern automatisieren~~ — **erledigt (25.07.2026):** Erneuter Durchlauf von Aufgabe 4 gegen eine Live-Installation von `/opt/ros/jazzy`; Ergebnisse in [`evals/RESULTS.md`](./evals/RESULTS.md).
2. ~~Evaluationsergebnisse für Aufgabe 5 veröffentlichen~~ — **erledigt (25.07.2026):** Binäres Build/Run/Echo-Ergebnis im Container gemessen; Ergebnisse in [`evals/RESULTS.md`](./evals/RESULTS.md).
3. **Container-Evaluationen auf die Aufgaben 1–3 ausweiten**, sodass jede Aufgabe in der Testsuite eine Messung auf einer Live-Installation aufweist.
4. **„Korrekturen bis zur Fertigstellung“ als Kernmetrik erfassen** — Messung der Anzahl der Feedback-Iterationen, die erforderlich sind, bevor der Code erfolgreich läuft.
5. **Deterministische `references/`-Lookups implementieren**, um sicherzustellen, dass detaillierte Referenzdokumente geladen werden, wann immer sie relevant sind.
6. **Die Aufteilung in Rumpf/`references` auf `ros2-core` und `gazebo-sim` ausdehnen**, um die Kontexteffizienz für hochfrequente Skills mit umfangreicher Referenzdokumentation zu optimieren.

## Mitwirken

Zusammenfassung: Skill-Dateien müssen sich auf die Entscheidungslogik konzentrieren (Validierungsschranken, Schleifenschritte und Fehlertabellen), während detaillierte Dokumentationen in `references/` verbleiben. Jedes API-Symbol muss gegen die offizielle Jazzy-Dokumentation oder `/opt/ros/jazzy/`-Installationen verifiziert werden. Verifikationsskripte müssen reine Logik beibehalten, die ohne ROS-Abhängigkeiten per Unit-Test geprüft werden kann. Die vollständigen Richtlinien, Checklisten für Skills und Skripte sowie Issue-Vorlagen finden Sie unter [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Lizenz

Apache-2.0 — siehe [LICENSE](./LICENSE).
