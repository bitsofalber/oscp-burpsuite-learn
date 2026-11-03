#!/usr/bin/env python3
"""
OSCPT Enum Trainer — Lab 2
Novera Group DevPortal — Reconocimiento, Enumeración e Intruder

Puerto: 8011
Flag: OSCPBT{n0v3r4_d3vp0rtal_3num3r4t3d}
"""
import os
import uuid
import json
import base64
from urllib.parse import quote
from flask import (
    Flask, request, session, redirect, make_response,
    jsonify, render_template_string
)

app = Flask(__name__)
app.secret_key = os.environ.get("OSCPT_SECRET_KEY", "n0v3r4-enum-lab2-2026-s3cr3t-k3y")

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "lab": "OSCPT-Enum-Trainer"}), 200


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES Y DATOS DEL DEVPORTAL VULNERABLE
# ══════════════════════════════════════════════════════════════════════════════

FINAL_FLAG        = "OSCPBT{n0v3r4_d3vp0rtal_3num3r4t3d}"
ADMIN_TOKEN_VALUE = "ADM-2026-N0V3R4-CART3R"
VALID_RESET_TOKEN = base64.b64encode(b"42").decode()  # NDI=
HEX_SECRET        = bytes("C4rt3r-S3cur3!", "utf-8").hex()  # 4334727433722d53336375723321

DEVPORTAL_USERS = {
    "admin": {
        "password": "N0vera-OLD!", "role": "sysadmin",
        "email": "admin@novera.corp", "active": False, "pin": None,
    },
    "j.morgan": {
        "password": "Morgan2024#", "role": "developer",
        "email": "j.morgan@novera.corp", "active": True, "pin": "4829",
    },
    "k.ross": {
        "password": "Ross@Novera99", "role": "developer",
        "email": "k.ross@novera.corp", "active": True, "pin": "1173",
    },
    "devops": {
        "password": "D3vOps-Novera!", "role": "devops",
        "email": "devops@novera.corp", "active": True, "pin": "7741",
    },
    "a.carter": {
        "password": "C4rt3r-S3cur3!", "role": "admin",
        "email": "a.carter@novera.corp", "active": True, "pin": None,
    },
}

API_TOKENS = {
    "dev-token-jm-2026":   "j.morgan",
    "dev-token-kr-2026":   "k.ross",
    "admin-token-ac-2026": "a.carter",
}

# JWT falso para challenge I4
_jwt_h = base64.b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip("=")
_jwt_p = base64.b64encode(b'{"sub":"a.carter","role":"admin","exp":"2027-01-01"}').decode().rstrip("=")
FAKE_ADMIN_JWT = f"{_jwt_h}.{_jwt_p}."


def make_devportal_token(username: str) -> str:
    """Cookie de sesión del DevPortal en Base64 (challenge D1)."""
    user = DEVPORTAL_USERS.get(username, {})
    payload = f"user:{username}:role:{user.get('role','unknown')}:exp:2027-01-01"
    return base64.b64encode(payload.encode()).decode()


def get_bearer_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def require_api_token():
    token = get_bearer_token()
    if not token or token not in API_TOKENS:
        return jsonify({"error": "unauthorized", "message": "Se requiere Bearer token válido"}), 401
    return None


def add_devportal_headers(resp):
    resp.headers["X-Powered-By"] = "NoveraPortal/2.3.1"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Server"] = "NoveraWS/1.4"
    return resp


# ══════════════════════════════════════════════════════════════════════════════
# DEFINICIÓN DE RETOS
# ══════════════════════════════════════════════════════════════════════════════

MODULES = {
    1: {"name": "🔍 Reconocimiento Pasivo",     "color": "#6C8EBF"},
    2: {"name": "📁 Enumeración de Endpoints",  "color": "#82B366"},
    3: {"name": "👤 Enumeración de Usuarios",   "color": "#D6B656"},
    4: {"name": "💥 Intruder & Brute Force",    "color": "#AE4132"},
    5: {"name": "🔓 Decoder & Análisis",        "color": "#9673A6"},
    6: {"name": "🏁 Escalada Final",            "color": "#E07A5F"},
}

