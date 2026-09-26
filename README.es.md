<div align="center">

<img src="assets/hero.png" alt="ROS 2 Jazzy skills for Claude Code and Codex" width="100%"/>

**Empaquetado contextual de herramientas de verificación, flujos de trabajo y pruebas de traspaso para ROS 2.**

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | **Español** | [Français](README.fr.md) | [Deutsch](README.de.md)

</div>

Tres skills para **Claude Code y Codex** dirigidos a **Ubuntu 24.04 / ROS 2 Jazzy**: desarrollar paquetes, verificar pruebas y artefactos instalados, y diagnosticar fallos en tiempo de ejecución.

Este repositorio empaqueta conocimiento de dominio, flujos de trabajo y diagnósticos ejecutables bajo el estándar [Agent Skills](https://agentskills.io/home). En lugar de afirmar que mejora las capacidades intrínsecas de generación de código de los modelos de frontera, este proyecto explora una hipótesis de ingeniería: **empaquetar comprobaciones de evidencia específicas del entorno y registros estructurados de traspaso (handoff) puede reducir la ambigüedad en la verificación y el coste de transferencia de contexto entre sesiones o colaboradores.** Aunque la funcionalidad de las herramientas individuales está validada en pruebas controladas, **la reducción del coste de traspaso y las ganancias globales de productividad siguen siendo hipótesis no demostradas.**

## Inicio rápido

Se admite el descubrimiento automático de skills (skill discovery) en todos los entornos.

**Codex — Instalación en un proyecto:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# Para instalación global de usuario:
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

Se instalan en `<proyecto>/.agents/skills` o `~/.agents/skills`, cargando el [protocolo de verificación](CLAUDE.md) compartido. Se conservan las configuraciones existentes y otros skills.

**Claude Code — Instalación de plugin:**

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

## Skills disponibles

| Skill | Cuándo ayuda | Qué aporta |
| :--- | :--- | :--- |
| [ros2-development](skills/ros2-development/SKILL.md) | Crear o modificar paquetes, nodos, interfaces, launch, configuración y pruebas | Compilaciones con dependencias, comprobación de artefactos instalados, rechazo de ejecuciones sin pruebas y herramienta opcional de seguimiento de evidencias para traspasos |
| [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md) | Fallos de ejecución en publicadores, callbacks, TF, IMU u odometría | Cuatro diagnósticos ejecutables y referencias directas sobre marcos (REP 103/105), QoS y calibración |
| [ros2-microros](skills/ros2-microros/SKILL.md) | Transporte MCU, agente, rclc, memoria de mensajes | Puntos de entrada y guía de diagnóstico; **no validado en hardware MCU** |

## Herramientas ejecutables de verificación y evidencia

Los scripts se incluyen dentro de cada skill. En los ejemplos, `ROS2_SKILL_DIR` es una variable ilustrativa establecida internamente por el agente según el directorio cargado; no requiere entrada del usuario.

| Script | Propósito y evidencia comprobada |
| :--- | :--- |
| `ros2-development/scripts/check_test_results.py` | Comprueba pruebas ejecutadas y aprobadas en reportes limpios de colcon (rechaza pruebas vacías) |
| `ros2-development/scripts/evidence.py begin / finish / inspect` | **Flujo opcional (opt-in)**: Registra metadatos declarados por el invocador y compara hashes de archivos y valores de entorno seleccionados para facilitar traspasos |
| `ros2-troubleshooting/scripts/check_qos_compat.py --topic /scan` | Compatibilidad QoS nativa en Jazzy para pares publicador/suscriptor |
| `ros2-troubleshooting/scripts/check_tf_tree.py --sensors laser_frame,imu_link` | Conectividad TF y ángulos RPY para comparación física |
| `ros2-troubleshooting/scripts/check_imu_gravity.py --topic /imu/data` | Gravedad en reposo sobre superficie nivelada transformada a `--base base_link` |
| `ros2-troubleshooting/scripts/check_odom_direction.py --topic /odom` | Dirección de odometría reciente antes y después de un movimiento observado |

**Códigos de salida de diagnóstico: 0 APROBADO, 1 FALLO, 2 NO CONCLUYENTE o solicitud inválida.**
**Códigos de salida de inspección de evidencia: 0 Coherente (Consistent), 1 Modificado (Changed), 2 Incompleto (Incomplete).**
La herramienta de evidencia separa estrictamente los resultados declarados por el invocador de los hashes observados por la herramienta. No ejecuta ni reejecuta comandos, no garantiza frescura ni ausencia de cambios intermedios, y no prueba el estado general del robot. Consulte [docs/DESIGN.md](docs/DESIGN.md).

## Límites de validación

En evaluaciones anteriores con Claude Code Opus 5.5 High, tanto el uso de skills como la línea base superaron las mismas tareas. En el estudio de migración de interfaces ([RESULTS.md](evals/workflow_value/RESULTS.md)), las sesiones con skills fueron más rápidas, pero las limitaciones de muestra y caché **no demuestran causalmente una mejora de velocidad, fiabilidad o capacidad de programación**.

Los robots físicos, el firmware MCU y las aplicaciones completas de Nav2/MoveIt permanecen sin verificar.

## Contribución y licencia

[CONTRIBUTING.md](CONTRIBUTING.md) · [evals/AUTHORING.md](evals/AUTHORING.md) · [Apache-2.0](LICENSE).
