<div align="center">

<img src="./assets/cover.jpg" alt="OSCPT Burp Trainer - Laboratorio de Web Hacking" width="100%" style="max-width: 850px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);"/>

# 🎯 OSCPT Burp Trainer
### Laboratorio Práctico de Web Hacking con Burp Suite

**Escenario Corporativo:** *Novera Group / PeopleHub*  
**Plataforma de Retos:** *Secuencial estilo TryHackMe / Hack The Box con 23 Desafíos*

[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Burp Suite](https://img.shields.io/badge/Burp_Suite-Compatible-FF6633?style=flat-square&logo=portswigger&logoColor=white)](https://portswigger.net/burp)
[![Modos](https://img.shields.io/badge/Modos-Aprendizaje_%7C_Guiado_%7C_Examen-2dd4bf?style=flat-square)](http://localhost:8010/help/settings)

</div>

---

## 📋 Resumen del Escenario

Bienvenido a **PeopleHub**, la intranet corporativa del grupo ficticio *Novera Group*. A través de 23 desafíos organizados en 6 módulos progresivos, investigarás la aplicación utilizando **Burp Suite** para descubrir:

- 🌐 Identificación de tecnologías y mapeo de endpoints web.
- 📡 Análisis de métodos HTTP y formulación de peticiones.
- 🧩 Fugas de información en APIs JSON no documentadas.
- 👤 Enumeración de usuarios por respuesta diferencial (404 vs 401).
- 🔑 Extracción de credenciales en comentarios y scripts JavaScript.
- 🚪 Movimiento lateral al portal interno de operaciones (*People Operations*).
- ⚡ Manipulación de peticiones administrativas (POST JSON) para obtener la **Flag de Administrador**.

---

## ⚡ Puesta en Marcha (1 Clic)

No necesitas instalar Python, Flask, pip ni bases de datos. Todo corre encapsulado en Docker.

### 1. Iniciar el laboratorio

- **macOS:** Haz doble clic en `Iniciar-Mac.command`.  
  *(Si macOS muestra advertencia de seguridad, abre Terminal en esta carpeta y ejecuta `chmod +x Iniciar-Mac.command` una sola vez).*
- **Windows:** Haz doble clic en `Iniciar-Windows.bat`.
- **Linux:** Ejecuta `./Iniciar-Mac.command` o `docker compose up --build`.

### 2. Acceder al laboratorio

| Servicio | URL | Descripción |
| :--- | :--- | :--- |
| **Plataforma de Retos** | [http://localhost:8010/help](http://localhost:8010/help) | **Acceso libre sin login**. Panel interactivo con preguntas, pistas y formato de respuesta con máscara `**`. |
| **Aplicación Objetivo** | [http://localhost:8010/](http://localhost:8010/) | Portal corporativo PeopleHub a auditar con Burp Suite. |
| **Comprobación de Salud** | [http://localhost:8010/health](http://localhost:8010/health) | Endpoint de comprobación de estado de la aplicación. |

---

## 🛑 Detener y Limpiar el Laboratorio (Sin residuos)

Para apagar el laboratorio y eliminar automáticamente contenedores, redes, el volumen de datos SQLite y las imágenes construidas:

- **macOS:** Doble clic en `Detener-y-Borrar-Mac.command` o ejecuta `./stop_and_erase.sh`.
- **Windows:** Doble clic en `Detener-y-Borrar-Windows.bat` (o `stop_and_erase.bat`).
- **Terminal:** `docker compose down --rmi all --volumes --remove-orphans`.

---

## 🛠️ Configuración con Burp Suite

1. Abre Burp Suite.
2. Utiliza el **navegador integrado** de Burp (*Proxy > Open browser*) para que todo el tráfico pase por el proxy de forma automática.
3. Navega a `http://127.0.0.1:8010/` para auditar la aplicación y a `http://127.0.0.1:8010/help` para enviar tus respuestas y seguir las tareas.

---

## ⚠️ Uso Autorizado

Este laboratorio está diseñado exclusivamente con fines formativos y de entrenamiento técnico controlado. No expongas este contenedor directamente a Internet.