CHALLENGES = [
    # ── MÓDULO 1: Reconocimiento ──────────────────────────────────────────
    {
        "id": "R1", "module": 1, "points": 75,
        "title": "Header de Tecnología",
        "objective": "Identifica la tecnología del DevPortal analizando las cabeceras HTTP de respuesta.",
        "question": "¿Cuál es el valor exacto del header <code>X-Powered-By</code> que devuelve el servidor?",
        "answers": ["NoveraPortal/2.3.1"],
        "hint1": "Haz un GET a <code>http://localhost:8011/devportal/</code> en Burp Repeater e inspecciona los headers de respuesta.",
        "hint2": "En Burp Suite, ve a la pestaña <b>Response → Headers</b>. Busca el header <code>X-Powered-By</code>.",
        "hint3": "El valor del header revela el nombre y versión del framework propietario de Novera Group.",
        "burp_tip": "Usa el panel <b>Inspector</b> a la derecha del Proxy/Repeater → <b>Response headers</b> para ver las cabeceras organizadas.",
    },
    {
        "id": "R2", "module": 1, "points": 75,
        "title": "Archivo robots.txt",
        "objective": "Descubre las rutas sensibles que el servidor intenta ocultar a los motores de búsqueda.",
        "question": "¿Cuál es la primera ruta <code>Disallow</code> del archivo <code>/robots.txt</code>?",
        "answers": ["/devportal/internal"],
        "hint1": "Accede a <code>http://localhost:8011/robots.txt</code> desde el navegador o Burp Repeater.",
        "hint2": "El archivo <code>robots.txt</code> lista directivas <code>Disallow</code> con rutas que los bots no deben indexar.",
        "hint3": "La primera directiva Disallow suele ser la ruta más sensible del servidor.",
        "burp_tip": "Desde <b>Target → Site map</b>, el archivo robots.txt aparecerá cuando lo hayas visitado.",
    },
    {
        "id": "R3", "module": 1, "points": 100,
        "title": "Comentarios en Código Fuente",
        "objective": "Los desarrolladores dejan información sensible en comentarios HTML. Analiza el código fuente.",
        "question": "¿Qué endpoint oculto encuentras en los comentarios HTML de <code>/devportal/</code>?",
        "answers": ["/devportal/api/v1/docs"],
        "hint1": "Carga <code>http://localhost:8011/devportal/</code> en el navegador y abre el código fuente con Ctrl+U.",
        "hint2": "En Burp Repeater, envía GET a <code>/devportal/</code> y usa Ctrl+F para buscar el texto <code>&lt;!--</code>.",
        "hint3": "El comentario menciona un endpoint de documentación que 'hay que mover antes del release'.",
        "burp_tip": "En la pestaña Response del Repeater, usa <b>Ctrl+F</b> y busca '<!--' para localizar comentarios HTML.",
    },
    # ── MÓDULO 2: Enumeración ─────────────────────────────────────────────
    {
        "id": "E1", "module": 2, "points": 100,
        "title": "Documentación de la API",
        "objective": "Explora el endpoint de documentación descubierto y mapea la superficie de ataque de la API.",
        "question": "¿Cuántos endpoints lista <code>/devportal/api/v1/docs</code>?",
        "answers": ["8"],
        "hint1": "Haz un GET a <code>http://localhost:8011/devportal/api/v1/docs</code> en Burp Repeater.",
        "hint2": "La respuesta es JSON. El campo <code>endpoints</code> contiene el listado completo de rutas.",
        "hint3": "Hay exactamente 8 rutas documentadas en la API v1.",
        "burp_tip": "Cambia a la vista <b>Pretty</b> en el panel Response del Repeater para ver el JSON formateado.",
    },
    {
        "id": "E2", "module": 2, "points": 150,
        "title": "Fuzzing de Parámetros Ocultos",
        "objective": "El endpoint de búsqueda tiene un parámetro no documentado. Usa Burp Intruder para descubrirlo.",
        "question": "¿Qué parámetro oculto activa el modo debug en <code>/devportal/search</code>?",
        "answers": ["debug"],
        "hint1": "Envía GET <code>/devportal/search?test=1</code> en Repeater. Mándalo a Intruder y marca <code>§test§</code> como posición.",
        "hint2": "Usa una wordlist de parámetros comunes: <code>debug, verbose, trace, admin, mode, dev, internal, test, inspect</code>.",
        "hint3": "El parámetro correcto hace que la respuesta incluya un campo <code>debug_info</code> adicional.",
        "burp_tip": "En Intruder → Settings → <b>Grep - Match</b>, añade <code>debug_info</code> para resaltar automáticamente la respuesta correcta.",
    },
    {
        "id": "E3", "module": 2, "points": 150,
        "title": "Descubrimiento de Archivos de Backup",
        "objective": "Los servidores mal configurados exponen archivos de backup. Usa Intruder para encontrarlos.",
        "question": "¿Qué archivo <code>.bak</code> existe en la ruta <code>/devportal/</code>?",
        "answers": ["config.bak"],
        "hint1": "Fuzzea la ruta <code>/devportal/§nombre§.bak</code> con Intruder y una lista: <code>config, database, settings, backup, app, web, site</code>.",
        "hint2": "Un código de respuesta 200 indica que el archivo existe. Un 404 indica que no.",
        "hint3": "El archivo que existe contiene la configuración del servidor incluyendo credenciales.",
        "burp_tip": "En Intruder → Settings, usa <b>Grep - Match</b> con el código 200 para identificar el archivo rápidamente.",
    },
    {
        "id": "E4", "module": 2, "points": 125,
        "title": "Extracción de Credenciales del Backup",
        "objective": "El archivo de backup tiene datos de configuración sensibles. Extrae el token de API.",
        "question": "¿Qué valor tiene <code>API_TOKEN</code> en el archivo <code>/devportal/config.bak</code>?",
        "answers": ["dev-token-jm-2026"],
        "hint1": "Haz un GET directo a <code>http://localhost:8011/devportal/config.bak</code> en Burp Repeater.",
        "hint2": "El archivo tiene formato de variables de entorno. Busca la línea <code>API_TOKEN=...</code>.",
        "hint3": "El token tiene formato <code>dev-token-XX-YYYY</code> e identifica a un desarrollador específico.",
        "burp_tip": "Usa <b>Ctrl+F</b> en la respuesta para buscar 'TOKEN' y localizar la línea rápidamente.",
    },
    # ── MÓDULO 3: Usuarios ────────────────────────────────────────────────
    {
        "id": "U1", "module": 3, "points": 125,
        "title": "User Enumeration por Errores",
        "objective": "Los mensajes de error del login revelan qué usuarios existen. Usa Intruder para identificarlos.",
        "question": "¿Cuál de los siguientes usuarios existe en el sistema? (usa Burp Intruder para comprobarlo)",
        "answers": ["j.morgan"],
        "hint1": "Prueba un login con un usuario inexistente, luego con <code>j.morgan</code>. El mensaje de error es diferente.",
        "hint2": "Usa Intruder Sniper con la lista: <code>admin, user, j.morgan, m.smith, k.ross, devops, test, root</code>.",
        "hint3": "Usuario válido → 'Contraseña incorrecta'. Usuario inválido → 'Usuario no encontrado'.",
        "burp_tip": "En Intruder → Settings → <b>Grep - Match</b>, configura las dos cadenas para clasificar respuestas automáticamente.",
    },
    {
        "id": "U2", "module": 3, "points": 150,
        "title": "Listado de Usuarios vía API",
        "objective": "Con el token de API obtenido del backup, accede al endpoint de usuarios y enuméralos.",
        "question": "¿Cuántos usuarios tiene el sistema según <code>/devportal/api/v1/users</code>?",
        "answers": ["5"],
        "hint1": "GET a <code>/devportal/api/v1/users</code> añadiendo el header <code>Authorization: Bearer dev-token-jm-2026</code>.",
        "hint2": "La respuesta JSON tiene un campo <code>users</code> con el listado completo.",
        "hint3": "Hay exactamente 5 usuarios registrados en el sistema.",
        "burp_tip": "Añade la cabecera desde el <b>Inspector → Request headers → botón +</b> para no editar el texto crudo.",
    },
    {
        "id": "U3", "module": 3, "points": 125,
        "title": "Identificación del Administrador",
        "objective": "En la lista de usuarios, identifica al administrador principal del sistema.",
        "question": "¿Cuál es el email del usuario con rol <code>admin</code>?",
        "answers": ["a.carter@novera.corp"],
        "hint1": "Revisa el JSON de usuarios del reto anterior y busca el que tenga <code>\"role\": \"admin\"</code>.",
        "hint2": "El email del admin sigue el patrón <code>inicial.apellido@novera.corp</code>.",
        "hint3": "El administrador principal del DevPortal es Amelia Carter.",
        "burp_tip": "Usa la vista <b>Pretty</b> del Repeater para ver el JSON con indentación y localizar el campo role.",
    },
    # ── MÓDULO 4: Intruder & Brute Force ──────────────────────────────────
    {
        "id": "I1", "module": 4, "points": 175,
        "title": "Brute Force de PIN",
        "objective": "El usuario j.morgan tiene un PIN de 4 dígitos para la API de desbloqueo. Encuéntralo.",
        "question": "¿Cuál es el PIN de 4 dígitos del usuario <code>j.morgan</code>?",
        "answers": ["4829"],
        "hint1": "POST a <code>/devportal/api/v1/unlock</code> con JSON: <code>{\"username\":\"j.morgan\",\"pin\":\"0000\"}</code>. Manda a Intruder.",
        "hint2": "Intruder → Sniper, marca <code>§0000§</code>. Payloads → Numbers: min 0, max 9999, Min integer digits: 4.",
        "hint3": "La respuesta correcta devuelve HTTP 200 con <code>{\"status\":\"unlocked\"}</code>. Las incorrectas devuelven 401.",
        "burp_tip": "En Intruder → Payloads, elige <b>Numbers</b>. Configura <b>Min integer digits: 4</b> para forzar el formato 0000–9999.",
    },
    {
        "id": "I2", "module": 4, "points": 175,
        "title": "Brute Force de Token Predecible",
        "objective": "El sistema de reset usa tokens Base64 de números del 1 al 100. Usa Intruder para encontrar el válido.",
        "question": "¿Cuál es el token Base64 válido para el endpoint <code>/devportal/reset</code>?",
        "answers": ["NDI=", "NDI"],
        "hint1": "POST a <code>/devportal/reset</code> con JSON: <code>{\"token\":\"AAAA\"}</code>. Marca AAAA como posición de Intruder.",
        "hint2": "En Python: <code>[base64.b64encode(str(n).encode()).decode() for n in range(1,101)]</code> genera los 100 tokens posibles.",
        "hint3": "El token válido corresponde al número 42 en Base64. El servidor responde 200 con <code>{\"status\":\"token_valid\"}</code>.",
        "burp_tip": "Pega la lista de tokens generada con Python directamente en Intruder → Payloads → <b>Simple list → Paste</b>.",
    },
    {
        "id": "I3", "module": 4, "points": 150,
        "title": "Enumeración de IDs de API",
        "objective": "Enumera el endpoint /devportal/api/v1/keys/{id} para encontrar el ID que contiene datos secretos.",
        "question": "¿Qué ID (del 1 al 50) devuelve datos válidos en <code>/devportal/api/v1/keys/{id}</code>?",
        "answers": ["17"],
        "hint1": "GET <code>/devportal/api/v1/keys/1</code> con Bearer token. Manda a Intruder y marca el número <code>§1§</code>.",
        "hint2": "Payloads → Numbers del 1 al 50. Filtra por código de respuesta 200.",
        "hint3": "Solo el ID 17 devuelve datos válidos con una clave secreta en formato hexadecimal.",
        "burp_tip": "En Intruder → Settings, activa <b>Grep - Match</b> con <code>hex</code> para resaltar la respuesta válida.",
    },
    {
        "id": "I4", "module": 4, "points": 175,
        "title": "Decodificación de JWT",
        "objective": "La API de perfil devuelve un token JWT con información sensible. Decodifica su payload para extraerla.",
        "question": "¿Cuál es el valor del claim <code>sub</code> en el JWT de <code>/devportal/api/v1/profile</code>?",
        "answers": ["a.carter"],
        "hint1": "GET <code>/devportal/api/v1/profile</code> con header <code>Authorization: Bearer dev-token-jm-2026</code>. La respuesta incluye <code>admin_jwt</code>.",
        "hint2": "Un JWT tiene 3 partes separadas por puntos: <code>HEADER.PAYLOAD.SIGNATURE</code>. Toma solo la parte central (PAYLOAD).",
        "hint3": "Lleva el payload a Burp Decoder → Base64 decode. El campo <code>sub</code> contiene el nombre del usuario admin.",
        "burp_tip": "En Burp <b>Decoder</b>, pega el payload del JWT (parte central) y elige <b>Decode as → Base64</b>.",
    },
    # ── MÓDULO 5: Decoder & Análisis ──────────────────────────────────────
    {
        "id": "D1", "module": 5, "points": 125,
        "title": "Decodificación de Cookie de Sesión",
        "objective": "Tras el login, el servidor establece una cookie con datos de sesión en Base64. Analízala.",
        "question": "¿Cuál es el rol (<code>role</code>) del usuario <code>j.morgan</code> en la cookie <code>devportal_token</code>?",
        "answers": ["developer"],
        "hint1": "Haz un POST de login exitoso como <code>j.morgan</code> con contraseña <code>Morgan2024#</code>. Busca la cookie <code>devportal_token</code> en la respuesta.",
        "hint2": "Copia el valor de la cookie y llévalo al Burp <b>Decoder</b>. Decodifícalo como Base64.",
        "hint3": "El valor decodificado tiene el formato <code>user:USERNAME:role:ROLE:exp:FECHA</code>.",
        "burp_tip": "En el <b>Inspector → Response cookies</b> (con la respuesta activa), verás la cookie con su valor. Haz clic para copiarlo.",
    },
    {
        "id": "D2", "module": 5, "points": 125,
        "title": "URL Decoding del Redirect",
        "objective": "El redirect de /devportal/internal contiene parámetros URL-encoded. Descúbrelos decodificándolos.",
        "question": "¿Qué parámetro oculto aparece al decodificar el header <code>Location</code> de <code>/devportal/internal</code>?",
        "answers": ["admin_mode"],
        "hint1": "GET a <code>/devportal/internal</code> en Repeater con <b>Follow redirects: Never</b>. Mira el header <code>Location</code>.",
        "hint2": "Copia el valor del header Location y llévalo a Burp <b>Decoder</b>. Decodifícalo como URL.",
        "hint3": "La URL decodificada contiene un parámetro de query especial que no era visible antes.",
        "burp_tip": "En Burp Repeater, configura <b>Follow redirects → Never</b> para poder ver la respuesta 302 con el header Location.",
    },
    {
        "id": "D3", "module": 5, "points": 200,
        "title": "Decodificación Hexadecimal",
        "objective": "El key ID 17 devuelve un secreto en hexadecimal. Decodifícalo para obtener la contraseña del admin.",
        "question": "¿Qué contraseña obtienes al decodificar el valor hex de <code>/devportal/api/v1/keys/17</code>?",
        "answers": ["C4rt3r-S3cur3!"],
        "hint1": "GET <code>/devportal/api/v1/keys/17</code> con Bearer token. La respuesta JSON tiene un campo <code>value</code> en formato hex.",
        "hint2": "Copia el valor hex y llévalo al Burp <b>Decoder</b>. Decodifícalo como <b>Hex</b>.",
        "hint3": "El valor decodificado es la contraseña del usuario administrador <code>a.carter</code>.",
        "burp_tip": "En Burp Decoder, pega el hex y selecciona <b>Decode as → Hex</b>. El resultado es la contraseña en texto plano.",
    },
    # ── MÓDULO 6: Escalada Final ──────────────────────────────────────────
    {
        "id": "F1", "module": 6, "points": 200,
        "title": "Login como Administrador",
        "objective": "Con el usuario y contraseña del admin obtenidos, autentícate y consigue el token de administración.",
        "question": "¿Cuál es el <code>admin_token</code> en la respuesta JSON al hacer login como <code>a.carter</code>?",
        "answers": ["ADM-2026-N0V3R4-CART3R"],
        "hint1": "POST <code>/devportal/login</code> con JSON: <code>{\"username\":\"a.carter\",\"password\":\"C4rt3r-S3cur3!\"}</code>.",
        "hint2": "La respuesta JSON incluye un campo <code>admin_token</code> adicional para usuarios con rol admin.",
        "hint3": "El token empieza por <code>ADM-2026-</code> y es la llave para el endpoint final.",
        "burp_tip": "Asegúrate de enviar <code>Content-Type: application/json</code> en la petición para que el servidor procese el body JSON.",
    },
    {
        "id": "F2", "module": 6, "points": 250,
        "title": "Flag Final — Acceso Total al Sistema",
        "objective": "Usa el token de admin para acceder al endpoint protegido y capturar la flag del sistema.",
        "question": "¿Cuál es la flag del sistema en <code>/devportal/admin/flag</code>?",
        "answers": ["OSCPBT{n0v3r4_d3vp0rtal_3num3r4t3d}"],
        "hint1": "GET <code>/devportal/admin/flag</code> añadiendo el header <code>X-Admin-Token: ADM-2026-N0V3R4-CART3R</code>.",
        "hint2": "También puedes usar la cookie de sesión activa de admin en lugar del header.",
        "hint3": "La respuesta JSON tiene el campo <code>flag</code> con el valor de la flag.",
        "burp_tip": "Añade el header <code>X-Admin-Token</code> en el <b>Inspector → Request headers → botón +</b> de Burp Repeater.",
    },
]

