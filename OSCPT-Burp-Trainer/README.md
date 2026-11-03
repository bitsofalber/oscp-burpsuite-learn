# OSCPT-Burp-Trainer

Laboratorio local de entrenamiento con Burp Suite. Escenario ficticio: Novera Group / PeopleHub.

## Requisitos

- Docker Desktop instalado y en ejecución.
- No necesitas instalar Python, Flask, pip ni crear entornos virtuales.

## Iniciar el laboratorio

1. Descomprime el ZIP.
2. Abre Docker Desktop y espera a que esté iniciado.
3. **macOS:** haz doble clic en `Iniciar-Mac.command`. Si macOS bloquea el archivo, abre Terminal en esta carpeta y ejecuta `chmod +x Iniciar-Mac.command` una sola vez; después vuelve a abrirlo.
4. **Windows:** haz doble clic en `Iniciar-Windows.bat`.

La primera ejecución descarga la imagen base e instala las dependencias dentro de Docker.

## Acceder

- PeopleHub: http://localhost:8010/
- Plataforma de desafíos: http://localhost:8010/help
- Comprobación del servicio: http://localhost:8010/health

Regístrate en PeopleHub y después accede a la plataforma de formación.

## Detener y limpiar el laboratorio

Para detener el laboratorio y borrar automáticamente todos los contenedores, redes, volúmenes de datos e imágenes generadas (sin dejar basura en el sistema):

- **macOS:** haz doble clic en `Detener-y-Borrar-Mac.command` o ejecuta `./stop_and_erase.sh`.
- **Windows:** haz doble clic en `Detener-y-Borrar-Windows.bat` (o `stop_and_erase.bat`).
- **Terminal:** ejecuta en esta carpeta:

```bash
docker compose down --rmi all --volumes --remove-orphans
```

La limpieza eliminará:
- El contenedor del laboratorio.
- La red interna creada por Docker Compose.
- El volumen de datos SQLite (usuarios, evidencias y progreso).
- La imagen local construida para este proyecto.

*(También se ejecuta automáticamente si iniciaste el laboratorio con `Iniciar-Mac.command` o `Iniciar-Windows.bat` y pulsas `Ctrl+C` en esa ventana).*

## Burp Suite

Abre el navegador integrado de Burp Suite y visita:

```text
http://127.0.0.1:8010/
```

El laboratorio está publicado únicamente en la interfaz local del equipo (`127.0.0.1`); no está expuesto a la red local.

## Uso autorizado

Este laboratorio está diseñado para prácticas educativas en un entorno local controlado. No lo expongas directamente a Internet.
