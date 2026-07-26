<div align="center">

<img src="assets/hero.png" alt="claude-ros2-skills — Claude Code skills for ROS 2 Jazzy" width="100%"/>

**Claude Code Skills for ROS 2 Jazzy Jalisco robotics development.**

Skills que transforman la manera en que los agentes de IA abordan el desarrollo en ROS 2: identifican parámetros desconocidos desde el principio, verifican la configuración con respecto a los paquetes instalados y confirman la ejecución mediante evidencia concreta.

![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?logo=ubuntu&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | **Español** | [Français](README.fr.md) | [Deutsch](README.de.md)

<sub>🌐 Este documento es una traducción automática. El original está en [English](README.md).</sub>

| Skills | Protocolo siempre cargado | Enlaces a documentación (verificados por CI) | Verificaciones en robot físico | Evaluaciones: Gazebo A/B |
| :---: | :---: | :---: | :---: | :---: |
| **11** | **26 líneas** | **38** | **4 scripts** | **objetivo alcanzado vs. aborto en bringup** |

</div>

---

## Contenido

- [Los fallos que cuestan caro](#los-fallos-que-cuestan-caro)
- [Cómo están construidos estos skills](#cómo-están-construidos-estos-skills)
- [Qué lo hace diferente](#qué-lo-hace-diferente)
- [Evaluaciones](#evaluaciones)
- [Inicio rápido](#inicio-rápido)
- [Skills](#skills)
- [Scripts de verificación](#scripts-de-verificación)
- [Cómo funciona](#cómo-funciona)
- [Actualización](#actualización)
- [Hoja de ruta](#hoja-de-ruta)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

## Los fallos que cuestan caro

Los errores más costosos en el código de ROS 2 generado por IA raras veces son fallos de sintaxis. En su lugar, suelen ser problemas sutiles que parecen correctos a primera vista:

| Fallo | Lo que ves | Por qué el agente encuentra el problema |
| :--- | :--- | :--- |
| **Fallo silencioso** | `ros2 topic hz` muestra 30 Hz; tu callback nunca se ejecuta | Un subscriptor RELIABLE por defecto intenta conectarse a un publicador BEST_EFFORT. El código compila y pasa la revisión de código, pero falla a nivel del middleware DDS. |
| **Ground truth incorrecto** | `/cmd_vel` indica movimiento hacia adelante y `/odom` reporta movimiento hacia adelante, pero el robot físico se mueve hacia **atrás** | El frame de TF estático está invertido con respecto al montaje físico. Los componentes posteriores calculan correctamente *utilizando la transformación incorrecta*, sin generar errores evidentes. |
| **API desactualizada** | El código pasa la revisión pero falla en tiempo de ejecución al llamar a un método incorrecto | El agente utiliza métodos de la API en Foxy o Humble obsoletos que fueron renombrados o eliminados en Jazzy. |
| **Premisa inválida** | El agente escribe 200 líneas de código basándose en una suposición que habrías podido corregir en una sola frase | No existe un mecanismo que pida al agente verificar detalles faltantes antes de generar código. |

Ni los compiladores, ni los linters, ni el análisis de logs detectan estos problemas ocultos. Resolver cada error requiere un ciclo de retroalimentación adicional: revisar la salida, diagnosticar la causa, explicar la solución y regenerar el código.

## Cómo están construidos estos skills

Cuatro reglas de diseño rigen cada skill de este repositorio:

**1. Identificar las variables desconocidas desde el principio.** Los detalles operativos clave con frecuencia no figuran en la documentación: si el entorno es hardware real o simulación, si se debe extender un workspace existente o crear uno nuevo, qué nodo ya publica una transformación o la geometría precisa del robot. [`CLAUDE.md`](./CLAUDE.md) instruye al agente a aclarar estas incógnitas antes de generar código. Los skills específicos de dominio gestionan parámetros concretos; por ejemplo, `ros2-dev` solicita el footprint del robot, la cinemática de tracción y la fuente de localización antes de configurar cualquier parámetro de Nav2.

**2. Ejecutar un bucle estructurado con criterios de salida claros.** Cada skill sigue un ciclo *verificar → escribir → probar*: inspeccionar los valores por defecto del sistema en el entorno instalado, aplicar cambios incrementales y confirmar la ejecución. Una tarea finaliza únicamente cuando está respaldada por evidencia observada —como una compilación exitosa, datos activos en `ros2 topic echo` o un script de verificación superado— en lugar de simplemente generar archivos de código.

**3. Priorizar tablas de fallos estructuradas sobre descripciones extensas.** Las tablas estructuradas que mapean síntomas → causas raíz → acciones correctivas brindan una guía clara y duradera de la que la documentación oficial suele carecer y que se mantiene confiable a través de las distintas versiones:

> `[` es GZ→ROS, `]` es ROS→GZ · `16UC1` son milímetros, `32FC1` son metros · `joint_state_broadcaster` no se lanza automáticamente · `raytrace_max_range` ≤ `obstacle_max_range` significa que los obstáculos nunca se limpian · rclc no asigna automáticamente campos de mensaje sin límite

**4. Optimizar el uso del contexto mediante una arquitectura de tres capas.** Cada skill equilibra la eficiencia del contexto: las descripciones del skill permanecen en el contexto, el cuerpo del skill se carga al ser invocado y los archivos de referencia detallados en `references/` se cargan solo según se requiera. Los catálogos extensos de símbolos y las tablas detalladas de ajuste de parámetros residen en `references/`, garantizando la conservación del contexto y evitando que la depuración de componentes específicos (como AMCL) cargue documentación innecesaria (como nodos de behavior-tree).

## Qué lo hace diferente

La mayoría de los paquetes de skills de robótica incluyen conocimiento estático de las API directamente dentro de sus archivos. Aunque su uso inicial es sencillo, este enfoque falla cuando se actualizan los paquetes subyacentes, dejando fragmentos desactualizados que fallan silenciosamente. Este repositorio adopta un enfoque dinámico orientado a la documentación:

| Característica | Paquetes de skills recargados de contenido | **claude-ros2-skills** |
| :--- | :--- | :--- |
| Ubicación del conocimiento | Integrado en los archivos del skill (**400–1.800 líneas/skill**) | Enlazado a la documentación oficial (cuerpo de skill de **~60 líneas**); las referencias detalladas se leen **solo cuando es necesario** |
| Contexto siempre cargado | Archivos `SKILL.md` completos | Protocolo principal de **26 líneas** |
| Gestión de actualizaciones de la API en Jazzy | Los fragmentos quedan obsoletos silenciosamente; requiere actualizaciones manuales continuas de pruebas | El riesgo de fragmentos obsoletos se minimiza a enlaces de punto de entrada y nombres de símbolos; **38 enlaces a documentación** se verifican semanalmente vía CI |
| Método de verificación | Análisis estático de código o verificación de logs | **Verificación física y en tiempo de ejecución**: comprobaciones de gravedad en IMU, pruebas de odometría direccional, alineación de frames TF, compatibilidad de QoS en DDS |
| Alcance de distribución | Afirma soportar múltiples distribuciones de ROS cuando solo apunta a una | **Exclusivo para ROS 2 Jazzy**, diseñado y validado explícitamente |

Este repositorio se optimiza para un único resultado: minimizar el riesgo de generar código con apariencia válida pero que falla al ejecutarse en ROS 2 Jazzy.

## Evaluaciones

Cada resultado presentado a continuación proviene de una prueba comparativa A/B: el **mismo prompt** ejecutado en sesiones independientes y limpias de Claude Code en modo headless (una vez sin estos skills y otra vez con ellos) utilizando el **mismo modelo** en ambas celdas. La evaluación pasó por cuatro etapas: comparación símbolo por símbolo con las fuentes oficiales fijadas de Jazzy, contra una instalación activa de `/opt/ros/jazzy`, cargando ambas salidas en una **simulación en vivo en Gazebo** y, finalmente, **ejecutando los nodos generados contra publicadores en funcionamiento**. Ahora cada tarea de la suite cuenta con una medición sobre una instalación real. Las transcripciones completas, el código generado y los registros de ejecución están guardados en [`evals/runs/`](./evals/runs/), y el arnés que produce los pares está en [`evals/harness/`](./evals/harness/), para que cualquiera pueda reevaluarlos o reejecutarlos de manera transparente.

El tamaño de muestra es **n=1 por celda**, y tanto la ejecución como la evaluación las realizó el mismo proyecto que publica estos resultados. La evaluación es mecánica siempre que es posible (¿existe el símbolo en la instalación? ¿el comando termina con éxito?), de modo que puede verificarse de forma independiente.

### Configuración de Nav2 MPPI — Haiku, instalación en vivo de Jazzy

*Prompt: configura Nav2 con el controlador MPPI para un robot de tracción diferencial en Jazzy y produce el YAML del controller server.*

| | Sin skills | Con skills |
| :--- | :--- | :--- |
| Proceso | Respondió de inmediato usando memoria; **cero** verificación a pesar de tener herramientas disponibles | Solicitó **primero** footprint, configuración existente, localización y límites de velocidad, y luego leyó los valores por defecto incluidos en `/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml` |
| Cadena de plugin | `mppi_generic::ControllerServer` — no existe | `nav2_mppi_controller::MPPIController` — correcto |
| Lista de `critics:` | Ausente por completo | Los 8, con nombres correctos |
| Claves de parámetros inventadas | **~16** | **0** — cada clave fue comparada mecánicamente contra los valores por defecto instalados |
| **Cargado en una simulación en vivo de Gazebo** | **`[FATAL] Failed to create controller … does not exist` — Nav2 se aborta en el bringup; el robot nunca se mueve** | **MPPI + los 8 critics se cargan; el robot se desplaza de (−2.0, −0.5) a (0.5, 0.5); `NavigateToPose` devuelve `SUCCEEDED`** |

### Un paquete que debe ejecutarse realmente — Haiku, dentro del contenedor

*Prompt: crea un paquete Python `demo_pkg` que publique `std_msgs/msg/String` en `/greeting` a 1 Hz, junto con un archivo launch; compílalo y muestra `ros2 topic echo /greeting`.*

| | Sin skills | Con skills |
| :--- | :--- | :--- |
| `ros2 run` / `ros2 launch` / `topic echo` | **Los tres fallan** — el paquete nunca se registra en el ament index | **Los tres se ejecutan con éxito**, confirmado mediante reejecuciones independientes de cada comando |
| Costo para obtener ese resultado | $0.17 · 36 turnos · 178 s | **$0.08 · 18 turnos · 61 s** — correcto al primer intento y **2.2 veces más económico** |

### Suscripción a sensores — Haiku, ambos nodos ejecutados contra un publicador activo

*Prompt: escribe un nodo Python para Jazzy que se suscriba a `/scan` y registre la distancia mínima una vez por segundo.* Después, cada nodo generado se ejecutó durante 6 s contra un publicador de `/scan` en modo BEST_EFFORT.

| | Sin skills | Con skills |
| :--- | :--- | :--- |
| QoS de la suscripción | `create_subscription(..., 10)` → RELIABLE | `qos_profile_sensor_data` |
| **Mensajes recibidos en ejecución** | **Cero.** rclpy informó por sí mismo: `offering incompatible QoS. No messages will be received from it. Last incompatible policy: RELIABILITY` | **Recibe a 5 Hz** |
| Mínimo reportado (respuesta correcta: 0,45 m) | nunca recibió ninguno | `0,020 m` — **también incorrecto**: ningún nodo filtra según `range_min`/`range_max` |

La diferencia de conectividad es la que decide si el pipeline de sensores existe siquiera, y es reproducible. El error numérico, en cambio, es un fallo real de ambas condiciones, por lo que queda registrado como tarea pendiente de `ros2-core` y no como un logro.

### Preguntar antes de escribir — Haiku, LiDAR montado al revés

*Prompt: mi LiDAR está montado boca abajo en la parte trasera del chasis, mirando hacia atrás; escribe la TF estática y dime cómo confirmar la corrección.*

| | Sin skills | Con skills |
| :--- | :--- | :--- |
| Establece primero el montaje físico | Respondió en un solo turno | **Se detuvo y preguntó por la distancia trasera y los desplazamientos** antes de emitir la transformada |
| Corrección de la transformada | roll≈180° + yaw≈180°, relación padre/hijo según REP 105 — correcto | correcto; al publicar ambas salidas, `check_tf_tree.py` las señaló exactamente como fue diseñado |
| Consejo de confirmación | RViz con una visualización **PointCloud2** — tipo de mensaje incorrecto para un LiDAR | `tf2_echo` más una visualización **LaserScan** |

### Lo que estos skills no resuelven

Se documenta porque omitirlo restaría credibilidad al resto:

- **La alucinación se desplaza, no desaparece.** En las tres tareas más recientes, la salida con skills siguió inventando `ros2_troubleshooting_helpers` (paquete inexistente, y precisamente al describir *el script de este propio repositorio*) y un valor de durability por defecto equivocado. Enrutar a la documentación eleva el suelo; no vuelve correcto al modelo.
- **En problemas que el modelo ya domina, los skills cuestan más y aportan poco.** En el diagnóstico clásico de incompatibilidad de QoS ambas condiciones acertaron en un turno, y la versión con skills añadió un error factual por ~1,4× el coste.
- **Los skills cambian lo que el agente *pregunta* con más fiabilidad que lo que *comprueba*.** Con una reproducción en vivo en marcha y `Bash` permitido, ambas celdas recomendaron `ros2 topic info -v` y ninguna lo ejecutó.
- **Ninguna de las dos condiciones acertó los números en la Tarea 1.** Los dos nodos generados omitieron el filtrado por `range_min`/`range_max` y reportarían como obstáculo más cercano una lectura por debajo del mínimo.

### El patrón en cada par

Ninguna celda de referencia, en ninguna ejecución, verificó contra los paquetes instalados o la documentación **antes** de escribir código, incluso con WebFetch, Read y Bash explícitamente permitidos; además, una de ellas reportó una compilación completamente funcional para un paquete que `ros2 run` ni siquiera puede encontrar. Las celdas con skills formularon las preguntas previas a la escritura en todas las ejecuciones donde la tarea tenía incógnitas, y sus afirmaciones coincidieron con la reejecución independiente. Los scripts de verificación ya se han ejercitado con datos reales en ambos sentidos: `check_qos_compat.py` produjo su primer `[FAIL]` real frente a una incompatibilidad BEST_EFFORT/RELIABLE genuina, y `check_tf_tree.py` señaló un sensor invertido sin marcar el que estaba correctamente montado.

Consulta las tablas completas de evaluación, los entornos de prueba y los análisis de cada ejecución en [`evals/RESULTS.md`](./evals/RESULTS.md). Para obtener más detalles sobre el protocolo de evaluación, las listas de verificación de tareas y la configuración del contenedor, consulta [`evals/README.md`](./evals/README.md). Los Pull Requests con transcripciones evaluadas adicionales son bienvenidos.

## Inicio rápido

**Opción A — Plugin Marketplace (Recomendado):**

```
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

Actualiza los plugins instalados en cualquier momento con `/plugin marketplace update`.

**Opción B — Instalación manual:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git

# Instalación a nivel de proyecto (se aplica solo al proyecto actual)
mkdir -p your-project/.claude/skills
cp -r claude-ros2-skills/skills/* your-project/.claude/skills/
cp claude-ros2-skills/CLAUDE.md your-project/

# Instalación a nivel de usuario (se aplica a todos los proyectos)
mkdir -p ~/.claude/skills
cp -r claude-ros2-skills/skills/* ~/.claude/skills/
```

Reinicia Claude Code (o inicia una nueva sesión) para aplicar los skills instalados.

## Skills

| Skill | Ruta | Cobertura |
| :--- | :--- | :--- |
| **ros2-core** | `skills/ros2-core/SKILL.md` | rclcpp, rclpy, TF2, odometría EKF, perfiles de QoS, parámetros |
| **ros2-package** | `skills/ros2-package/SKILL.md` | `ros2 pkg create`, configuración de CMakeLists/setup.py, colcon build y source, interfaces personalizadas |
| **ros2-dev** | `skills/ros2-dev/SKILL.md` | Nav2 (AMCL, costmaps, MPPI/Smac), SLAM Toolbox, RTAB-Map, Isaac ROS |
| **gazebo-sim** | `skills/gazebo-sim/SKILL.md` | Gazebo Harmonic, ros_gz_bridge, ros_gz_sim, modelado SDFormat |
| **ros2-control** | `skills/ros2-control/SKILL.md` | abstracción de hardware en ros2_control, controller manager, etiquetas URDF |
| **ros2-moveit** | `skills/ros2-moveit/SKILL.md` | MoveIt 2, API C++/Python de MoveGroup, solucionadores IK, OMPL, MoveIt Servo |
| **ros2-perception** | `skills/ros2-perception/SKILL.md` | image_transport, cv_bridge, vision_msgs, depth_image_proc, PCL |
| **ros2-testing** | `skills/ros2-testing/SKILL.md` | launch_testing, gtest/pytest, API C++/Python de rosbag2, ros2trace |
| **ros2-microros** | `skills/ros2-microros/SKILL.md` | micro-ROS Agent, API cliente rclc, transportes personalizados, memoria estática |
| **ros2-security** | `skills/ros2-security/SKILL.md` | SROS2, generación de keystore PKI, control de acceso, DDS Security |
| **ros2-troubleshooting** | `skills/ros2-troubleshooting/SKILL.md` | árbol TF de referencia REP 103/105, alineación de LiDAR/IMU, verificación física |

## Scripts de verificación

Estos scripts de verificación están incluidos dentro del skill `ros2-troubleshooting` (`skills/ros2-troubleshooting/scripts/`) y forman parte de cada instalación. Convierten las comprobaciones de hardware físico en pasos de verificación ejecutables con resultado de éxito/fallo (requiere un entorno ROS 2 cargado previamente; códigos de retorno: 0 = PASS, 1 = FAIL, 2 = NO DATA):

| Script | Verifica |
| :--- | :--- |
| `check_imu_gravity.py` | Valida que un robot en reposo mida la gravedad en ~+9.81 m/s² a lo largo del eje **+Z** (REP 103). Detecta montajes de IMU invertidos o desalineados. |
| `check_odom_direction.py` | Valida que empujar el robot hacia adelante produzca un desplazamiento positivo de odometría a lo largo de su orientación. Detecta direcciones de motor invertidas, problemas de polaridad en encoders o configuraciones de TF invertidas. |
| `check_tf_tree.py` | Verifica que `map→odom→base_link` se resuelva correctamente; muestra el desfase de montaje de cada sensor en grados RPY y resalta posibles errores de orientación de 180°. |
| `check_qos_compat.py` | Verifica la compatibilidad de QoS entre todos los pares publicador/subscriptor en un tema (topic) utilizando las reglas de DDS. Previene fallos silenciosos (como un publicador BEST_EFFORT emparejado con un subscriptor RELIABLE, o desajustes en durabilidad, deadline y liveliness). |

La lógica principal de decisión cuenta con pruebas unitarias independientes de ROS (`python3 skills/ros2-troubleshooting/scripts/test_checks.py`) y se ejecuta mediante integración continua (CI) en cada push.

## Cómo funciona

```mermaid
flowchart LR
    A["your request"] --> B["CLAUDE.md<br/>protocol + gates,<br/>no API details"]
    B --> C["skills/&lt;name&gt;/SKILL.md<br/>gates, loop,<br/>failure tables"]
    C --> D["/opt/ros/jazzy/<br/>or official Jazzy docs"]
    C -.only if needed.-> R["references/<br/>symbol catalogs,<br/>tuning tables"]
    D --> E["code, then proof it ran"]
    R --> E
```

`CLAUDE.md` no contiene detalles específicos de la API. En su lugar, establece el protocolo operativo y requiere responder preguntas aclaratorias antes de escribir código. Cada archivo `SKILL.md` gestiona decisiones específicas de su dominio: identificar variables desconocidas, ejecutar el ciclo de verificar-escribir-probar y consultar tablas de fallos. Los materiales de referencia detallados se almacenan por separado en el directorio `references/`. Consulta [`CLAUDE.md`](./CLAUDE.md) para más detalles.

## Actualización

```bash
cd claude-ros2-skills
git pull
cp -r skills/* ~/.claude/skills/   # o el .claude/skills/ de tu proyecto
```

## Hoja de ruta

1. ~~Automatizar pares de evaluación dentro de contenedores `ros:jazzy`~~ — **completado (2026-07-25):** Reejecución de la Tarea 4 frente a una instalación en vivo de `/opt/ros/jazzy`; resultados en [`evals/RESULTS.md`](./evals/RESULTS.md).
2. ~~Publicar resultados de evaluación de la Tarea 5~~ — **completado (2026-07-25):** Resultado binario de compilación/ejecución/echo medido dentro del contenedor; resultados en [`evals/RESULTS.md`](./evals/RESULTS.md).
3. ~~Extender las evaluaciones sobre instalación en vivo a las Tareas 1–3~~ — **completado (2026-07-26):** ejecutado sobre una instalación nativa de `ros-jazzy-ros-base`, con ambos nodos generados ejecutados contra publicadores activos; arnés en [`evals/harness/`](./evals/harness/), resultados en [`evals/RESULTS.md`](./evals/RESULTS.md).
4. ~~Corregir los defectos que esas ejecuciones revelaron~~ — **completado (2026-07-26):** `ros2-troubleshooting` ya indica la invocación literal del script (el modelo estaba inventando un paquete) y que `check_tf_tree.py` siempre marca un montaje de ~180° para confirmación física; `ros2-core` incorporó la regla de límites `range_min`/`range_max` y un patrón de cierre limpio. **Las tablas de evaluación miden los skills tal como estaban antes de estas correcciones.**
5. **Reejecutar las Tareas 1–3 con los skills corregidos**, para averiguar si las correcciones cambian realmente la salida — el motivo por el que las tablas anteriores siguen describiendo la versión previa.
6. **Hacer que la Tarea 3 discrimine** — actualmente ambas condiciones aciertan de memoria, así que debe exigir que el diagnóstico de QoS se *demuestre* contra endpoints reales, no que se recomiende.
7. **Rastrear "correcciones hasta completar" como una métrica clave** — midiendo el número de iteraciones de retroalimentación necesarias antes de que el código se ejecute con éxito.
8. **Implementar búsquedas deterministas en `references/`** para asegurar que los documentos de referencia detallados se carguen cuando sean relevantes.
9. **Ampliar la separación cuerpo/`references`** a `ros2-core` y `gazebo-sim`, optimizando la eficiencia del contexto en skills de alta frecuencia con documentación de referencia sustancial.

## Contribuir

Resumen: Los archivos de los skills deben enfocarse en la lógica de decisión (puertas de validación, pasos de bucle y tablas de fallos), mientras que la documentación detallada permanece en `references/`. Cada símbolo de la API debe ser verificado contra la documentación oficial de Jazzy o instalaciones en `/opt/ros/jazzy/`. Los scripts de verificación deben mantener una lógica pura que pueda ser sometida a pruebas unitarias sin dependencias de ROS. Para consultar las guías completas, listas de verificación de skills y scripts, y plantillas de issues, consulta [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Licencia

Apache-2.0 — consulta [LICENSE](./LICENSE).