CHALLENGE_MAP = {c["id"]: c for c in CHALLENGES}
TOTAL_POINTS   = sum(c["points"] for c in CHALLENGES)

# ══════════════════════════════════════════════════════════════════════════════
# CSS COMÚN — TEMA OSCURO NOVERA
# ══════════════════════════════════════════════════════════════════════════════

BASE_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
    --bg:        #0d0d1a;
    --bg2:       #12132a;
    --bg3:       #1a1b35;
    --border:    #2a2b55;
    --text:      #c9d1e0;
    --text-dim:  #6b7280;
    --accent:    #6366f1;
    --accent2:   #8b5cf6;
    --green:     #10b981;
    --yellow:    #f59e0b;
    --red:       #ef4444;
    --orange:    #f97316;
    --radius:    10px;
    --shadow:    0 4px 24px rgba(0,0,0,.45);
}
body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    font-size: 15px;
    line-height: 1.6;
}
a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent2); text-decoration: underline; }
code, pre {
    font-family: 'Cascadia Code', 'Fira Code', 'Courier New', monospace;
    background: rgba(99,102,241,.15);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.87em;
    color: #a5b4fc;
}
pre { padding: 14px; white-space: pre-wrap; word-break: break-all; }

/* NAV */
.nav {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    display: flex;
    align-items: center;
    gap: 24px;
    height: 56px;
    position: sticky; top: 0; z-index: 100;
}
.nav-brand { font-weight: 700; font-size: 1rem; color: #fff; letter-spacing: .02em; }
.nav-brand span { color: var(--orange); }
.nav-links { display: flex; gap: 4px; margin-left: auto; }
.nav-links a {
    color: var(--text-dim); padding: 6px 12px; border-radius: 6px;
    font-size: 0.88em; transition: .15s;
}
.nav-links a:hover, .nav-links a.active {
    background: rgba(99,102,241,.18); color: #fff; text-decoration: none;
}
.badge {
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 0.75em; font-weight: 600;
}
.badge-green  { background: rgba(16,185,129,.18); color: var(--green); }
.badge-yellow { background: rgba(245,158,11,.18);  color: var(--yellow); }
.badge-red    { background: rgba(239,68,68,.18);   color: var(--red); }
.badge-purple { background: rgba(99,102,241,.18);  color: #a5b4fc; }

/* CONTAINERS */
.container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
.page-title {
    font-size: 1.55rem; font-weight: 700; color: #fff;
    margin-bottom: 6px; letter-spacing: -.01em;
}
.page-subtitle { color: var(--text-dim); margin-bottom: 28px; font-size: 0.93em; }

/* CARDS */
.card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 22px 24px;
    box-shadow: var(--shadow);
}
.card + .card { margin-top: 16px; }

/* MÓDULOS */
.module-header {
    display: flex; align-items: center; gap: 10px;
    font-size: 0.82em; font-weight: 600;
    color: var(--text-dim); letter-spacing: .05em; text-transform: uppercase;
    margin: 28px 0 12px;
}
.module-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* CHALLENGE GRID */
.challenge-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(310px,1fr)); gap: 14px; }
.challenge-card {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 18px 20px;
    transition: .2s; cursor: pointer; display: block;
    text-decoration: none !important; color: inherit;
}
.challenge-card:hover { border-color: var(--accent); transform: translateY(-2px); box-shadow: var(--shadow); }
.challenge-card.solved { border-color: var(--green); background: rgba(16,185,129,.05); }
.challenge-card.solved:hover { border-color: #34d399; }
.ch-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
.ch-id { font-size: 0.72em; font-weight: 700; color: var(--text-dim); letter-spacing: .08em; }
.ch-pts { font-size: 0.78em; color: var(--yellow); font-weight: 600; white-space: nowrap; }
.ch-title { font-weight: 600; font-size: 1rem; color: #e0e6f0; margin-bottom: 4px; }
.ch-obj { font-size: 0.84em; color: var(--text-dim); }
.ch-solved-badge { display: flex; align-items: center; gap: 4px; font-size: 0.8em; color: var(--green); font-weight: 600; }

/* CHALLENGE DETAIL — 2 columnas */
.challenge-layout {
    display: grid; grid-template-columns: 1fr 400px; gap: 24px; align-items: start;
}
@media (max-width: 900px) { .challenge-layout { grid-template-columns: 1fr; } }

.ch-panel { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); }
.ch-panel-head {
    padding: 16px 20px; border-bottom: 1px solid var(--border);
    font-weight: 600; color: #fff; display: flex; align-items: center; gap: 8px;
}
.ch-panel-body { padding: 20px; }

.objective-box {
    background: rgba(99,102,241,.08); border: 1px solid rgba(99,102,241,.3);
    border-radius: 8px; padding: 14px 16px; margin-bottom: 18px;
    font-size: 0.9em;
}
.objective-box strong { color: var(--accent); display: block; margin-bottom: 4px; font-size: 0.78em; text-transform: uppercase; letter-spacing: .05em; }

.burp-tip {
    background: rgba(245,158,11,.07); border-left: 3px solid var(--yellow);
    border-radius: 0 8px 8px 0; padding: 12px 14px;
    font-size: 0.86em; color: #d1c07a; margin-top: 18px;
}
.burp-tip strong { color: var(--yellow); }

/* FORMULARIO */
.answer-form { display: flex; flex-direction: column; gap: 12px; }
.answer-label { font-size: 0.85em; color: var(--text-dim); font-weight: 500; }
.answer-input {
    width: 100%; background: var(--bg3); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 14px; color: #fff; font-size: 0.95em;
    font-family: 'Cascadia Code', 'Fira Code', monospace;
    outline: none; transition: .15s;
}
.answer-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(99,102,241,.2); }
.btn {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 10px 20px; border-radius: 8px; border: none;
    font-size: 0.92em; font-weight: 600; cursor: pointer; transition: .15s;
}
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { background: var(--accent2); }
.btn-sm { padding: 6px 14px; font-size: 0.82em; }
.btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--text-dim); }
.btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
.btn-danger { background: rgba(239,68,68,.15); color: var(--red); border: 1px solid rgba(239,68,68,.3); }
.btn-danger:hover { background: rgba(239,68,68,.25); }

