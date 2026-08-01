<div align="center">

<img src="assets/hero.png" alt="claude-ros2-skills — Claude Code skills for ROS 2 Jazzy" width="100%"/>

**Claude Code Skills for ROS 2 Jazzy Jalisco robotics development.**

Skills que transforman la manera en que los agentes de IA abordan el desarrollo con ROS 2: identifican los parámetros desconocidos desde el principio, verifican la configuración contra los paquetes instalados y confirman la ejecución mediante evidencia real de funcionamiento.

![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?logo=ubuntu&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | **Español** | [Français](README.fr.md) | [Deutsch](README.de.md)

<sub>🌐 Este documento es la traducción al español del original en [English](README.md).</sub>

| Skills | Protocolo siempre cargado | Enlaces a documentación (verificados por CI) | Scripts de verificación física y en ejecución |
| :---: | :---: | :---: | :---: |
| **2** | **30 líneas** | **6** | **4** |

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
- [Contribuir](#contribuir)
- [Licencia](#licencia)

## Los fallos que cuestan caro

Los errores más costosos en el código ROS 2 generado por IA rara vez son fallos de sintaxis. Son problemas sutiles que a primera vista parecen correctos:

| Fallo | Lo que ves | Por qué un agente cae en ello |
| :--- | :--- | :--- |
| **Desajuste del middleware** | `ros2 topic hz` muestra 30 Hz; tu callback nunca se dispara | Un suscriptor RELIABLE por defecto no puede emparejarse con un publicador BEST_EFFORT. Compila, pasa la revisión y falla por debajo de la aplicación. rclpy sí avisa — `offering incompatible QoS ... Last incompatible policy: RELIABILITY` — pero solo en tiempo de ejecución, en el log de arranque, a quien lo esté leyendo. |
| **Referencia errónea** | `/cmd_vel` indica avance y `/odom` informa avance, pero el robot físico se mueve **hacia atrás** | El frame TF estático está invertido respecto al montaje físico. Los componentes posteriores calculan correctamente *usando la transformación equivocada*, sin producir errores evidentes. |
| **API obsoleta** | El código pasa la revisión pero falla en ejecución al llamar a un método incorrecto | El agente usa métodos de Foxy o Humble que fueron renombrados o eliminados en Jazzy. |
| **Premisa inválida** | El agente escribe 200 líneas basándose en una suposición que habrías corregido en una sola frase | Nada obliga al agente a verificar los detalles que faltan antes de generar código. |

Ni compiladores, ni linters, ni el análisis de logs detectan estos problemas ocultos. Resolver cada uno exige un ciclo de realimentación adicional: revisar la salida, diagnosticar la causa, explicar la corrección y volver a generar el código.

## Cómo están construidos estos skills

Cuatro reglas de diseño rigen cada skill de este repositorio:

**1. Identificar las variables desconocidas desde el principio.** Detalles operativos clave rara vez figuran en la documentación: si el entorno es hardware real o simulación, si se debe extender un workspace existente o crear uno nuevo, qué nodo publica ya una transformación, o la geometría precisa del robot. [`CLAUDE.md`](./CLAUDE.md) instruye al agente a aclarar estas incógnitas antes de generar código.

**2. Ejecutar un bucle estructurado con criterios de salida claros.** El ciclo *verificar → escribir → demostrar*: inspeccionar los valores por defecto en el entorno instalado, aplicar cambios incrementales y confirmar la ejecución. Una tarea solo se completa cuando la respalda evidencia observada — una compilación exitosa, datos reales en `ros2 topic echo`, un script de verificación que pasa — y no por el mero hecho de producir archivos de código.

**3. No decir nada que el modelo ya sepa o que `CLAUDE.md` ya especifique.** Cada tabla síntoma→causa→acción incluida anteriormente en este paquete se evaluó comparándola con un agente de referencia sin skills cargados. La prosa descriptiva nunca mejoró los resultados de las pruebas: el modelo alcanza la solución de forma autónoma o bien requiere un script ejecutable o una restricción de protocolo en `CLAUDE.md`. Véase [Evaluaciones](#evaluaciones).

**4. Señalar un artefacto ejecutable, nunca describirlo.** Las pruebas empíricas demostraron que el texto descriptivo que explica lo que verificaría un script no produjo ninguna mejora en las evaluaciones. Solo los scripts ejecutables con códigos de salida deterministas (`scripts/check_*.py` en `ros2-troubleshooting`) modificaron de manera medible el comportamiento del modelo.

## Qué lo hace diferente

La mayoría de los paquetes de skills de robótica incrustan conocimiento estático de API dentro de los propios archivos. El uso inicial es cómodo, pero este enfoque se rompe cuando los paquetes subyacentes se actualizan, dejando fragmentos obsoletos que fallan en silencio. Este repositorio adopta un enfoque dinámico, guiado por la documentación:

| Característica | Paquetes de skills con mucho contenido | **claude-ros2-skills** |
| :--- | :--- | :--- |
| Ubicación del conocimiento | Incrustado en los archivos de skill (**400–1.800 líneas por skill**) | Enlazado a la documentación oficial (cuerpos de skill de **~60 líneas**); las referencias detalladas se leen **solo cuando hacen falta** |
| Contexto siempre cargado | Archivos `SKILL.md` completos | Protocolo central de **30 líneas** |
| Gestión de cambios de API en Jazzy | Los fragmentos se quedan obsoletos en silencio; requiere actualización manual continua | El riesgo de obsolescencia se reduce a enlaces de entrada y nombres de símbolos — **6 enlaces de documentación** verificados semanalmente por CI |
| Método de verificación | Análisis estático de código o revisión de logs | **Verificación física y en tiempo de ejecución**: comprobación de gravedad del IMU, prueba direccional de odometría, alineación de frames TF, compatibilidad QoS de DDS |
| Alcance de distribución | Afirma soportar varias distribuciones de ROS apuntando en realidad a una sola | **Solo ROS 2 Jazzy**, por diseño — sin rodeos del tipo "también funciona en Humble" |

Este repositorio optimiza un único resultado: minimizar el riesgo de generar código con apariencia plausible que no llega a ejecutarse en ROS 2 Jazzy.

## Evaluaciones

**El criterio.** Un skill se gana su sitio solo si aporta algo que el agente **no puede alcanzar por sí mismo**, teniendo ya su propio conocimiento, búsqueda web y una instalación real de Jazzy delante. Un texto que solo le dice al agente lo que iba a hacer de todos modos es coste sin beneficio.

**Cómo se mide.** Una tarea real en un contenedor limpio, diez ejecuciones con el elemento bajo prueba y diez sin él, evaluadas *ejecutando* lo que salió — una compilación, un topic con datos, un código de salida — nunca leyéndolo. Test exacto de Fisher, con corrección de Benjamini–Hochberg sobre toda la ronda.

**Qué quedó resuelto.** Ocho dominios pasaron por una escalera de tres peldaños — 24 peldaños en total, cada uno añadiendo un mecanismo concreto y evaluado por una verificación que ejecuta el artefacto. El agente de referencia alcanzó **todos los mecanismos que se le pidieron**:

| Dominio | L1 → L2 → L3, mecanismos añadidos por peldaño | Sin ayuda |
| :--- | :--- | ---: |
| Empaquetado y compilación | `ament_python`/`ament_cmake` → `.srv` entre paquetes → nodo componible + `colcon test` | **190/190** |
| Simulación | Mundo SDF + tracción diferencial → `ros_gz_bridge` + `gpu_lidar` → spawn de URDF + `use_sim_time` | **108/110** |
| Ejecutores | Servicio de 1 s desde un timer → desde un callback de suscripción + heartbeat → 5 llamadas concurrentes | **110/110** |
| `ros2_control` | Hardware simulado + broadcaster → segundo controlador reclamando interfaces → **plugin `SystemInterface` en C++ propio** | **90/90** |
| Testing | pytest que `colcon test` realmente ejecuta → `launch_testing` sobre un nodo vivo → rosbag2 grabado y releído | **110/110** |
| MoveIt 2 | URDF+SRDF propios cargados por `move_group` → `GetMotionPlan` real → objeto de colisión en la escena de planificación | **100/100** |
| Núcleo | TF estático desde parámetros → TF dinámico + `ExtrapolationException` → nodo lifecycle en silencio hasta activarse | **110/110** |
| Nav2 | Archivo de parámetros que los servidores aceptan tal cual → pila llevada hasta `active` → costmap marcando obstáculos con escaneo en vivo | véase más abajo |
| Percepción | Ida y vuelta con `cv_bridge` → proyección con `CameraInfo` → profundidad 16UC1 → `PointCloud2` | **106/120** |

**Ni un solo fallo se cerró aportando información.** Se encontraron cuatro carencias, todas de comportamiento:

| Lo que el modelo no hace por sí solo | Referencia | Qué lo cerró | Después |
| :--- | ---: | :--- | ---: |
| Verificar contra la instalación en vez de responder de memoria | **2/10** | un párrafo de `CLAUDE.md` | **10/10** (q=0,002) |
| Producir un veredicto con código de salida en lugar de "parece correcto" | **0/10** | un script ejecutable incluido | **10/10** (q<0,001) |
| Ejecutar el código QoS que escribe antes de entregarlo | **5/10** | el "hecho significa que se ejecutó" de `CLAUDE.md` | **9/10** (potencia insuficiente) |
| Ejecutar la configuración Nav2 que escribe antes de entregarla | **0/10** | una tarea que exige llegar a `active` | **30/30** |

La última fila ilustra este principio de la forma más clara. Al solicitar únicamente un archivo de parámetros de Nav2, las 10 ejecuciones produjeron configuraciones que los propios servidores de Nav2 rechazaron cargar. Sin embargo, al solicitar el archivo de parámetros *y exigir además* que la pila alcanzara el estado `active`, todas las ejecuciones encontraron el mismo error de configuración, lo diagnosticaron a partir de los logs, lo corrigieron y aprobaron. **El mismo modelo, la misma concepción errónea, cero diferencia de información**: solo varió la exigencia de ejecutar y verificar.

**Consecuencia para este paquete.** Se eliminaron por completo seis skills de dominio, además de los dos eliminados anteriormente: el modelo alcanza su contenido de forma independiente y ninguna prosa descriptiva en este repositorio mejoró nunca una prueba de evaluación. Lo que queda es un protocolo de 30 líneas, cuatro scripts ejecutables y el material de referencia que los respalda. Método, resultados por dominio y ejecuciones originales: [`evals/`](./evals/).

## Inicio rápido

**Opción A — Marketplace de plugins (recomendado):**

```
/plugin marketplace add Leehyunbin0131/claude-ros2-skills
/plugin install claude-ros2-skills@claude-ros2-skills
```

Actualiza los plugins instalados en cualquier momento con `/plugin marketplace update`.

**Opción B — Instalación manual:**

```bash
git clone https://github.com/Leehyunbin0131/claude-ros2-skills.git

# Instalación a nivel de proyecto (solo para el proyecto actual)
mkdir -p your-project/.claude/skills
cp -r claude-ros2-skills/skills/* your-project/.claude/skills/
cp claude-ros2-skills/CLAUDE.md your-project/

# Instalación a nivel de usuario (para todos los proyectos)
mkdir -p ~/.claude/skills
cp -r claude-ros2-skills/skills/* ~/.claude/skills/
```

Reinicia Claude Code (o abre una sesión nueva) para aplicar los skills instalados.

## Skills

| Skill | Ruta | Cobertura |
| :--- | :--- | :--- |
| **ros2-troubleshooting** | `skills/ros2-troubleshooting/SKILL.md` | Cuatro verificaciones ejecutables de aprobado/fallo — compatibilidad QoS, árbol TF, montaje del IMU, dirección de odometría — más las convenciones de frames REP 103/105, el comportamiento en ejecución de Jazzy y la calibración de odometría en hardware que las respaldan |
| **ros2-microros** | `skills/ros2-microros/SKILL.md` | Agente micro-ROS, API cliente rclc, transportes personalizados, memoria estática |

**Por qué solo dos.** Todos los demás skills se midieron contra un agente de referencia sin ningún skill cargado y se eliminaron cuando el agente produjo el mismo resultado sin ellos — `ros2-core`, `ros2-dev`, `ros2-control`, `ros2-moveit`, `ros2-perception`, `ros2-testing`, `ros2-package` y `gazebo-sim`, en ese orden de medición. `ros2-microros` es el único dominio sin escalera: aquí no hay hardware para ejecutarla, así que se conserva y **no se declara verificado**. Véase [Evaluaciones](#evaluaciones).

## Scripts de verificación

Estos scripts vienen incluidos en el skill `ros2-troubleshooting` (`skills/ros2-troubleshooting/scripts/`) y se distribuyen con cada instalación. Convierten comprobaciones de hardware físico en pasos ejecutables de aprobado/fallo (requiere un entorno ROS 2 cargado con source; códigos de retorno: 0 = APROBADO, 1 = FALLO, 2 = SIN DATOS):

| Script | Verifica |
| :--- | :--- |
| `check_imu_gravity.py` | Que un robot en reposo mida la gravedad a ~+9,81 m/s² sobre el eje **+Z** (REP 103). Detecta montajes de IMU invertidos o desalineados. |
| `check_odom_direction.py` | Que empujar el robot hacia adelante produzca un desplazamiento de odometría positivo a lo largo de su rumbo. Detecta direcciones de motor invertidas, problemas de polaridad de encoders o configuraciones TF invertidas. |
| `check_tf_tree.py` | Que `map→odom→base_link` se resuelva correctamente; muestra el offset de montaje de cada sensor en grados RPY y destaca posibles errores de orientación de 180°. |
| `check_qos_compat.py` | La compatibilidad QoS entre todos los pares publicador/suscriptor de un topic según las reglas DDS. Previene fallos silenciosos (como un publicador BEST_EFFORT junto a un suscriptor RELIABLE, o desajustes de durability, deadline y liveliness). |

La lógica de decisión central se prueba unitariamente sin depender de ROS (`python3 skills/ros2-troubleshooting/scripts/test_checks.py`) y se ejecuta mediante integración continua (CI) en cada push.

## Cómo funciona

```mermaid
flowchart LR
    A["tu petición"] --> B["CLAUDE.md<br/>protocolo + controles,<br/>sin detalles de API"]
    B --> D["/opt/ros/jazzy/<br/>o documentación oficial de Jazzy"]
    B -.fallo en ejecución.-> C["ros2-troubleshooting<br/>verificaciones ejecutables"]
    C -.solo si hace falta.-> R["references/<br/>frames, runtime,<br/>calibration"]
    D --> E["código, y la prueba de que se ejecutó"]
    C --> E
    R --> E
```

[`CLAUDE.md`](./CLAUDE.md) no contiene detalles específicos de la API. En su lugar, establece el protocolo operativo: verificar la configuración con el entorno local, identificar las incógnitas operativas desde el principio y dar una tarea por terminada solo cuando se observe su ejecución. El conocimiento de dominio se deja en manos del modelo y del entorno instalado, ya que las evaluaciones empíricas demostraron que la prosa descriptiva no aportaba valor. El skill `ros2-troubleshooting` se invoca únicamente cuando un sistema parece correcto en los logs pero falla en tiempo de ejecución, proporcionando códigos de salida accionables en lugar de texto descriptivo. Véase [`CLAUDE.md`](./CLAUDE.md) para más detalles.

## Actualización

```bash
cd claude-ros2-skills
git pull
cp -r skills/* ~/.claude/skills/   # o el .claude/skills/ de tu proyecto
```

## Contribuir

**Resumen:** El contenido nuevo de un skill debe demostrar su valor frente a un agente de referencia sin ayuda mediante pruebas empíricas (una tarea real, 10 ejecuciones por condición, evaluadas mediante la ejecución del resultado). El contenido que el modelo genera sin ayuda no se añadirá, independientemente de su exactitud. Los scripts de verificación deben mantener una lógica de decisión pura para poder probarse de forma unitaria independientemente de ROS. Para consultar el protocolo de evaluación, las listas de comprobación y las plantillas de issues, véase [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Licencia

Apache-2.0 — véase [LICENSE](./LICENSE).
