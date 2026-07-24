---
name: ros2-security
description: "SROS2: ros2 security CLI, PKI keystore, enclaves, access-control XML, DDS Security."
---

# ROS 2 Security (SROS2) Instructions (Ubuntu 24.04 LTS & ROS 2 Jazzy)

## 1. Core Principles & Architecture
- **Target OS & ROS Distro**: **Ubuntu 24.04 LTS & ROS 2 Jazzy Jalisco**.
- **Cyber-Physical Security**: SROS2 integrates OMG DDS-Security standards (Fast DDS, Cyclone DDS) to enforce node authentication (X.509 PKI), access control (Governance/Permissions XML), and topic/service encryption (AES-GCM-GMAC 128/256-bit).
- **Zero-Hallucination Policy**: Always verify `ros2 security` CLI subcommands, environment variable names (`ROS_SECURITY_ENABLE`, `ROS_SECURITY_STRATEGY`, `ROS_SECURITY_KEYSTORE`), and policy XML tags against official documentation.

## 2. Official Documentation Catalog

### A. Master Documentation & Tutorials
- **ROS 2 Security Concepts**: `https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Security.html`
- **Introducing ros2-security Tutorial**: `https://docs.ros.org/en/jazzy/Tutorials/Advanced/Security/Introducing-ros2-security.html`
- **Setting Access Control Policies**: `https://docs.ros.org/en/jazzy/Tutorials/Advanced/Security/Access-Controls.html`

## 3. Key Concepts & Workflows

### A. SROS2 CLI Commands
```bash
# 1. Create root keystore
ros2 security create_keystore ~/my_keystore

# 2. Create security enclave for node
ros2 security create_enclave ~/my_keystore /talker_listener/talker

# 3. Launch node inside enclave
export ROS_SECURITY_ENABLE=true
export ROS_SECURITY_STRATEGY=Enforce
export ROS_SECURITY_KEYSTORE=~/my_keystore

ros2 run demo_nodes_cpp talker --ros-args --enclave /talker_listener/talker
```

### B. High-Level Access Control Policy (`policy.xml`)
```xml
<policy version="0.2.0">
  <enclaves>
    <enclave path="/talker_listener/talker">
      <profiles>
        <profile node="talker" ns="/">
          <topics publish="ALLOW">
            <topic>chatter</topic>
          </topics>
        </profile>
      </profiles>
    </enclave>
  </enclaves>
</policy>
```
