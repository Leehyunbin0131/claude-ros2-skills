# Desarrollo ROS 2 con pruebas de funcionamiento

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Français](README.fr.md) | [Deutsch](README.de.md)

Tres skills de Claude Code y Codex para Ubuntu 24.04 / ROS 2 Jazzy: desarrollar paquetes, comprobar pruebas y artefactos instalados, y diagnosticar fallos de ejecución. Respetan las convenciones del proyecto y consultan la documentación instalada cuando hace falta.

## Instalación

### Instalar en Codex

Tras clonar el repositorio, ejecute el comando siguiente. Se instala en `.agents/skills` del proyecto; sustituya `--project` por `--user` para usar `~/.agents/skills`. Cada skill incluye el protocolo compartido, que se carga al utilizarlo. Se conservan `AGENTS.md`, `CLAUDE.md` y la configuración existente. Inicie una sesión nueva en el proyecto. En CLI/IDE puede invocar `$ros2-development`. Consulte la [validación de Codex](evals/CODEX.md). El plugin y los comandos manuales predeterminados siguientes son para Claude Code.

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --agent codex --project /path/to/your-workspace
# python3 claude-ros2-skills/scripts/install.py --agent codex --user
```

### Claude Code

Elige un método. Para el plugin, ejecuta en una sesión de Claude Code:

```text
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

Instalación manual en un proyecto existente:

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git
python3 claude-ros2-skills/scripts/install.py --project /path/to/your-workspace
# --user: alternative to --project
```

Inicia una sesión nueva. El plugin carga el protocolo mediante SessionStart; la instalación de usuario afecta a todos los proyectos. El instalador manual conserva CLAUDE.md y otros skills, y copia el protocolo a .claude/rules/ros2-verification.md. No sobrescribe cambios locales. ROS, colcon y los controladores deben estar instalados por separado.

## Skills

- [ros2-development](skills/ros2-development/SKILL.md): Paquetes, nodos, interfaces, launch/config y pruebas; comprueba que cada paquete haya ejecutado pruebas.
- [ros2-troubleshooting](skills/ros2-troubleshooting/SKILL.md): Cuatro diagnósticos ejecutables: QoS, TF, IMU y dirección de odometría, con referencias de marcos y calibración.
- [ros2-microros](skills/ros2-microros/SKILL.md): Guía de MCU, agente, rclc y memoria. No verificada en una MCU.

Puedes mencionar el skill en tu petición: «Usa ros2-development para modificar este paquete Jazzy, compilar sus dependencias y verificar el nodo instalado y las pruebas ejecutadas».

## Validación y límites

Códigos: 0 PASS, 1 FAIL, 2 INCONCLUSIVE o solicitud inválida. Datos ausentes, NaN, QoS desconocido, TF ausente o cero pruebas no cuentan como éxito. La IMU se transforma al marco base; la gravedad no verifica yaw. La odometría verifica dirección, no calibración de distancia. Los diagnósticos no publican órdenes de movimiento.

CI comprueba conservación de instalaciones, lógica, paquetes temporales Python/CMake reales, comunicación y TF sintéticos en Jazzy y el evaluador. Opus 5.5 High completó tres tareas con plugin y con instalación manual; la referencia sin el paquete también completó las tres. Es una observación por método y tarea: consulta el [registro de aceptación](evals/development/RESULTS.md). Las pruebas acreditan herramientas, no una mejora medida del agente. Robots físicos y MCU requieren validación aparte.

Un [estudio posterior de migración de interfaces](evals/workflow_value/RESULTS.md) comparó tres variantes con consumidores Python/C++ usando Opus 5.5 High. Los seis resultados, con y sin el pack, superaron la verificación independiente. La fidelidad de los informes, la ambigüedad de las reglas y los procesos residuales se documentan aparte. No se ha demostrado una mejora de fiabilidad ni una aceleración causal; se mantiene la versión 0.1.2.

Algunas cifras históricas carecen de registros o reevaluaciones reproducibles; no se presentan como rendimiento actual. [CAPABILITIES.md](evals/CAPABILITIES.md).

## Actualización

Para la instalación manual, actualiza el repositorio y repite el instalador. Para el plugin usa el comando siguiente y abre una sesión nueva.

```bash
claude plugin update claude-ros2-skills@claude-ros2-skills
```

[Flujo completo y alcance de la evidencia (English)](README.md) · [Cómo contribuir](CONTRIBUTING.md) · [Apache-2.0](LICENSE).
