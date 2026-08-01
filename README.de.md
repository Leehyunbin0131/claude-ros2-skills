<div align="center">

<img src="assets/hero.png" alt="claude-ros2-skills — Claude Code skills for ROS 2 Jazzy" width="100%"/>

**Claude Code Skills for ROS 2 Jazzy Jalisco robotics development.**

Skills, die verändern, wie KI-Agenten ROS-2-Entwicklung angehen: unbekannte Parameter vorab klären, Konfigurationen gegen die installierten Pakete prüfen und die Ausführung durch Belege für tatsächliches Funktionieren bestätigen.

![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?logo=ubuntu&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | **Deutsch**

<sub>🌐 Dieses Dokument ist die deutsche Übersetzung des Originals auf [English](README.md).</sub>

| Skills | Immer geladenes Protokoll | Doku-Links (CI-geprüft) | Skripte für physische & Laufzeit-Verifikation |
| :---: | :---: | :---: | :---: |
| **2** | **30 Zeilen** | **6** | **4** |

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
- [Mitwirken](#mitwirken)
- [Lizenz](#lizenz)

## Die teuren Fehlermuster

Die kostspieligsten Fehler in KI-generiertem ROS-2-Code sind selten Syntaxfehler. Es sind subtile Probleme, die auf den ersten Blick korrekt aussehen:

| Fehler | Was man sieht | Warum ein Agent darauf hereinfällt |
| :--- | :--- | :--- |
| **Middleware-Mismatch** | `ros2 topic hz` zeigt 30 Hz; der Callback feuert nie | Ein standardmäßig RELIABLE eingestellter Subscriber kann sich nicht mit einem BEST_EFFORT-Publisher paaren. Der Code kompiliert, besteht das Review und scheitert unterhalb der Anwendungsebene. rclpy warnt zwar — `offering incompatible QoS ... Last incompatible policy: RELIABILITY` — aber nur zur Laufzeit, im Startlog, für den, der es liest. |
| **Falsche Referenz** | `/cmd_vel` gibt Vorwärtsfahrt vor und `/odom` meldet Vorwärtsfahrt, doch der reale Roboter fährt **rückwärts** | Der statische TF-Frame ist gegenüber der physischen Montage invertiert. Nachgelagerte Komponenten rechnen korrekt — *mit der falschen Transformation* — und erzeugen keine erkennbaren Fehler. |
| **Veraltete API** | Der Code besteht das Review, scheitert aber zur Laufzeit beim Aufruf einer falschen Methode | Der Agent verwendet Foxy- oder Humble-Methoden, die in Jazzy umbenannt oder entfernt wurden. |
| **Falsche Prämisse** | Der Agent schreibt 200 Zeilen auf Basis einer Annahme, die Sie mit einem Satz korrigiert hätten | Nichts zwingt den Agenten, fehlende Details vor der Codegenerierung zu klären. |

Weder Compiler noch Linter noch Log-Analysen erkennen diese verborgenen Probleme. Jede Behebung kostet einen zusätzlichen Rückkopplungszyklus: Ausgabe prüfen, Ursache diagnostizieren, Korrektur erklären, neu generieren.

## Wie diese Skills aufgebaut sind

Vier Entwurfsregeln gelten für jeden Skill in diesem Repository:

**1. Unbekannte Variablen vorab identifizieren.** Zentrale betriebliche Details stehen oft in keiner Dokumentation — ob die Umgebung reale Hardware oder Simulation ist, ob ein bestehender Workspace erweitert oder ein neuer angelegt wird, welcher Node bereits eine Transformation publiziert, oder wie die genaue Geometrie des Roboters aussieht. [`CLAUDE.md`](./CLAUDE.md) weist den Agenten an, diese Unbekannten vor der Codegenerierung zu klären.

**2. Eine strukturierte Schleife mit klaren Abbruchkriterien ausführen.** Der Zyklus *prüfen → schreiben → nachweisen*: Standardwerte in der installierten Umgebung inspizieren, Änderungen schrittweise anwenden, Ausführung bestätigen. Eine Aufgabe gilt erst als abgeschlossen, wenn beobachtete Belege sie stützen — ein erfolgreicher Build, echte Daten auf `ros2 topic echo`, ein bestandenes Verifikationsskript — und nicht schon durch das bloße Erzeugen von Codedateien.

**3. Nichts sagen, was das Modell bereits weiß oder `CLAUDE.md` bereits festlegt.** Jede Symptom→Ursache→Maßnahme-Tabelle, die früher in diesem Paket enthalten war, wurde gegen einen Basis-Agenten ohne geladene Skills evaluiert. Beschreibende Prosa hat die Evaluationsergebnisse nie verbessert — das Modell erreicht die Lösung entweder eigenständig oder benötigt ein ausführbares Skript bzw. eine Protokoll-Bedingung in `CLAUDE.md`. Siehe [Evaluationen](#evaluationen).

**4. Auf ein ausführbares Artefakt zeigen, es niemals beschreiben.** Empirische Tests haben gezeigt, dass beschreibender Text darüber, was ein Skript prüfen würde, keine Verbesserung in den Evaluationen brachte. Nur ausführbare Skripte mit deterministischen Exit-Codes (`scripts/check_*.py` in `ros2-troubleshooting`) haben das Verhalten des Modells messbar verändert.

## Was es anders macht

Die meisten Robotik-Skill-Pakete betten statisches API-Wissen direkt in die Skill-Dateien ein. Die anfängliche Nutzung ist bequem, doch der Ansatz bricht, sobald die zugrunde liegenden Pakete aktualisiert werden — zurück bleiben veraltete Snippets, die stillschweigend versagen. Dieses Repository verfolgt einen dynamischen, dokumentationsgetriebenen Ansatz:

| Merkmal | Inhaltsschwere Skill-Pakete | **claude-ros2-skills** |
| :--- | :--- | :--- |
| Ort des Wissens | In Skill-Dateien eingebettet (**400–1.800 Zeilen pro Skill**) | Auf offizielle Dokumentation verlinkt (**~60 Zeilen** Skill-Rumpf); ausführliche Referenzen werden **nur bei Bedarf** gelesen |
| Immer geladener Kontext | Vollständige `SKILL.md`-Dateien | **30-zeiliges** Kernprotokoll |
| Umgang mit Jazzy-API-Änderungen | Snippets veralten stillschweigend; laufende manuelle Pflege nötig | Veraltungsrisiko auf Einstiegslinks und Symbolnamen begrenzt — **6 Dokumentationslinks**, wöchentlich per CI geprüft |
| Verifikationsmethode | Statische Codeanalyse oder Log-Prüfung | **Physikalische und Laufzeit-Verifikation**: IMU-Schwerkraftprüfung, gerichteter Odometrietest, TF-Frame-Ausrichtung, DDS-QoS-Kompatibilität |
| Verteilungsumfang | Bewirbt Unterstützung mehrerer ROS-Distributionen, zielt real auf eine | Konstruktionsbedingt **nur ROS 2 Jazzy** — ohne „läuft auch unter Humble"-Ausweichen |

Dieses Repository optimiert auf ein einziges Ergebnis: das Risiko zu minimieren, plausibel aussehenden Code zu erzeugen, der unter ROS 2 Jazzy nicht läuft.

## Evaluationen

**Der Maßstab.** Ein Skill verdient seinen Platz nur, wenn er etwas liefert, das der Agent **nicht selbst erreichen kann** — und zwar mit eigenem Wissen, Websuche und einer realen Jazzy-Installation vor sich. Text, der dem Agenten nur mitteilt, was er ohnehin getan hätte, ist Kosten ohne Nutzen.

**Wie gemessen wird.** Eine reale Aufgabe in einem sauberen Container, zehn Durchläufe mit dem geprüften Element und zehn ohne, bewertet durch *Ausführen* des Ergebnisses — ein Build, ein Topic mit Daten, ein Exit-Code — niemals durch Lesen. Exakter Test nach Fisher, Benjamini–Hochberg-Korrektur über die gesamte Runde.

**Was das geklärt hat.** Acht Domänen wurden auf eine dreistufige Leiter gestellt — 24 Sprossen insgesamt, jede fügt einen benannten Mechanismus hinzu und wird von einer Prüfung bewertet, die das Artefakt ausführt. Der Basis-Agent erreichte **jeden Mechanismus, der von ihm verlangt wurde**:

| Domäne | L1 → L2 → L3, pro Sprosse ergänzte Mechanismen | Ohne Hilfe |
| :--- | :--- | ---: |
| Packaging und Build | `ament_python`/`ament_cmake` → paketübergreifende `.srv` → komponierbarer Node + `colcon test` | **190/190** |
| Simulation | SDF-Welt + Differentialantrieb → `ros_gz_bridge` + `gpu_lidar` → URDF-Spawn + `use_sim_time` | **108/110** |
| Executors | 1-s-Service aus einem Timer → aus einem Subscription-Callback + Heartbeat → 5 nebenläufige Aufrufe | **110/110** |
| `ros2_control` | Mock-Hardware + Broadcaster → zweiter Controller, der Interfaces beansprucht → **eigenes C++-`SystemInterface`-Plugin** | **90/90** |
| Testing | pytest, den `colcon test` tatsächlich ausführt → `launch_testing` gegen einen laufenden Node → rosbag2 geschrieben und zurückgelesen | **110/110** |
| MoveIt 2 | Selbst verfasste URDF+SRDF, die `move_group` lädt → echter `GetMotionPlan` → Kollisionsobjekt in der Planungsszene | **100/100** |
| Kern | Statische TF aus Parametern → dynamische TF + `ExtrapolationException` → Lifecycle-Node, der bis zur Aktivierung schweigt | **110/110** |
| Nav2 | Parameterdatei, die die Server unverändert akzeptieren → Stack bis `active` gefahren → Costmap, die Hindernisse aus Live-Scans markiert | siehe unten |
| Perception | `cv_bridge`-Rundlauf → `CameraInfo`-Projektion → 16UC1-Tiefe → `PointCloud2` | **106/120** |

**Kein einziger Fehler wurde durch Bereitstellen von Information geschlossen.** Vier Lücken wurden gefunden, allesamt verhaltensbezogen:

| Was das Modell ohne Hilfe nicht tut | Basis | Was es schloss | Danach |
| :--- | ---: | :--- | ---: |
| Gegen die Installation prüfen, statt aus dem Gedächtnis zu antworten | **2/10** | ein Absatz in `CLAUDE.md` | **10/10** (q=0,002) |
| Ein Urteil mit Exit-Code liefern statt „sieht richtig aus" | **0/10** | ein mitgeliefertes ausführbares Skript | **10/10** (q<0,001) |
| Den geschriebenen QoS-Code vor der Übergabe ausführen | **5/10** | das „fertig heißt, es lief" aus `CLAUDE.md` | **9/10** (zu geringe Teststärke) |
| Die geschriebene Nav2-Konfiguration vor der Übergabe ausführen | **0/10** | eine Aufgabe, die das Erreichen von `active` verlangt | **30/30** |

Die letzte Zeile verdeutlicht dieses Prinzip am klarsten. Auf die Aufforderung hin, nur eine Nav2-Parameterdatei zu erstellen, erzeugten alle 10 Durchläufe Konfigurationen, die ihre eigenen Nav2-Server zu laden verweigerten. Auf die Aufforderung hin, dieselbe Datei zu erstellen *und zusätzlich* den Stack in den Zustand `active` zu bringen, stieß jeder Durchlauf auf genau denselben Konfigurationsfehler, diagnostizierte ihn aus den Logs, behob ihn und bestand. **Gleiches Modell, gleiche Fehlvorstellung, null Unterschied an Information** — nur die Anforderung, auszuführen und zu verifizieren, unterschied sich.

**Konsequenz für dieses Paket.** Sechs Domänen-Skills wurden vollständig entfernt, zusätzlich zu den beiden zuvor entfernten: Das Modell erreicht diese Inhalte bereits eigenständig, und keine beschreibende Prosa in diesem Repository hat je eine Evaluationsprüfung verbessert. Übrig bleiben ein 30-zeiliges Protokoll, vier ausführbare Skripte und das Referenzmaterial dahinter. Methode, Ergebnisse je Domäne und Rohdurchläufe: [`evals/`](./evals/).

## Schnellstart

**Option A — Plugin-Marketplace (empfohlen):**

```
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

Installierte Plugins lassen sich jederzeit mit `/plugin marketplace update` aktualisieren.

**Option B — Manuelle Installation:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git

# Installation auf Projektebene (gilt nur für das aktuelle Projekt)
mkdir -p your-project/.claude/skills
cp -r claude-ros2-skills/skills/* your-project/.claude/skills/
cp claude-ros2-skills/CLAUDE.md your-project/

# Installation auf Benutzerebene (gilt für alle Projekte)
mkdir -p ~/.claude/skills
cp -r claude-ros2-skills/skills/* ~/.claude/skills/
```

Starten Sie Claude Code neu (oder beginnen Sie eine neue Sitzung), um die installierten Skills zu übernehmen.

## Skills

| Skill | Pfad | Abdeckung |
| :--- | :--- | :--- |
| **ros2-troubleshooting** | `skills/ros2-troubleshooting/SKILL.md` | Vier ausführbare Bestanden/Durchgefallen-Prüfungen — QoS-Kompatibilität, TF-Baum, IMU-Montage, Odometrierichtung — sowie die dahinterliegenden REP-103/105-Frame-Konventionen, das Laufzeitverhalten von Jazzy und die Odometrie-Kalibrierung an realer Hardware |
| **ros2-microros** | `skills/ros2-microros/SKILL.md` | micro-ROS-Agent, rclc-Client-API, eigene Transporte, statischer Speicher |

**Warum nur zwei.** Alle anderen Skills wurden gegen einen Basis-Agenten ohne geladene Skills gemessen und entfernt, sobald der Agent ohne sie dasselbe Ergebnis lieferte — `ros2-core`, `ros2-dev`, `ros2-control`, `ros2-moveit`, `ros2-perception`, `ros2-testing`, `ros2-package` und `gazebo-sim`, in dieser Messreihenfolge. `ros2-microros` ist die einzige Domäne ohne Leiter: Die Hardware, um eine solche auszuführen, steht hier nicht zur Verfügung, daher bleibt der Skill erhalten und **wird nicht als verifiziert ausgewiesen**. Siehe [Evaluationen](#evaluationen).

## Verifikationsskripte

Diese Skripte sind im Skill `ros2-troubleshooting` enthalten (`skills/ros2-troubleshooting/scripts/`) und werden mit jeder Installation ausgeliefert. Sie überführen physikalische Hardwareprüfungen in ausführbare Bestanden/Durchgefallen-Schritte (erfordert eine gesourcte ROS-2-Umgebung; Rückgabewerte: 0 = BESTANDEN, 1 = DURCHGEFALLEN, 2 = KEINE DATEN):

| Skript | Verifiziert |
| :--- | :--- |
| `check_imu_gravity.py` | Dass ein ruhender Roboter die Schwerkraft mit ~+9,81 m/s² entlang der **+Z**-Achse misst (REP 103). Erkennt invertierte oder fehlausgerichtete IMU-Montagen. |
| `check_odom_direction.py` | Dass Vorwärtsschieben des Roboters eine positive Odometrieverschiebung entlang seiner Fahrtrichtung erzeugt. Erkennt invertierte Motorrichtungen, Encoder-Polaritätsprobleme oder invertierte TF-Konfigurationen. |
| `check_tf_tree.py` | Dass `map→odom→base_link` korrekt auflöst; zeigt den Montage-Offset jedes Sensors in RPY-Grad und hebt mögliche 180°-Orientierungsfehler hervor. |
| `check_qos_compat.py` | Die QoS-Kompatibilität aller Publisher-/Subscriber-Paare eines Topics nach DDS-Regeln. Verhindert stille Fehler (etwa BEST_EFFORT-Publisher zusammen mit RELIABLE-Subscriber oder Abweichungen bei Durability, Deadline und Liveliness). |

Die zentrale Entscheidungslogik wird unabhängig von ROS unit-getestet (`python3 skills/ros2-troubleshooting/scripts/test_checks.py`) und läuft bei jedem Push über Continuous Integration (CI).

## Funktionsweise

```mermaid
flowchart LR
    A["Ihre Anfrage"] --> B["CLAUDE.md<br/>Protokoll + Prüfpunkte,<br/>keine API-Details"]
    B --> D["/opt/ros/jazzy/<br/>oder offizielle Jazzy-Doku"]
    B -.Laufzeitfehler.-> C["ros2-troubleshooting<br/>ausführbare Prüfungen"]
    C -.nur bei Bedarf.-> R["references/<br/>frames, runtime,<br/>calibration"]
    D --> E["Code, und der Beleg, dass er lief"]
    C --> E
    R --> E
```

[`CLAUDE.md`](./CLAUDE.md) enthält keine konkreten API-Details. Stattdessen legt es das operative Protokoll fest: Konfigurationen gegen die lokale Umgebung verifizieren, betriebliche Unbekannte vorab klären und eine Aufgabe erst dann als abgeschlossen betrachten, wenn eine Ausführung beobachtet wurde. Das Domänenwissen bleibt dem Modell und der installierten Umgebung überlassen, da empirische Evaluationen zeigten, dass beschreibende Prosa keinen Mehrwert bot. Der `ros2-troubleshooting`-Skill wird nur aufgerufen, wenn ein System in den Logs unauffällig aussieht, aber zur Laufzeit fehlschlägt, und liefert handlungsfähige Exit-Codes statt beschreibenden Textes. Einzelheiten in [`CLAUDE.md`](./CLAUDE.md).

## Aktualisierung

```bash
cd claude-ros2-skills
git pull
cp -r skills/* ~/.claude/skills/   # oder das .claude/skills/ Ihres Projekts
```

## Mitwirken

**Zusammenfassung:** Neue Skill-Inhalte müssen ihren Wert gegenüber einem Basis-Agenten ohne Hilfe durch empirische Tests nachweisen (eine reale Aufgabe, 10 Durchläufe je Bedingung, bewertet durch Ausführen der Ausgabe). Inhalte, die das Modell ohne Hilfe erzeugt, werden nicht aufgenommen, unabhängig von ihrer Korrektheit. Verifikationsskripte müssen ihre Entscheidungslogik rein halten, damit sie unabhängig von ROS unit-getestet werden können. Für das Evaluationsprotokoll, Checklisten und Issue-Vorlagen siehe [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Lizenz

Apache-2.0 — siehe [LICENSE](./LICENSE).