/* ALERTS */
.alert {
    padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;
    font-size: 0.9em; border: 1px solid;
}
.alert-success { background: rgba(16,185,129,.1); border-color: rgba(16,185,129,.3); color: #6ee7b7; }
.alert-error   { background: rgba(239,68,68,.1);  border-color: rgba(239,68,68,.3);  color: #fca5a5; }
.alert-info    { background: rgba(99,102,241,.1); border-color: rgba(99,102,241,.3); color: #c7d2fe; }

/* HINTS */
.hints-section { margin-top: 20px; }
.hints-title { font-size: 0.8em; color: var(--text-dim); text-transform: uppercase; letter-spacing: .05em; font-weight: 600; margin-bottom: 8px; }
details.hint-item {
    background: var(--bg3); border: 1px solid var(--border);
    border-radius: 8px; margin-bottom: 6px; overflow: hidden;
}
details.hint-item summary {
    padding: 10px 14px; cursor: pointer; font-size: 0.85em;
    font-weight: 500; color: var(--text-dim); list-style: none;
    display: flex; align-items: center; gap: 8px;
}
details.hint-item summary:hover { color: var(--yellow); }
details.hint-item[open] summary { color: var(--yellow); border-bottom: 1px solid var(--border); }
details.hint-item .hint-body { padding: 12px 14px; font-size: 0.87em; }

/* PROGRESS */
.progress-bar-wrap {
    background: var(--bg3); border-radius: 999px; height: 8px; overflow: hidden; margin-top: 6px;
}
.progress-bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 999px; transition: .5s; }

/* SOLVED indicator */
.solved-overlay {
    background: rgba(16,185,129,.12); border: 1px solid rgba(16,185,129,.3);
    border-radius: 8px; padding: 14px 16px; text-align: center;
}
.solved-overlay .sol-icon { font-size: 2rem; }
.solved-overlay .sol-text { color: var(--green); font-weight: 700; font-size: 1.05em; }

/* MASK */
.masked { letter-spacing: .08em; color: var(--text-dim); }

/* SCROLLBAR */
::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* FINAL PAGE */
.flag-display {
    background: var(--bg3); border: 1px solid var(--green);
    border-radius: var(--radius); padding: 20px 24px;
    font-family: 'Cascadia Code','Fira Code',monospace;
    font-size: 1.15em; color: #6ee7b7; letter-spacing: .04em;
    word-break: break-all; margin: 20px 0;
}
"""

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE SESIÓN / PROGRESO (PLATAFORMA DE RETOS)
# ══════════════════════════════════════════════════════════════════════════════

def init_training_session():
    if "training_uid" not in session:
        session["training_uid"] = str(uuid.uuid4())[:8]
    if "solved" not in session:
        session["solved"] = {}
    if "hints_used" not in session:
        session["hints_used"] = {}
    if "mode" not in session:
        session["mode"] = "guided"  # aprendizaje | guided | autonomo


def get_progress():
    init_training_session()
    solved = session.get("solved", {})
    pts = sum(CHALLENGE_MAP[cid]["points"] for cid in solved if cid in CHALLENGE_MAP)
    return len(solved), pts


def mask_answer(answer: str) -> str:
    return "•" * len(answer)


# ══════════════════════════════════════════════════════════════════════════════
# RUTAS DEL DEVPORTAL VULNERABLE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def root_redirect():
    return redirect("/devportal/")


@app.route("/robots.txt")
def robots_txt():
    content = (
        "User-agent: *\n"
        "Disallow: /devportal/internal\n"
        "Disallow: /devportal/admin\n"
        "Disallow: /devportal/backup\n"
        "Disallow: /devportal/.git\n"
        "Disallow: /devportal/config.bak\n"
        "\n"
        "# Novera Group DevPortal — Internal development only\n"
    )
    r = make_response(content, 200)
    r.headers["Content-Type"] = "text/plain"
    return r


@app.route("/devportal/")
@app.route("/devportal")
def devportal_home():
    html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Novera Group — DevPortal</title>
<style>
body{background:#0a0a14;color:#c9d1e0;font-family:'Segoe UI',sans-serif;margin:0;padding:0}
.topbar{background:#11122a;border-bottom:1px solid #22235a;padding:0 32px;height:52px;display:flex;align-items:center;gap:16px}
.logo{font-weight:700;font-size:1.05rem;color:#fff}.logo span{color:#f97316}
nav a{color:#6b7280;font-size:0.88em;padding:6px 12px;border-radius:6px;text-decoration:none}
nav a:hover{background:rgba(99,102,241,.15);color:#fff}
.hero{max-width:900px;margin:80px auto;text-align:center;padding:0 24px}
.hero h1{font-size:2.4rem;font-weight:800;color:#fff;margin-bottom:12px}
.hero p{color:#6b7280;font-size:1.05rem;margin-bottom:32px}
.btn{display:inline-block;padding:12px 28px;background:#6366f1;color:#fff;border-radius:8px;font-weight:600;text-decoration:none;margin:6px;transition:.15s}
.btn:hover{background:#4f46e5}
.btn-outline{background:transparent;border:1px solid #2a2b55;color:#a5b4fc}
.btn-outline:hover{border-color:#6366f1;background:rgba(99,102,241,.1)}
.status{display:inline-flex;align-items:center;gap:6px;font-size:0.82em;color:#10b981;background:rgba(16,185,129,.12);padding:4px 12px;border-radius:999px;border:1px solid rgba(16,185,129,.25);margin-bottom:28px}
.dot{width:7px;height:7px;border-radius:50%;background:#10b981;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
footer{text-align:center;padding:40px;color:#374151;font-size:0.8em;border-top:1px solid #1a1b35;margin-top:80px}
</style>
</head>
<body>
<div class="topbar">
  <div class="logo">Novera<span>.</span>DevPortal</div>
  <nav style="margin-left:auto">
    <a href="/devportal/">Inicio</a>
    <a href="/devportal/search">Búsqueda</a>
    <a href="/devportal/login">Acceder</a>
  </nav>
</div>
<div class="hero">
  <div class="status"><div class="dot"></div> Sistema operativo — v2.3.1</div>
  <h1>Portal de Desarrolladores<br>Novera Group</h1>
  <p>Plataforma interna de gestión de APIs, credenciales y herramientas<br>para el equipo de desarrollo de Novera Group.</p>
  <a href="/devportal/login" class="btn">Iniciar Sesión</a>
  <a href="/devportal/search" class="btn btn-outline">Búsqueda</a>
</div>
<!-- TODO: mover la documentacion de la API a /devportal/api/v1/docs antes del release de produccion -->
<!-- Internal build: NVR-DEVPORTAL-2.3.1-20261031 -->
<footer>
  &copy; 2026 Novera Group &mdash; Internal Use Only &mdash; All access is monitored and logged
</footer>
</body>
</html>"""
    r = make_response(html, 200)
    return add_devportal_headers(r)


@app.route("/devportal/login", methods=["GET", "POST"])
def devportal_login():
    login_form = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Login — Novera DevPortal</title>
<style>
body{background:#0a0a14;color:#c9d1e0;font-family:'Segoe UI',sans-serif;margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh}
.box{background:#11122a;border:1px solid #22235a;border-radius:12px;padding:36px 40px;width:380px;box-shadow:0 8px 32px rgba(0,0,0,.5)}
h2{color:#fff;margin-bottom:4px;font-size:1.3rem}
p{color:#6b7280;font-size:0.85em;margin-bottom:28px}
label{display:block;font-size:0.82em;color:#9ca3af;margin-bottom:6px;font-weight:500}
input{width:100%;background:#0d0e22;border:1px solid #2a2b55;border-radius:8px;padding:10px 14px;color:#fff;font-size:0.95em;margin-bottom:16px;outline:none;font-family:inherit}
input:focus{border-color:#6366f1;box-shadow:0 0 0 3px rgba(99,102,241,.2)}
button{width:100%;background:#6366f1;color:#fff;border:none;border-radius:8px;padding:11px;font-weight:600;cursor:pointer;font-size:0.95em}
button:hover{background:#4f46e5}
.msg{padding:10px 14px;border-radius:8px;margin-bottom:16px;font-size:0.88em}
.msg.err{background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);color:#fca5a5}
.msg.ok{background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3);color:#6ee7b7}
.logo{font-size:0.85em;color:#6b7280;margin-bottom:20px}
.logo span{color:#f97316;font-weight:700}
</style>
</head>
<body>
<div class="box">
  <div class="logo">Novera<span>.</span>DevPortal</div>
  <h2>Acceso al Portal</h2>
  <p>Introduce tus credenciales de desarrollador</p>
  {MSG}
  <form method="POST">
    <label>Usuario</label>
    <input name="username" placeholder="usuario@novera" required autocomplete="off">
    <label>Contraseña</label>
    <input name="password" type="password" placeholder="••••••••••••" required>
    <button type="submit">Iniciar sesión</button>
  </form>
</div>
</body>
</html>"""

    if request.method == "GET":
        r = make_response(login_form.replace("{MSG}", ""), 200)
        return add_devportal_headers(r)

    # POST — acepta JSON o form
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = DEVPORTAL_USERS.get(username)

    if not user:
        # Usuario no existe — user enumeration vulnerability
        if request.is_json:
            r = jsonify({"error": "user_not_found", "message": "Usuario no encontrado"})
            r.status_code = 401
            return add_devportal_headers(r)
        msg = '<div class="msg err">⚠ Usuario no encontrado</div>'
        r = make_response(login_form.replace("{MSG}", msg), 401)
        return add_devportal_headers(r)

    if not user["active"]:
        if request.is_json:
            r = jsonify({"error": "account_disabled", "message": "Cuenta desactivada"})
            r.status_code = 403
            return add_devportal_headers(r)
        msg = '<div class="msg err">🔒 Cuenta desactivada</div>'
        r = make_response(login_form.replace("{MSG}", msg), 403)
        return add_devportal_headers(r)

    if user["password"] != password:
        # Contraseña incorrecta — mensaje diferente al de usuario no encontrado
        if request.is_json:
            r = jsonify({"error": "invalid_password", "message": "Contraseña incorrecta"})
            r.status_code = 401
            return add_devportal_headers(r)
        msg = '<div class="msg err">❌ Contraseña incorrecta</div>'
        r = make_response(login_form.replace("{MSG}", msg), 401)
        return add_devportal_headers(r)

    # Login OK
    session["devportal_user"] = username
    session["devportal_role"] = user["role"]

    devportal_token = make_devportal_token(username)

    if request.is_json:
        payload = {
            "status": "ok",
            "username": username,
            "role": user["role"],
            "email": user["email"],
            "session_token": devportal_token,
        }
        if user["role"] == "admin":
            payload["admin_token"] = ADMIN_TOKEN_VALUE
        r = jsonify(payload)
        r.set_cookie("devportal_token", devportal_token, httponly=False)
        return add_devportal_headers(r)

    msg = f'<div class="msg ok">✅ Bienvenido, {username}</div>'
    r = make_response(login_form.replace("{MSG}", msg), 200)
    r.set_cookie("devportal_token", devportal_token, httponly=False)
    return add_devportal_headers(r)


@app.route("/devportal/logout")
def devportal_logout():
    session.pop("devportal_user", None)
    session.pop("devportal_role", None)
    r = make_response("", 302)
    r.headers["Location"] = "/devportal/"
    r.delete_cookie("devportal_token")
    return r


@app.route("/devportal/search")
def devportal_search():
    query = request.args.get("q", "")
    debug = request.args.get("debug", "")

    result = {
        "query": query,
        "results": [],
        "total": 0,
    }

    if debug.lower() in ("true", "1", "yes", "on"):
        result["debug_info"] = {
            "server": "NoveraPortal/2.3.1",
            "db_host": "10.10.0.5",
            "index": "devportal_docs_v2",
            "query_time_ms": 12,
            "internal_user": "search_svc",
            "note": "debug mode activo — deshabilitar en produccion",
        }

    r = jsonify(result)
    return add_devportal_headers(r)


@app.route("/devportal/config.bak")
def devportal_config_bak():
    content = (
        "# Novera Group DevPortal — Configuracion de Produccion\n"
        "# ATENCION: NO SUBIR AL REPOSITORIO\n"
        "# Generado: 2026-10-31\n"
        "\n"
        "# Base de datos\n"
        "DB_HOST=10.10.0.5\n"
        "DB_PORT=5432\n"
        "DB_NAME=devportal_prod\n"
        "DB_USER=dp_app\n"
        "DB_PASS=N0v3r4-DB-2026!\n"
        "\n"
        "# API\n"
        "API_TOKEN=dev-token-jm-2026\n"
        "API_VERSION=v1\n"
        "API_RATE_LIMIT=100\n"
        "\n"
        "# Seguridad\n"
        "SECRET_KEY=n0v3r4-enum-lab2-2026-s3cr3t-k3y\n"
        "SESSION_TIMEOUT=3600\n"
        "MFA_ENABLED=false\n"
        "\n"
        "# Correo\n"
        "SMTP_HOST=mail.novera.corp\n"
        "SMTP_PORT=587\n"
        "SMTP_USER=devportal@novera.corp\n"
    )
    r = make_response(content, 200)
    r.headers["Content-Type"] = "text/plain"
    return add_devportal_headers(r)


@app.route("/devportal/internal")
def devportal_internal():
    # Challenge D2: redirect con parámetro URL-encoded
    dest = quote("/devportal/admin/dashboard?admin_mode=true&src=internal", safe="")
    r = make_response("", 302)
    r.headers["Location"] = f"/devportal/login?next={dest}"
    return add_devportal_headers(r)


# ── API v1 ─────────────────────────────────────────────────────────────────

@app.route("/devportal/api/v1/docs")
def api_v1_docs():
    data = {
        "api": "Novera DevPortal API",
        "version": "v1",
        "base_url": "/devportal/api/v1",
        "auth": "Bearer token requerido en header Authorization",
        "endpoints": [
            {"method": "GET",  "path": "/devportal/api/v1/docs",    "auth": False, "description": "Esta documentación"},
            {"method": "GET",  "path": "/devportal/api/v1/status",  "auth": False, "description": "Estado del sistema"},
            {"method": "GET",  "path": "/devportal/api/v1/users",   "auth": True,  "description": "Listado de usuarios"},
            {"method": "POST", "path": "/devportal/api/v1/unlock",  "auth": False, "description": "Desbloqueo por PIN"},
            {"method": "GET",  "path": "/devportal/api/v1/profile", "auth": True,  "description": "Perfil del usuario autenticado"},
            {"method": "GET",  "path": "/devportal/api/v1/keys/{id}", "auth": True, "description": "Consulta de API key por ID"},
            {"method": "POST", "path": "/devportal/api/v1/rotate",  "auth": True,  "description": "Rotación de API key"},
            {"method": "GET",  "path": "/devportal/api/v1/audit",   "auth": True,  "description": "Log de auditoría (solo admin)"},
        ],
    }
    r = jsonify(data)
    return add_devportal_headers(r)


@app.route("/devportal/api/v1/status")
def api_v1_status():
    r = jsonify({
        "status": "operational",
        "version": "2.3.1",
        "environment": "production",
        "uptime_hours": 2187,
    })
    return add_devportal_headers(r)


@app.route("/devportal/api/v1/users")
def api_v1_users():
    err = require_api_token()
    if err:
        return add_devportal_headers(err[0]), err[1]

    users_list = [
        {"username": u, "email": v["email"], "role": v["role"], "active": v["active"]}
        for u, v in DEVPORTAL_USERS.items()
    ]
    r = jsonify({"total": len(users_list), "users": users_list})
    return add_devportal_headers(r)


@app.route("/devportal/api/v1/unlock", methods=["POST"])
def api_v1_unlock():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    pin = str(data.get("pin", "")).strip()

    user = DEVPORTAL_USERS.get(username)
    if not user:
        r = jsonify({"error": "user_not_found"})
        r.status_code = 404
        return add_devportal_headers(r)

    if user.get("pin") is None:
        r = jsonify({"error": "pin_not_required", "message": "Este usuario no usa PIN"})
        r.status_code = 400
        return add_devportal_headers(r)

    if pin == user["pin"]:
        r = jsonify({"status": "unlocked", "username": username, "token": f"unlock-{username}-{pin}"})
        return add_devportal_headers(r)

    r = jsonify({"error": "invalid_pin", "message": "PIN incorrecto"})
    r.status_code = 401
    return add_devportal_headers(r)


@app.route("/devportal/api/v1/profile")
def api_v1_profile():
    err = require_api_token()
    if err:
        return add_devportal_headers(err[0]), err[1]

    token = get_bearer_token()
    username = API_TOKENS.get(token, "unknown")
    user = DEVPORTAL_USERS.get(username, {})

    r = jsonify({
        "username": username,
        "email": user.get("email", ""),
        "role": user.get("role", ""),
        "admin_jwt": FAKE_ADMIN_JWT,
        "note": "El campo admin_jwt contiene informacion del administrador del sistema",
    })
    return add_devportal_headers(r)


@app.route("/devportal/api/v1/keys/<int:kid>")
def api_v1_keys(kid):
    err = require_api_token()
    if err:
        return add_devportal_headers(err[0]), err[1]

    if kid == 17:
        r = jsonify({
            "id": 17,
            "name": "admin-emergency-credentials",
            "encoding": "hex",
            "value": HEX_SECRET,
            "note": "Credenciales de emergencia del administrador — SOLO USO INTERNO",
            "created": "2026-01-15",
        })
        return add_devportal_headers(r)

    if 1 <= kid <= 50:
        r = jsonify({"error": "key_not_found", "id": kid})
        r.status_code = 404
        return add_devportal_headers(r)

    r = jsonify({"error": "invalid_id"})
    r.status_code = 400
    return add_devportal_headers(r)


@app.route("/devportal/api/v1/rotate", methods=["POST"])
def api_v1_rotate():
    err = require_api_token()
    if err:
        return add_devportal_headers(err[0]), err[1]
    r = jsonify({"status": "not_implemented", "message": "Funcionalidad en desarrollo"})
    r.status_code = 501
    return add_devportal_headers(r)


@app.route("/devportal/api/v1/audit")
def api_v1_audit():
    err = require_api_token()
    if err:
        return add_devportal_headers(err[0]), err[1]

    token = get_bearer_token()
    username = API_TOKENS.get(token, "")
    user = DEVPORTAL_USERS.get(username, {})
    if user.get("role") != "admin":
        r = jsonify({"error": "forbidden", "message": "Solo administradores"})
        r.status_code = 403
        return add_devportal_headers(r)

    r = jsonify({"log": [], "note": "Audit log vacio en este entorno de laboratorio"})
    return add_devportal_headers(r)


# ── Reset de contraseña ────────────────────────────────────────────────────

@app.route("/devportal/reset", methods=["POST"])
def devportal_reset():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()

    if token == VALID_RESET_TOKEN or token.rstrip("=") == VALID_RESET_TOKEN.rstrip("="):
        r = jsonify({
            "status": "token_valid",
            "message": "Token correcto. Puedes establecer una nueva contraseña.",
            "reset_session": "rst-42-novera-2026",
        })
        return add_devportal_headers(r)

    r = jsonify({"error": "invalid_token", "message": "Token de reset inválido o expirado"})
    r.status_code = 400
    return add_devportal_headers(r)


# ── Panel de admin ─────────────────────────────────────────────────────────

def is_admin_request():
    """Comprueba si la petición tiene credenciales de admin (sesión o token header)."""
    if session.get("devportal_role") == "admin":
        return True
    x_token = request.headers.get("X-Admin-Token", "")
    if x_token == ADMIN_TOKEN_VALUE:
        return True
    return False


@app.route("/devportal/admin/dashboard")
def devportal_admin_dashboard():
    if not is_admin_request():
        r = jsonify({
            "error": "forbidden",
            "message": "Acceso denegado. Se requieren privilegios de administrador.",
            "hint": "Usa el header X-Admin-Token o inicia sesión como admin.",
        })
        r.status_code = 403
        return add_devportal_headers(r)

    r = jsonify({
        "status": "admin_panel",
        "message": "Bienvenido al panel de administración de Novera DevPortal",
        "internal_code": "NV3R4-ENUM-2026",
        "active_users": len([u for u in DEVPORTAL_USERS.values() if u["active"]]),
        "system_version": "2.3.1",
        "endpoints": [
            "/devportal/admin/dashboard",
            "/devportal/admin/flag",
        ],
    })
    return add_devportal_headers(r)


@app.route("/devportal/admin/flag")
def devportal_admin_flag():
    if not is_admin_request():
        r = jsonify({
            "error": "forbidden",
            "message": "Acceso denegado. Se requieren privilegios de administrador.",
            "hint": "Añade el header X-Admin-Token con el valor correcto.",
        })
        r.status_code = 403
        return add_devportal_headers(r)

    r = jsonify({
        "status": "pwned",
        "message": "¡Acceso completo obtenido! Has comprometido el DevPortal de Novera Group.",
        "flag": FINAL_FLAG,
        "congratulations": "Excelente trabajo de reconocimiento y enumeración.",
    })
    return add_devportal_headers(r)


# ══════════════════════════════════════════════════════════════════════════════
# PLATAFORMA DE RETOS — /help/*
# ══════════════════════════════════════════════════════════════════════════════

def nav_html(active=""):
    solved_count, pts = get_progress()
    return f"""
<nav class="nav">
  <span class="nav-brand">OSCPT <span>Enum</span> Trainer</span>
  <div class="nav-links">
    <a href="/help/" class="{'active' if active=='home' else ''}">Retos</a>
    <a href="/help/progress" class="{'active' if active=='progress' else ''}">Mi Progreso</a>
    <a href="/help/final" class="{'active' if active=='final' else ''}">Flag Final</a>
    <a href="/devportal/" target="_blank">DevPortal ↗</a>
  </div>
  <span class="badge badge-purple" style="margin-left:12px">{pts} pts</span>
</nav>"""


def base_page(title, content, active=""):
    return render_template_string("""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{title}} — OSCPT Enum Trainer</title>
<style>{{css}}</style>
</head>
<body>
{{nav}}
{{content}}
</body>
</html>""",
        title=title, css=BASE_CSS, nav=nav_html(active), content=content
    )


@app.route("/help/")
@app.route("/help")
def help_home():
    init_training_session()
    solved  = session.get("solved", {})
    n_solved, pts = get_progress()
    pct     = round(n_solved / len(CHALLENGES) * 100)

    # Agrupa challenges por módulo
    by_module = {}
    for ch in CHALLENGES:
        by_module.setdefault(ch["module"], []).append(ch)

    cards_html = ""
    for mod_id in sorted(by_module.keys()):
        mod_info = MODULES[mod_id]
        cards_html += f"""
<div class="module-header">
  <div class="module-dot" style="background:{mod_info['color']}"></div>
  {mod_info['name']}
</div>
<div class="challenge-grid">"""
        for ch in by_module[mod_id]:
            is_solved = ch["id"] in solved
            solved_cls = " solved" if is_solved else ""
            solved_badge = (
                '<div class="ch-solved-badge">✔ Resuelto</div>'
                if is_solved else
                f'<span class="badge badge-yellow">{ch["points"]} pts</span>'
            )
            cards_html += f"""
<a href="/help/challenge/{ch['id']}" class="challenge-card{solved_cls}">
  <div class="ch-header">
    <span class="ch-id">{ch['id']}</span>
    {solved_badge}
  </div>
  <div class="ch-title">{ch['title']}</div>
  <div class="ch-obj">{ch['objective'][:100]}{'…' if len(ch['objective'])>100 else ''}</div>
</a>"""
        cards_html += "</div>"

    content = f"""
<div class="container">
  <h1 class="page-title">🎓 OSCPT Enum Trainer — Lab 2</h1>
  <p class="page-subtitle">Reconocimiento · Enumeración · Intruder · Decoder | Novera Group DevPortal</p>

  <div class="card" style="margin-bottom:28px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
      <span style="font-weight:600;color:#fff">Progreso global</span>
      <span style="font-size:0.85em;color:var(--text-dim)">{n_solved}/{len(CHALLENGES)} retos · {pts}/{TOTAL_POINTS} pts</span>
    </div>
    <div class="progress-bar-wrap">
      <div class="progress-bar-fill" style="width:{pct}%"></div>
    </div>
  </div>

  <div style="background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.25);border-radius:10px;padding:16px 20px;margin-bottom:28px;font-size:0.9em">
    <strong style="color:#a5b4fc">🎯 Objetivo del laboratorio</strong><br>
    <span style="color:var(--text-dim)">Audita el portal interno de Novera Group. Usa Burp Suite para hacer reconocimiento pasivo,
    enumerar endpoints y usuarios, y finalmente escalar privilegios hasta obtener acceso de administrador.</span><br>
    <span style="color:var(--text-dim);margin-top:6px;display:block">🌐 Target: <code>http://localhost:8011/devportal/</code></span>
  </div>

  {cards_html}
</div>"""

    return base_page("Retos", content, active="home")


@app.route("/help/challenge/<cid>")
def help_challenge(cid):
    init_training_session()
    ch = CHALLENGE_MAP.get(cid.upper())
    if not ch:
        return "Reto no encontrado", 404

    solved    = session.get("solved", {})
    hints_used = session.get("hints_used", {}).get(cid, [])
    is_solved  = cid in solved
    mod_info   = MODULES[ch["module"]]

    # Panel izquierdo — descripción
    solved_html = ""
    if is_solved:
        answer_shown = solved[cid]
        solved_html = f"""
<div class="solved-overlay" style="margin-bottom:18px">
  <div class="sol-icon">✅</div>
  <div class="sol-text">¡Reto resuelto!</div>
  <div style="font-size:0.85em;color:var(--text-dim);margin-top:4px">Respuesta: <code>{answer_shown}</code></div>
</div>"""

    # Pistas
    hints_html = ""
    if not is_solved:
        hints_html = f"""
<div class="hints-section">
  <div class="hints-title">💡 Pistas disponibles</div>"""
        for lvl, (hkey, label, penalty) in enumerate([
            ("hint1", "Pista 1 — Dirección general", 0),
            ("hint2", "Pista 2 — Más específica",    0),
            ("hint3", "Pista 3 — Casi la solución",  0),
        ], 1):
            used = lvl in hints_used
            body = f'<div class="hint-body">{ch[hkey]}</div>' if used else ""
            reveal = f'<a href="/help/hint/{cid}/{lvl}" class="btn btn-sm btn-ghost" style="margin-left:auto;font-size:0.75em">Revelar</a>' if not used else ""
            hints_html += f"""
<details class="hint-item" {'open' if used else ''}>
  <summary>{label} {reveal}</summary>
  {body}
</details>"""
        hints_html += "</div>"

    left_panel = f"""
<div class="ch-panel">
  <div class="ch-panel-head">
    <span style="background:{mod_info['color']};width:10px;height:10px;border-radius:50%;flex-shrink:0"></span>
    {mod_info['name']} &nbsp;·&nbsp; <span style="color:var(--text-dim);font-weight:400">{ch['id']}</span>
    <span class="badge badge-yellow" style="margin-left:auto">{ch['points']} pts</span>
  </div>
  <div class="ch-panel-body">
    {solved_html}
    <div class="objective-box">
      <strong>Objetivo</strong>
      {ch['objective']}
    </div>
    <div style="font-size:0.95em;margin-bottom:16px">{ch['question']}</div>
    <div class="burp-tip">
      <strong>💡 Burp Tip:</strong> {ch['burp_tip']}
    </div>
    {hints_html}
  </div>
</div>"""

    # Panel derecho — formulario de respuesta
    if is_solved:
        right_content = f"""
<div class="solved-overlay">
  <div class="sol-icon" style="font-size:3rem">🏆</div>
  <div class="sol-text" style="font-size:1.2em;margin:8px 0">¡Completado!</div>
  <div style="color:var(--text-dim);font-size:0.88em">+{ch['points']} puntos conseguidos</div>
  <a href="/help/" class="btn btn-primary" style="margin-top:16px;width:100%;justify-content:center">← Volver a retos</a>
</div>"""
    else:
        right_content = f"""
<form class="answer-form" method="POST" action="/help/submit/{cid}">
  <div class="alert alert-info" style="font-size:0.85em">
    Escribe la respuesta exacta que encuentres en el DevPortal.
  </div>
  <label class="answer-label">Tu respuesta</label>
  <input
    class="answer-input"
    name="answer"
    placeholder="Escribe aquí tu respuesta..."
    autocomplete="off"
    spellcheck="false"
    required
  >
  <button type="submit" class="btn btn-primary">Verificar respuesta ▸</button>
  <a href="/help/" class="btn btn-ghost" style="text-align:center">← Volver</a>
</form>"""

    flash = request.args.get("flash", "")
    flash_html = ""
    if flash == "wrong":
        flash_html = '<div class="alert alert-error">❌ Respuesta incorrecta. ¡Sigue intentándolo!</div>'
    elif flash == "ok":
        flash_html = '<div class="alert alert-success">✅ ¡Correcto! Reto superado.</div>'

    right_panel = f"""
<div class="ch-panel">
  <div class="ch-panel-head">✏️ Responde el reto</div>
  <div class="ch-panel-body">
    {flash_html}
    {right_content}
  </div>
</div>"""

    content = f"""
<div class="container">
  <div style="margin-bottom:20px">
    <a href="/help/" style="font-size:0.85em;color:var(--text-dim)">← Todos los retos</a>
    <h1 class="page-title" style="margin-top:8px">{ch['title']}</h1>
    <p class="page-subtitle">{mod_info['name']}</p>
  </div>
  <div class="challenge-layout">
    {left_panel}
    {right_panel}
  </div>
</div>"""

    return base_page(ch["title"], content)


@app.route("/help/submit/<cid>", methods=["POST"])
def help_submit(cid):
    init_training_session()
    ch = CHALLENGE_MAP.get(cid.upper())
    if not ch:
        return "Reto no encontrado", 404

    answer = request.form.get("answer", "").strip()
    correct_answers = [a.lower() for a in ch["answers"]]

    if answer.lower() in correct_answers:
        session["solved"] = session.get("solved", {})
        session["solved"][cid] = answer
        session.modified = True
        return redirect(f"/help/challenge/{cid}?flash=ok")

    return redirect(f"/help/challenge/{cid}?flash=wrong")


@app.route("/help/hint/<cid>/<int:level>")
def help_hint(cid, level):
    init_training_session()
    ch = CHALLENGE_MAP.get(cid.upper())
    if not ch or level not in (1, 2, 3):
        return redirect(f"/help/challenge/{cid}")

    hints_used = session.get("hints_used", {})
    hints_used.setdefault(cid, [])
    if level not in hints_used[cid]:
        hints_used[cid].append(level)
    session["hints_used"] = hints_used
    session.modified = True

    return redirect(f"/help/challenge/{cid}")


@app.route("/help/progress")
def help_progress():
    init_training_session()
    solved = session.get("solved", {})
    n_solved, pts = get_progress()
    pct = round(n_solved / len(CHALLENGES) * 100)

    by_module = {}
    for ch in CHALLENGES:
        by_module.setdefault(ch["module"], []).append(ch)

    rows = ""
    for mod_id in sorted(by_module.keys()):
        mod_info = MODULES[mod_id]
        mod_challenges = by_module[mod_id]
        mod_solved = sum(1 for c in mod_challenges if c["id"] in solved)
        for ch in mod_challenges:
            is_solved = ch["id"] in solved
            status = (
                '<span class="badge badge-green">✔ Resuelto</span>'
                if is_solved else
                '<span class="badge" style="background:rgba(107,114,128,.15);color:#6b7280">Pendiente</span>'
            )
            pts_cell = f'+{ch["points"]}' if is_solved else f'{ch["points"]}'
            rows += f"""
<tr>
  <td><span style="color:{mod_info['color']};font-size:0.78em;font-weight:700">{mod_info['name']}</span></td>
  <td><code style="font-size:0.82em">{ch['id']}</code></td>
  <td style="color:#e0e6f0">{ch['title']}</td>
  <td style="text-align:center">{status}</td>
  <td style="text-align:right;color:{'var(--green)' if is_solved else 'var(--text-dim)'};font-weight:600">{pts_cell}</td>
</tr>"""

    content = f"""
<div class="container">
  <h1 class="page-title">📊 Mi Progreso</h1>
  <p class="page-subtitle">Sesión: <code>{session.get('training_uid','')}</code></p>

  <div class="card" style="margin-bottom:24px">
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;text-align:center">
      <div>
        <div style="font-size:2rem;font-weight:800;color:#fff">{n_solved}</div>
        <div style="font-size:0.82em;color:var(--text-dim)">Retos resueltos</div>
      </div>
      <div>
        <div style="font-size:2rem;font-weight:800;color:var(--yellow)">{pts}</div>
        <div style="font-size:0.82em;color:var(--text-dim)">Puntos</div>
      </div>
      <div>
        <div style="font-size:2rem;font-weight:800;color:var(--accent)">{pct}%</div>
        <div style="font-size:0.82em;color:var(--text-dim)">Completado</div>
      </div>
    </div>
    <div class="progress-bar-wrap" style="margin-top:20px">
      <div class="progress-bar-fill" style="width:{pct}%"></div>
    </div>
  </div>

  <div class="card">
    <table style="width:100%;border-collapse:collapse">
      <thead>
        <tr style="border-bottom:1px solid var(--border);font-size:0.82em;color:var(--text-dim)">
          <th style="text-align:left;padding:8px 12px">Módulo</th>
          <th style="text-align:left;padding:8px 4px">ID</th>
          <th style="text-align:left;padding:8px 4px">Reto</th>
          <th style="text-align:center;padding:8px 4px">Estado</th>
          <th style="text-align:right;padding:8px 12px">Puntos</th>
        </tr>
      </thead>
      <tbody style="font-size:0.88em">
        {rows}
      </tbody>
    </table>
  </div>

  <form method="POST" action="/help/reset" style="margin-top:20px;text-align:right"
        onsubmit="return confirm('¿Seguro que quieres reiniciar todo tu progreso?')">
    <button type="submit" class="btn btn-danger btn-sm">🗑 Reiniciar progreso</button>
  </form>
</div>"""

    return base_page("Mi Progreso", content, active="progress")


@app.route("/help/reset", methods=["POST"])
def help_reset():
    session.pop("solved", None)
    session.pop("hints_used", None)
    session.modified = True
    return redirect("/help/")


@app.route("/help/final")
def help_final():
    init_training_session()
    n_solved, pts = get_progress()
    pct = round(n_solved / len(CHALLENGES) * 100)

    congrats = ""
    if n_solved == len(CHALLENGES):
        congrats = """
<div style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);border-radius:10px;padding:20px;text-align:center;margin-bottom:24px">
  <div style="font-size:2.5rem">🏆</div>
  <div style="font-size:1.3rem;font-weight:700;color:#6ee7b7;margin:8px 0">¡Laboratorio completado al 100%!</div>
  <div style="color:var(--text-dim);font-size:0.9em">Has completado todos los retos del OSCPT Enum Trainer.</div>
</div>"""

    content = f"""
<div class="container" style="max-width:720px">
  <h1 class="page-title">🏁 Flag Final</h1>
  <p class="page-subtitle">Compromiso del DevPortal de Novera Group</p>

  {congrats}

  <div class="card">
    <h3 style="color:#fff;margin-bottom:16px;font-size:1.1rem">🎯 Flujo de ataque completo</h3>
    <ol style="color:var(--text-dim);font-size:0.9em;line-height:2;padding-left:20px">
      <li><strong style="color:#e0e6f0">Reconocimiento:</strong> Header <code>X-Powered-By</code> → <code>robots.txt</code> → comentario HTML con endpoint de API docs</li>
      <li><strong style="color:#e0e6f0">Enumeración de API:</strong> Descubrir 8 endpoints → fuzzing de parámetro <code>debug</code> → archivo <code>config.bak</code> con API token</li>
      <li><strong style="color:#e0e6f0">User Enumeration:</strong> Mensajes de error diferentes → usuario <code>j.morgan</code> → lista completa vía API → admin <code>a.carter</code></li>
      <li><strong style="color:#e0e6f0">Intruder:</strong> PIN brute force (4829) → token reset predecible (NDI=) → key ID 17 → JWT con sub claim</li>
      <li><strong style="color:#e0e6f0">Decoder:</strong> Cookie Base64 → URL decode del redirect → hex decode de la contraseña del admin</li>
      <li><strong style="color:#e0e6f0">Escalada:</strong> Login como <code>a.carter</code> → admin_token → GET <code>/devportal/admin/flag</code></li>
    </ol>
  </div>

  <div class="card" style="margin-top:16px">
    <h3 style="color:#fff;margin-bottom:8px;font-size:1rem">🚩 Flag del sistema</h3>
    <p style="color:var(--text-dim);font-size:0.88em;margin-bottom:12px">
      Obtenida haciendo GET a <code>/devportal/admin/flag</code> con el header
      <code>X-Admin-Token: ADM-2026-N0V3R4-CART3R</code>
    </p>
    <div class="flag-display">{FINAL_FLAG}</div>
    <p style="font-size:0.82em;color:var(--text-dim)">Progreso actual: {n_solved}/{len(CHALLENGES)} retos · {pts}/{TOTAL_POINTS} pts · {pct}%</p>
  </div>

  <div style="margin-top:24px;text-align:center">
    <a href="/help/" class="btn btn-primary">← Volver a los retos</a>
    <a href="/devportal/" class="btn btn-ghost" target="_blank">Abrir DevPortal ↗</a>
  </div>
</div>"""

    return base_page("Flag Final", content, active="final")


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8011))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"""
╔══════════════════════════════════════════════════════╗
║        OSCPT Enum Trainer — Lab 2                    ║
║        Novera Group DevPortal                        ║
╠══════════════════════════════════════════════════════╣
║  🌐 DevPortal:    http://localhost:{port}/devportal/    ║
║  🎓 Retos:        http://localhost:{port}/help/         ║
║  🔍 robots.txt:   http://localhost:{port}/robots.txt    ║
╠══════════════════════════════════════════════════════╣
║  Flag: OSCPBT{{n0v3r4_d3vp0rtal_3num3r4t3d}}        ║
╚══════════════════════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=port, debug=debug)
