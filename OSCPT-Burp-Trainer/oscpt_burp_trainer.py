#!/usr/bin/env python3
"""OSCPT-Burp-Trainer: laboratorio local autocontenido para entrenamiento con Flask y Burp Suite."""
import os, re, sys, sqlite3, secrets
from pathlib import Path
from datetime import datetime, timezone
try:
    from flask import Flask, request, redirect, url_for, session, jsonify, make_response, render_template_string, g, abort
except ImportError:
    print("Falta Flask. Ejecuta esta aplicación a través de Docker Compose; consulta las instrucciones en README.md.")
    sys.exit(1)

HOST, PORT = "0.0.0.0", 8010
DB = Path(os.environ.get("OSCPT_DB_PATH", "/app/data/oscpt_burp_trainer.db"))
FLAG = "OSCPBT{n0v3r4_p30pl3hub_c0mpletad0}"
app = Flask(__name__)
app.secret_key = os.environ.get("OSCPT_SECRET_KEY", secrets.token_hex(32))
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db
@app.teardown_appcontext
def close_db(_):
    c = g.pop("db", None)
    if c: c.close()

def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT,
      email TEXT UNIQUE, username TEXT UNIQUE, password TEXT, role TEXT, department TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS progress(user_id INTEGER, challenge_id INTEGER, completed_at TEXT,
      hints_used INTEGER DEFAULT 0, PRIMARY KEY(user_id,challenge_id), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS hints(user_id INTEGER, challenge_id INTEGER, level INTEGER, used_at TEXT,
      PRIMARY KEY(user_id,challenge_id,level), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY, user_id INTEGER, note TEXT, created_at TEXT,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    """)
    seed = [
      ("Morgan","Reeves","m.reeves@novera.example","m.reeves","Reclutador-Temp-2026!","Reclutador","Recursos Humanos"),
      ("Sarah","Morgan","s.morgan@novera.example","s.morgan","RRHH-Manager-2026!","Responsable de RR. HH.","Recursos Humanos"),
      ("Laura","Vidal","l.vidal@novera.example","l.vidal","N0vera-Soporte-2026!","Agente de soporte","Operaciones IT"),
      ("Alex","Carter","a.carter@novera.example","a.carter","N0vera-Admin-2026!","Administrador","Operaciones IT"),
      ("Jamie","Parker","j.parker@novera.example","j.parker","Finanzas-User-2026!","Empleado","Finanzas"),
      ("Alumno","Laboratorio","alumno@novera.example","alumno","Laboratorio-2026!","Estudiante","Seguridad")]
    for f,l,e,u,p,r,d in seed:
        c.execute("INSERT OR IGNORE INTO users(first_name,last_name,email,username,password,role,department,created_at) VALUES(?,?,?,?,?,?,?,?)",
                  (f,l,e,u,p,r,d,now()))
    c.commit(); c.close()

MODULES = {
    1: "Reconocimiento y Huella Web",
    2: "Enumeración de Autenticación",
    3: "Enumeración del Directorio de Empleados",
    4: "Recopilación de Información y Fugas de Datos",
    5: "Enumeración de People Operations",
    6: "Recursos Internos y Operaciones Administrativas"
}

MODES_INFO = {
    "learning": {
        "id": "learning",
        "name": "Modo Aprendizaje",
        "badge": "Recomendado para iniciarse",
        "color": "#10b981",
        "icon": "🎓",
        "desc": "Pensado para estudiantes que están empezando con Burp Suite o desean una práctica con soporte metodológico.",
        "features": [
            "Guía de metodología con Burp Suite en cada reto (qué herramienta y pestaña usar)",
            "3 niveles de pistas disponibles en cualquier momento",
            "Formato de respuesta con máscara visual (asteriscos ** estilo TryHackMe)",
            "Pistas sin penalización en la puntuación",
            "Enfoque educativo paso a paso"
        ],
        "penalty": "Sin penalización de puntos"
    },
    "guided": {
        "id": "guided",
        "name": "Modo Guiado",
        "badge": "Equilibrado / Estándar",
        "color": "#38bdf8",
        "icon": "🧭",
        "desc": "El formato estándar estilo plataforma CTF. Resuelves de forma autónoma pero dispones de pistas si te atascas.",
        "features": [
            "Enfoque autónomo (tú investigas qué herramienta de Burp Suite utilizar)",
            "Formato de respuesta con máscara visual (asteriscos ** estilo TryHackMe)",
            "3 niveles de pistas desbloqueables bajo demanda",
            "Penalización gradual de puntuación al desbloquear pistas (-10%, -25%, -40%)",
            "Registro de evidencias habilitado"
        ],
        "penalty": "Penalización gradual por uso de pistas"
    },
    "autonomous": {
        "id": "autonomous",
        "name": "Modo Autónomo / Examen",
        "badge": "Simulación OSCP / OSCPT",
        "color": "#f59e0b",
        "icon": "🎯",
        "desc": "Simulación rigurosa de entorno de examen de certificación. Sin ayudas, sin pistas y con máxima exigencia.",
        "features": [
            "Pistas totalmente desactivadas",
            "Sin consejos metodológicos en la tarea",
            "Formato de respuesta con máscara visual (asteriscos ** estilo TryHackMe)",
            "Puntuación íntegra máxima por resolución individual",
            "Evalúa tu soltura real de cara a certificaciones técnicas"
        ],
        "penalty": "Pistas bloqueadas"
    }
}

DESAFÍOS = [
(1,1,"Identificar la aplicación","¿Cómo se llama la aplicación de Recursos Humanos?",["PeopleHub"],35,
 ["Inspecciona la identidad visual de la página principal.","Revisa el título y el encabezado del HTML en la respuesta.","La aplicación se llama PeopleHub."]),
(2,1,"Localizar la ruta de inicio de sesión","¿Qué ruta sirve el formulario de inicio de sesión?",["/login"],25,
 ["Inspecciona el enlace para iniciar sesión.","Revisa el atributo action del formulario HTML.","La ruta es /login."]),
(3,1,"Determinar el método de autenticación","¿Qué método HTTP envía el formulario de inicio de sesión?",["POST"],20,
 ["Intercepta un intento de inicio de sesión en el proxy.","Inspecciona la primera línea de la petición HTTP.","El método utilizado es POST."]),
(4,1,"Encontrar el archivo JavaScript principal","¿Cuál es el nombre del archivo del recurso JavaScript principal?",["app.js"],20,
 ["Inspecciona las referencias a scripts en el HTML o el Site map.","Busca archivos estáticos dentro de /static/js/.","El archivo se llama app.js."]),
(5,2,"Identificar el parámetro del nombre de usuario","¿Qué parámetro del formulario contiene el nombre de usuario?",["username"],25,
 ["Intercepta la petición de inicio de sesión.","Inspecciona el cuerpo (Request body) de la petición.","El parámetro es username."]),
(6,2,"Identificar el parámetro de la contraseña","¿Qué parámetro del formulario contiene la contraseña?",["password"],25,
 ["Compara los campos del formulario con el cuerpo de la petición.","Inspecciona el campo de clave enviado en formato URL-encoded.","El parámetro es password."]),
(7,2,"Analizar las respuestas de autenticación","¿Qué código de estado HTTP se devuelve cuando el usuario existe, pero la contraseña es incorrecta?",["401"],50,
 ["En Burp Repeater, compara un usuario inexistente con uno válido al que le introduces una clave incorrecta.","La aplicación diferencia ambos tipos de error (404 vs otro código).","La cuenta existente con contraseña incorrecta devuelve código 401."]),
(8,2,"Identificar una cuenta interna","¿Qué cuenta de selección de personal aparece referenciada en el recurso de contratación?",["m.reeves"],50,
 ["Inspecciona la página de contratación y su llamada API en segundo plano.","Revisa el objeto recruitment_owner en la respuesta JSON.","El nombre de usuario es m.reeves."]),
(9,3,"Encontrar el directorio de empleados","¿Qué ruta muestra el directorio de empleados?",["/directory"],25,
 ["Inspecciona la navegación una vez iniciada la sesión.","Localiza la página que muestra el listado del personal de la empresa.","La ruta es /directory."]),
(10,3,"Identificar la API de empleados","¿Qué endpoint devuelve la colección de empleados?",["/api/employees"],40,
 ["Carga el directorio con el proxy de Burp activo.","Localiza en HTTP history la petición AJAX que devuelve la lista de empleados.","El endpoint es /api/employees."]),
(11,3,"Determinar el método de consulta","¿Qué método HTTP se utiliza para consultar la colección de empleados?",["GET"],25,
 ["Inspecciona la petición dirigida a la API de empleados en HTTP history.","La petición consulta información sin modificar datos.","El método utilizado es GET."]),
(12,3,"Identificar al empleado de Operaciones IT","¿Qué nombre de usuario corresponde al empleado del departamento de Operaciones IT?",["l.vidal","a.carter"],60,
 ["Revisa el JSON de empleados devuelto por la API en Burp Repeater.","Busca el registro con department 'Operaciones IT'.","El nombre de usuario del agente de soporte es l.vidal."]),
(13,4,"Encontrar el campo de información adicional","¿Qué campo del JSON contiene las notas adicionales del empleado?",["notes"],40,
 ["Compara los datos visibles en la tabla con el JSON sin procesar en Burp.","Busca un campo de texto libre dentro del objeto del empleado.","El campo es notes."]),
(14,4,"Relacionar la cuenta secundaria","¿Qué cuenta está asociada al servicio People Operations?",["l.vidal"],50,
 ["Revisa las notas del empleado y las referencias a servicios secundarios.","Relaciona la cuenta de soporte con el departamento de Operaciones IT.","La cuenta es l.vidal."]),
(15,4,"Recuperar las credenciales del servicio secundario","¿Qué contraseña está documentada para la cuenta del servicio secundario de entrenamiento?",["N0vera-Soporte-2026!","N0vera-Support-2026!"],60,
 ["Sigue la referencia al documento de traspaso (/documents/4) indicada en las notas del empleado.","Inspecciona la respuesta del documento referenciado.","La contraseña de entrenamiento es N0vera-Soporte-2026!."]),
(16,5,"Localizar People Operations","¿Qué ruta sirve la página de inicio de sesión de People Operations?",["/ops/login"],30,
 ["La nota del empleado y el documento de traspaso identifican un servicio secundario.","Sigue la referencia a la ruta del servicio de operaciones.","La ruta es /ops/login."]),
(17,5,"Identificar el rol de la cuenta secundaria","¿Qué rol tiene asignado la cuenta secundaria?",["Agente de soporte"],35,
 ["Autentícate en People Operations con la cuenta l.vidal.","Inspecciona la identidad y cargo que aparece en el panel de soporte.","El rol es Agente de soporte."]),
(18,5,"Encontrar el archivo JavaScript secundario","¿Cómo se llama el archivo JavaScript utilizado por People Operations?",["ops.js"],35,
 ["Inspecciona las referencias a scripts en el panel de soporte.","Busca dentro de /ops/static/.","El archivo se llama ops.js."]),
(19,5,"Localizar el directorio de adjuntos","¿Cómo se llama el directorio que contiene los adjuntos internos?",["attachments"],50,
 ["Revisa el JavaScript secundario (ops.js) y las rutas de almacenamiento de tickets.","Localiza la subcarpeta bajo /ops/files/ donde se guardan los adjuntos.","El directorio se llama attachments."]),
(20,6,"Identificar el documento de traspaso","¿Cuál es el nombre del archivo que contiene el traspaso administrativo?",["admin-handover.txt"],40,
 ["Realiza una petición GET a /ops/files/attachments/ para enumerar el directorio.","Identifica el archivo que contiene el traspaso administrativo.","El archivo se llama admin-handover.txt."]),
(21,6,"Determinar el método de la operación administrativa","¿Qué método HTTP requiere la operación documentada?",["POST"],30,
 ["Lee el formato de petición indicado en admin-handover.txt.","La operación registra un cambio de estado en el servidor.","El método utilizado es POST."]),
(22,6,"Identificar el endpoint administrativo","¿Qué endpoint ejecuta la operación de revisión de cuentas documentada?",["/ops/api/account-review"],40,
 ["Relaciona admin-handover.txt con el código de ops.js.","Localiza la acción account-review.","El endpoint es /ops/api/account-review."]),
(23,6,"Identificar el parámetro objetivo","¿Qué parámetro identifica la cuenta enviada a la operación?",["username"],40,
 ["Inspecciona el cuerpo JSON documentado en el archivo de traspaso.","Localiza el campo que especifica el usuario sobre el que se aplica la revisión.","El parámetro es username."])
]
POINTS = {c[0]: c[5] for c in DESAFÍOS}

BURP_TIPS = {
    1: ("Burp Proxy & HTTP History", "Navega a http://127.0.0.1:8010/ con el navegador integrado de Burp Suite. En <b>Proxy > HTTP history</b>, selecciona la petición <code>GET /</code> y observa en la pestaña <b>Response</b> el título y la marca visual de la aplicación."),
    2: ("Inspección de peticiones y respuestas HTML", "Haz clic en 'Iniciar sesión'. En <b>HTTP history</b> o inspeccionando el código fuente devuelto, busca el atributo <code>action</code> del elemento <code>&lt;form&gt;</code> para determinar la ruta del formulario."),
    3: ("Interceptación activa (Proxy Intercept)", "Activa <b>Proxy > Intercept is on</b> en Burp Suite. Envía cualquier dato en el formulario de inicio de sesión. Burp detendrá la petición antes de salir. Observa el método HTTP en la primera línea (ej. GET, POST, PUT)."),
    4: ("Mapeo del sitio (Target Site map)", "Revisa la pestaña <b>Target > Site map</b> de Burp Suite para <code>http://127.0.0.1:8010</code>. Despliega la carpeta <code>/static/js/</code> o filtra en HTTP history por archivos de tipo Script para localizar el archivo principal."),
    5: ("Análisis de parámetros de cuerpo (Request Body)", "En <b>HTTP history</b>, selecciona la petición de login enviada. En la pestaña <b>Request</b>, examina los parámetros del cuerpo codificados en URL (o consulta la pestaña lateral <b>Params</b>) para ver el nombre del parámetro del usuario."),
    6: ("Inspector de parámetros en Burp Suite", "Observa el panel lateral <b>Inspector</b> en la petición de login capturada. En la sección 'Body Parameters', localiza el nombre exacto del parámetro que transporta la clave."),
    7: ("Burp Repeater & Comparación de respuestas", "Envía la petición de login a <b>Repeater</b> (Ctrl+R / Cmd+R). Envía una prueba con un usuario inexistente (código 404). Luego prueba con un usuario existente y contraseña incorrecta. Fíjate en la diferencia en el código de estado (Status Code)."),
    8: ("Inspección de llamadas a APIs en segundo plano", "Inicia sesión con tu cuenta de empleado y visita <b>Contratación</b> (<code>/recruitment</code>). En HTTP history verás la petición <code>GET /api/candidates</code>. Inspecciona la respuesta JSON y busca el campo <code>recruitment_owner</code>."),
    9: ("Navegación autenticada y Site map", "Una vez autenticado en PeopleHub, haz clic en 'Directorio de empleados'. Observa la ruta que aparece en la barra del navegador o en el mapa de URLs de Burp Target."),
    10: ("Identificación de endpoints REST (AJAX)", "Al abrir el directorio, la página realiza una consulta asíncrona para cargar los empleados. Filtra en HTTP history por tipo JSON o busca peticiones bajo el prefijo <code>/api/</code>."),
    11: ("Verbos HTTP en servicios REST", "Comprueba la columna 'Method' en la tabla de <b>HTTP history</b> correspondiente a la petición que devuelve los empleados."),
    12: ("Búsqueda de cadenas en Burp Repeater", "Envía la petición <code>GET /api/employees</code> a <b>Repeater</b> y pulsa 'Send'. Usa el buscador inferior (Ctrl+F / Cmd+F) para localizar 'Operaciones IT' y anota el <code>username</code> del empleado correspondiente."),
    13: ("Fuga de información (Data Exposure en APIs)", "Compara los datos mostrados en la tabla web con los atributos devueltos en el JSON de la API. Observa qué campo contiene información adicional que la interfaz web no renderiza."),
    14: ("Análisis de referencias cruzadas", "Lee con atención el contenido del campo de notas (<code>notes</code>) del registro del empleado de Operaciones IT. Descubrirás una referencia a un documento interno y una cuenta secundaria."),
    15: ("Petición manual de recursos internos (Repeater)", "En <b>Repeater</b>, clona la petición o edita la ruta para solicitar <code>GET /documents/4</code>. Envía la petición y lee las credenciales del servicio secundario anotadas en el traspaso."),
    16: ("Descubrimiento de portales y accesos secundarios", "Comprueba la ruta del portal de People Operations documentada en el traspaso o referenciada en los comentarios de <code>app.js</code>."),
    17: ("Gestión de identidades y roles", "Inicia sesión en <code>/ops/login</code> con las credenciales de <code>l.vidal</code>. Observa la identidad y el rol mostrado en la cabecera del panel de control de People Operations."),
    18: ("Inspección de scripts secundarios", "En el panel de soporte (<code>/ops/dashboard</code>), examina en HTTP history qué archivo de script se solicita bajo la ruta <code>/ops/static/</code>."),
    19: ("Análisis de código JavaScript en Burp", "Abre el archivo <code>ops.js</code> en el visor de Burp Repeater. Revisa los comentarios de código al final del archivo para ver la ruta del directorio de almacenamiento de archivos adjuntos."),
    20: ("Listado de directorios en APIs (Directory Listing)", "Envía una petición <code>GET /ops/files/attachments/</code> en Repeater asegurándote de incluir tu cookie de sesión de soporte. Observa el array de nombres de archivos devuelto en el JSON."),
    21: ("Interpretación de documentación de APIs internas", "Solicita <code>GET /ops/files/attachments/admin-handover.txt</code> en Burp Repeater. Lee el formato documentado de la petición administrativa y el método HTTP necesario."),
    22: ("Identificación de endpoints administrativos", "Localiza en <code>admin-handover.txt</code> o en las funciones de <code>ops.js</code> la URL del endpoint encargado de la revisión de cuentas."),
    23: ("Construcción manual de peticiones POST JSON (Repeater)", "En Burp Repeater, crea una petición <code>POST /ops/api/account-review</code> con cabecera <code>Content-Type: application/json</code> y cuerpo <code>{\"username\":\"a.carter\"}</code>. Tras recibir confirmación, visita <code>/ops/admin</code> para obtener la flag final.")
}

def get_mask(ans):
    """Devuelve la máscara en formato asteriscos estilo TryHackMe/Hack The Box."""
    return "".join("*" if c.isalnum() else c for c in str(ans))

def user():
    uid = session.get("uid")
    return db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() if uid else None

def get_student_uid():
    """Identificador persistente del estudiante para el laboratorio de retos (no requiere login)."""
    uid = session.get("training_uid")
    if uid:
        row = db().execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone()
        if row: return uid
    row = db().execute("SELECT id FROM users WHERE username='alumno'").fetchone()
    if not row:
        c = db()
        c.execute("INSERT OR IGNORE INTO users(first_name,last_name,email,username,password,role,department,created_at) VALUES ('Alumno','Laboratorio','alumno@novera.example','alumno','Laboratorio-2026!','Estudiante','Seguridad',?)", (now(),))
        c.commit()
        row = c.execute("SELECT id FROM users WHERE username='alumno'").fetchone()
    session["training_uid"] = row["id"]
    return row["id"]

def require(view):
    from functools import wraps
    @wraps(view)
    def inner(*a, **kw):
        if not user(): return redirect("/login")
        return view(*a, **kw)
    return inner

def ops_require(view):
    from functools import wraps
    @wraps(view)
    def inner(*a, **kw):
        if session.get("ops") != "l.vidal":
            if request.path.startswith("/ops/api/"): return jsonify(error="autenticacion_requerida"), 401
            return redirect("/ops/login")
        return view(*a, **kw)
    return inner

def done_ids(uid):
    return {r["challenge_id"] for r in db().execute("SELECT challenge_id FROM progress WHERE user_id=?", (uid,))}

def next_id(uid):
    done = done_ids(uid)
    return next((c[0] for c in DESAFÍOS if c[0] not in done), None)

def score(uid):
    rows = db().execute("SELECT challenge_id, hints_used FROM progress WHERE user_id=?", (uid,)).fetchall()
    total = 0
    for r in rows:
        base = POINTS[r["challenge_id"]]
        total += int(base * [1, 0.9, 0.75, 0.6][min(r["hints_used"], 3)])
    if len(rows) == len(DESAFÍOS): total += 150
    return total

CSS = """<style>
:root{
  --bg:#0b111e;--panel:#111a2e;--panel-hover:#16223b;--line:#22334f;--line-focus:#3b82f6;
  --text:#e6edf8;--muted:#8ea1be;--blue:#38bdf8;--blue-dark:#0284c7;--cyan:#2dd4bf;
  --green:#22c55e;--green-dark:#15803d;--yellow:#f59e0b;--red:#ef4444;--mono:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.top{height:64px;background:#0d1627;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;padding:0 max(calc((100vw - 1180px)/2),22px)}
.brand{font-weight:900;letter-spacing:.12em;font-size:16px;color:#fff}.brand span{color:var(--cyan)}
nav{display:flex;gap:18px;font-size:13px;align-items:center}
main{max-width:1180px;margin:32px auto;padding:0 22px}
.hero,.card{border:1px solid var(--line);border-radius:14px;background:var(--panel);padding:24px}
.hero{background:linear-gradient(135deg,#132238 0%,#0f192b 100%)}
.eyebrow{color:var(--cyan);font-size:11px;letter-spacing:.14em;text-transform:uppercase;font-weight:800;display:flex;align-items:center;gap:6px}
h1{font-size:30px;line-height:1.25;margin:8px 0 12px;font-weight:800}
h2{font-size:20px;margin:12px 0 8px;font-weight:700}
h3{font-size:16px;margin:10px 0 6px;font-weight:700}
.muted{color:var(--muted)}.small{font-size:12px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:18px 0}.two{grid-template-columns:repeat(2,1fr)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;background:var(--blue);color:#071321;padding:10px 18px;border:0;border-radius:8px;font-weight:700;font-size:14px;cursor:pointer;transition:all .15s ease}
.btn:hover{filter:brightness(1.1);text-decoration:none}
.btn.secondary{background:#1f2e47;color:var(--text);border:1px solid var(--line)}
.btn.secondary:hover{background:#273b5c}
.btn.green{background:var(--green);color:#05210f}
.btn.small{padding:6px 12px;font-size:12px}
.btn.disabled{opacity:.4;cursor:not-allowed;pointer-events:none}
input,textarea,select{display:block;width:100%;padding:11px 13px;margin:6px 0 14px;background:#09121f;color:white;border:1px solid var(--line);border-radius:8px;font-size:14px}
input:focus,textarea:focus,select:focus{outline:0;border-color:var(--blue);box-shadow:0 0 0 3px rgba(56,189,248,0.15)}
label{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.form{max-width:520px;margin:auto}
.alert{padding:14px 16px;margin:14px 0;border:1px solid #385674;background:#17283c;border-radius:9px;font-size:14px}
.alert.error{background:#3b1822;border-color:#742a3a;color:#fecdd3}
.alert.success{background:#0e3321;border-color:#1e633d;color:#bbf7d0}
.alert.info{background:#13293f;border-color:#2a507a;color:#bae6fd}
.alert.warning{background:#382b13;border-color:#6e521c;color:#fde68a}
table{width:100%;border-collapse:collapse;margin-top:12px}
td,th{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em}
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;background:#1a283f;color:#b9dcff;font-size:11px;font-weight:700}
.badge.done{background:#133827;color:#86efac;border:1px solid #226442}
.badge.active{background:#1e3a5f;color:#7dd3fc;border:1px solid #38bdf8}
.badge.locked{background:#1a2233;color:#6b7c96}
.bar{height:10px;background:#18253b;border-radius:10px;overflow:hidden;margin:12px 0}
.bar span{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--cyan));border-radius:10px;transition:width .3s ease}
pre,code{font-family:var(--mono)}
pre{white-space:pre-wrap;background:#08101a;padding:14px;border:1px solid var(--line);border-radius:8px;font-size:13px}
footer{text-align:center;color:#6b7c96;padding:40px 20px;font-size:12px;border-top:1px solid #162236;margin-top:50px}

/* TryHackMe / Hack The Box Layout */
.challenge-grid{display:grid;grid-template-columns:1.35fr 1fr;gap:22px;align-items:start;margin-top:20px}
.task-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.thm-panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:22px}
.thm-mask-box{background:#070d17;border:1px dashed #304769;border-radius:8px;padding:12px 14px;margin:12px 0 18px;display:flex;justify-content:space-between;align-items:center}
.thm-mask{font-family:var(--mono);font-size:16px;letter-spacing:3px;color:var(--cyan);font-weight:700}
.thm-input-group{display:flex;gap:10px;margin-top:10px}
.thm-input-group input{margin:0;font-family:var(--mono);font-size:15px;letter-spacing:1px}
.thm-nav{display:flex;justify-content:space-between;gap:12px;margin-top:24px;padding-top:18px;border-top:1px solid var(--line)}
.burp-box{background:#102235;border-left:4px solid var(--blue);border-radius:8px;padding:14px 18px;margin:16px 0}
.hint-card{background:#0c1524;border:1px solid var(--line);border-radius:8px;margin-top:10px;overflow:hidden}
.hint-summary{padding:12px 16px;cursor:pointer;font-weight:700;display:flex;justify-content:space-between;align-items:center;user-select:none;font-size:13px}
.hint-summary:hover{background:#121e33}
.hint-content{padding:14px 16px;border-top:1px solid var(--line);background:#09101c;font-size:14px;color:#cbd5e1}

/* Selector de Modos de Ayuda */
.modes-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:22px 0}
.mode-card{background:var(--panel);border:2px solid var(--line);border-radius:14px;padding:22px;display:flex;flex-direction:column;justify-content:space-between;transition:all .2s ease}
.mode-card:hover{border-color:#334b6e;transform:translateY(-2px)}
.mode-card.selected{border-color:var(--blue);background:linear-gradient(180deg,#15253d 0%,#111c2e 100%);box-shadow:0 0 20px rgba(56,189,248,0.15)}
.mode-card ul{padding-left:18px;margin:14px 0 20px;font-size:13px;color:var(--muted);line-height:1.7}
.mode-card li{margin-bottom:6px}

/* Tareas en el mapa /help */
.task-row{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid var(--line);transition:background .15s ease}
.task-row:last-child{border-bottom:0}
.task-row:hover{background:#142138}
.task-left{display:flex;align-items:center;gap:14px}
.task-num{font-family:var(--mono);font-weight:800;color:var(--muted);font-size:13px}

@media(max-width:880px){
  .challenge-grid,.modes-grid,.grid,.two{grid-template-columns:1fr}
  .top{padding:0 14px}nav{gap:10px;font-size:12px}
}
</style>"""

def render(title, body, training=False):
    u = user()
    if training:
        nav = '<a href="/help">Mapa de Tareas</a><a href="/help/settings">Nivel de Ayuda</a><a href="/help/evidence">Evidencias</a><a href="/" target="_blank">Abrir PeopleHub ↗</a>'
        if u:
            nav += f'<span class="badge" style="margin-left:6px">{u["first_name"]}</span><a href="/logout">Cerrar sesión PeopleHub</a>'
    else:
        nav = '<a href="/">PeopleHub</a><a href="/directory">Directorio</a><a href="/recruitment">Contratación</a><a href="/documents">Documentos</a><a href="/help" style="color:var(--cyan);font-weight:700">★ Laboratorio Burp</a>'
        if u:
            nav += f'<a href="/dashboard">Mi área</a><a href="/logout">Cerrar sesión ({u["first_name"]})</a>'
        else:
            nav += '<a href="/login">Iniciar sesión</a><a href="/register">Crear cuenta</a>'
    return render_template_string(f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>{CSS}</head><body><header class="top"><div class="brand">NOVERA<span>/</span>GROUP <small style="font-size:11px;color:var(--cyan);font-weight:600;letter-spacing:0">BURP LAB</small></div><nav>{nav}</nav></header><main>{body}</main><footer>OSCPT-Burp-Trainer · Entorno de entrenamiento local con Burp Suite · Solo prácticas autorizadas</footer></body></html>""")

@app.route("/")
def index():
    return render("PeopleHub", '<section class="hero"><div class="eyebrow">Novera Group · Personas y Cultura</div><h1>PeopleHub</h1><p class="muted">Tu entorno de trabajo conectado. Accede a los servicios para empleados, información de contratación y recursos de la empresa.</p><a class="btn" href="/login">Iniciar sesión</a> <a class="btn secondary" href="/register">Crear cuenta</a> <a class="btn secondary" href="/help">Ir a la plataforma de retos →</a></section><div class="grid"><div class="card"><h2>Servicios para empleados</h2><p class="muted">Accede a tu perfil y al directorio de la empresa.</p></div><div class="card"><h2>Contratación</h2><p class="muted">Consulta la actividad de selección de personal.</p></div><div class="card"><h2>Recursos</h2><p class="muted">Encuentra políticas corporativas y soporte.</p></div></div>')

@app.route("/register", methods=["GET","POST"])
def register():
    err = ""
    if request.method == "POST":
        f = request.form.get("first_name","").strip(); l = request.form.get("last_name","").strip()
        e = request.form.get("email","").strip().lower(); u = request.form.get("username","").strip().lower(); p = request.form.get("password","")
        if not all([f,l,e,u,p]): err = "Todos los campos son obligatorios."
        elif not re.fullmatch(r"[a-z0-9._-]{3,32}", u): err = "El nombre de usuario debe tener entre 3 y 32 caracteres válidos."
        elif len(p) < 8: err = "La contraseña debe contener al menos 8 caracteres."
        else:
            try:
                db().execute("INSERT INTO users(first_name,last_name,email,username,password,role,department,created_at) VALUES(?,?,?,?,?,'Empleado','General',?)",(f,l,e,u,p,now())); db().commit()
                return redirect("/login")
            except sqlite3.IntegrityError: err = "El correo electrónico o el nombre de usuario ya están registrados."
    body = f'<div class="card form"><div class="eyebrow">Nueva cuenta de empleado</div><h1>Crea tu cuenta</h1>{("<div class=\"alert error\">"+err+"</div>") if err else ""}<form method="post"><label>Nombre</label><input name="first_name" required><label>Apellidos</label><input name="last_name" required><label>Correo electrónico</label><input type="email" name="email" required><label>Nombre de usuario</label><input name="username" required><label>Contraseña</label><input type="password" name="password" required><button class="btn">Crear cuenta</button></form><p class="small">¿Ya tienes una cuenta? <a href="/login">Iniciar sesión</a></p></div>'
    return render("Registro | PeopleHub", body)

@app.route("/login", methods=["GET","POST"])
def login():
    err = ""; status = 200
    if request.method == "POST":
        u = request.form.get("username","").strip().lower(); p = request.form.get("password","")
        row = db().execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        # Comportamiento intencional de enumeración de usuarios para este laboratorio controlado.
        if not row: err = "No se ha encontrado la cuenta."; status = 404
        elif row["password"] != p: err = "La contraseña es incorrecta."; status = 401
        else:
            session["uid"] = row["id"]
            if "mode" not in session: session["mode"] = "guided"
            return redirect("/dashboard")
    body = f'<div class="card form"><div class="eyebrow">Autenticación de PeopleHub</div><h1>Iniciar sesión</h1>{("<div class=\"alert error\">"+err+"</div>") if err else ""}<form method="post"><label>Nombre de usuario</label><input name="username" required><label>Contraseña</label><input type="password" name="password" required><button class="btn">Iniciar sesión</button></form><p class="small">¿No tienes una cuenta? <a href="/register">Crear una cuenta</a></p></div>'
    return render("Iniciar sesión | PeopleHub", body), status

@app.route("/logout")
def logout():
    session.pop("uid", None)
    session.pop("ops", None)
    session.pop("admin_review", None)
    return redirect("/")

@app.route("/dashboard")
@require
def dashboard():
    u = user()
    body = f'<section class="hero"><div class="eyebrow">Área de empleado</div><h1>Te damos la bienvenida, {u["first_name"]}</h1><p class="muted">{u["role"]} · {u["department"]}</p></section><div class="grid"><a class="card" href="/profile"><h2>Mi perfil →</h2></a><a class="card" href="/directory"><h2>Directorio de empleados →</h2></a><a class="card" href="/recruitment"><h2>Contratación →</h2></a><a class="card" href="/documents"><h2>Documentos de la empresa →</h2></a><a class="card" href="/support"><h2>Soporte interno →</h2></a><a class="card" href="/help"><h2>Objetivos de formación con Burp →</h2></a></div>'
    return render("Panel | PeopleHub", body)

@app.route("/profile")
@require
def profile():
    u = user()
    return render("Perfil", f'<div class="card"><h1>Mi perfil</h1><p>{u["first_name"]} {u["last_name"]} · {u["email"]} · {u["username"]}</p><p>{u["role"]} / {u["department"]}</p></div>')

EMPLOYEES = [
{"id":101,"name":"Morgan Reeves","username":"m.reeves","email":"m.reeves@novera.example","department":"Recursos Humanos","role":"Reclutador","notes":"Responsable de contratación. Coordina los registros de candidatos."},
{"id":102,"name":"Sarah Morgan","username":"s.morgan","email":"s.morgan@novera.example","department":"Recursos Humanos","role":"Responsable de RR. HH.","notes":"Aprueba los flujos de trabajo de RR. HH. y el acceso a contratación."},
{"id":103,"name":"Laura Vidal","username":"l.vidal","email":"l.vidal@novera.example","department":"Operaciones IT","role":"Agente de soporte","notes":"Cuenta de soporte de People Operations. Ver traspaso de soporte: /documents/4."},
{"id":104,"name":"Alex Carter","username":"a.carter","email":"a.carter@novera.example","department":"Operaciones IT","role":"Administrador","notes":"Administrador de la plataforma. Solo operaciones internas."},
{"id":105,"name":"Jamie Parker","username":"j.parker","email":"j.parker@novera.example","department":"Finanzas","role":"Empleado","notes":"Empleado de operaciones financieras."}
]

@app.route("/directory")
@require
def directory():
    return render("Directorio", '<div class="eyebrow">Personas y Cultura</div><h1>Directorio de empleados</h1><div class="card"><table><tbody id="rows"><tr><td>Cargando...</td></tr></tbody></table></div><script src="/static/js/app.js"></script>')

@app.route("/api/employees")
@require
def employees(): return jsonify(status="success", count=len(EMPLOYEES), employees=EMPLOYEES)

@app.route("/api/employees/<int:eid>")
@require
def employee(eid):
    item = next((x for x in EMPLOYEES if x["id"] == eid), None)
    return (jsonify(status="success", employee=item), 200) if item else (jsonify(error="employee_not_found"), 404)

@app.route("/recruitment")
@require
def recruitment():
    return render("Contratación", '<div class="card"><h1>Contratación</h1><p>Para consultas sobre los procesos de contratación, contacta con la persona responsable de selección.</p><div id="info">Cargando...</div></div><script>fetch("/api/candidates").then(r=>r.json()).then(d=>document.getElementById("info").textContent="Responsable de contratación: "+d.recruitment_owner.username)</script>')

@app.route("/api/candidates")
@require
def candidates():
    return jsonify(status="success", open_roles=4, recruitment_owner={"name":"Morgan Reeves","username":"m.reeves","email":"m.reeves@novera.example"}, candidates=[{"candidate_id":"C-2041","position":"Analista de sistemas","status":"Entrevista"},{"candidate_id":"C-2042","position":"Ingeniero de seguridad","status":"Revisión"}])

@app.route("/api/candidates/<cid>")
@require
def candidate(cid):
    data = {"C-2041":{"candidate_id":"C-2041","position":"Analista de sistemas","status":"Entrevista"},"C-2042":{"candidate_id":"C-2042","position":"Ingeniero de seguridad","status":"Revisión"}}
    return (jsonify(status="success", candidate=data[cid]), 200) if cid in data else (jsonify(error="candidate_not_found"), 404)

@app.route("/documents")
@require
def documents():
    return render("Documentos", '<div class="card"><h1>Documentos de la empresa</h1><p><a href="/documents/1">Manual del empleado</a></p><p><a href="/documents/2">Uso aceptable de TI</a></p><p><a href="/documents/3">Política de trabajo remoto</a></p></div>')

@app.route("/documents/<int:did>")
@require
def document(did):
    docs = {
        1: ("Manual del empleado", "Te damos la bienvenida a Novera Group. Sigue las políticas de la empresa y comunica las incidencias por los canales establecidos."),
        2: ("Uso aceptable de TI", "Los sistemas de la empresa se proporcionan para uso profesional autorizado."),
        3: ("Política de trabajo remoto", "El trabajo en remoto requiere la aprobación de un responsable."),
        4: ("Traspaso de soporte", "Servicio People Operations: /ops/login\\nCuenta de soporte: l.vidal\\nContraseña de entrenamiento: N0vera-Soporte-2026!\\nUtiliza el servicio secundario para administrar los tickets.")
    }
    if did not in docs: return "No encontrado", 404
    title, text = docs[did]
    return make_response(f"<html><body><h1>{title}</h1><pre>{text}</pre></body></html>", 200, {"Content-Type":"text/html; charset=utf-8"})

@app.route("/support")
@require
def support(): return render("Soporte", '<div class="card"><h1>Soporte interno</h1><p>El espacio de trabajo de People Operations está disponible para el personal de soporte.</p></div>')

@app.route("/static/js/app.js")
def app_js():
    js = """document.addEventListener('DOMContentLoaded',async()=>{let e=document.getElementById('rows');if(!e)return;let d=await(await fetch('/api/employees')).json();e.innerHTML='<tr><th>Nombre</th><th>Departamento</th><th>Cargo</th></tr>'+d.employees.map(x=>`<tr><td>${x.name}</td><td>${x.department}</td><td>${x.role}</td></tr>`).join('')});\n/* Compilación frontend de PeopleHub 2.6.4. Integración de soporte: /ops/login */"""
    return make_response(js, 200, {"Content-Type":"application/javascript"})

@app.route("/ops/login", methods=["GET","POST"])
def ops_login():
    err = ""; status = 200
    if request.method == "POST":
        u = request.form.get("username","").lower().strip(); p = request.form.get("password","")
        if u != "l.vidal": err = "No se ha encontrado la cuenta."; status = 404
        elif p not in ("N0vera-Soporte-2026!", "N0vera-Support-2026!"): err = "La contraseña es incorrecta."; status = 401
        else: session["ops"] = "l.vidal"; return redirect("/ops/dashboard")
    b = f'<div class="card form"><div class="eyebrow">Operaciones IT</div><h1>People Operations</h1>{("<div class=\"alert error\">"+err+"</div>") if err else ""}<form method="post"><label>Nombre de usuario</label><input name="username"><label>Contraseña</label><input type="password" name="password"><button class="btn">Iniciar sesión</button></form></div>'
    return render("Acceso a People Operations", b), status

@app.route("/ops/dashboard")
@ops_require
def ops_dashboard():
    return render("People Operations", '<section class="hero"><h1>People Operations</h1><p>Laura Vidal · Agente de soporte</p></section><div class="grid"><a class="card" href="/ops/tickets">Tickets de soporte</a><a class="card" href="/ops/files/attachments/">Adjuntos</a></div><script src="/ops/static/ops.js"></script>')

@app.route("/ops/tickets")
@ops_require
def ops_tickets():
    return render("Tickets", '<div class="card"><h1>Tickets de soporte</h1><p>INC-8831 · Acceso a cuenta de PeopleHub · Abierto</p><p>INC-8834 · Revisión trimestral de accesos · Pendiente</p></div>')

@app.route("/ops/static/ops.js")
def ops_js():
    js = """const OPS_API='/ops/api'; async function submitAccountReview(username){return fetch(OPS_API+'/account-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});}\n// Almacenamiento de adjuntos de tickets: /ops/files/attachments/"""
    return make_response(js, 200, {"Content-Type":"application/javascript"})

@app.route("/ops/files/<directory>/")
@ops_require
def file_listing(directory):
    if directory != "attachments": return jsonify(error="directory_not_found"), 404
    return jsonify(directory="attachments", files=["ticket-8831.txt", "admin-handover.txt"], count=2)

@app.route("/ops/files/<directory>/<path:filename>")
@ops_require
def file_download(directory, filename):
    files = {
        "ticket-8831.txt": "Ticket INC-8831: El usuario informa de problemas para acceder a PeopleHub.",
        "admin-handover.txt": 'NOVERA GROUP - TRASPASO ADMINISTRATIVO INTERNO\\nPOST /ops/api/account-review\\nContent-Type: application/json\\nBody: {"username":"a.carter"}\\nLa operación registra una solicitud de revisión para la cuenta indicada.'
    }
    if directory != "attachments" or filename not in files: return jsonify(error="file_not_found"), 404
    return make_response(files[filename], 200, {"Content-Type":"text/plain; charset=utf-8"})

@app.route("/ops/api/account-review", methods=["POST"])
@ops_require
def account_review():
    data = request.get_json(silent=True) or {}
    target = str(data.get("username", "")).strip().lower()
    if not target: return jsonify(error="username_required"), 400
    if target == "a.carter": session["admin_review"] = True
    return jsonify(status="review_recorded", username=target, message="La revisión de la cuenta administrativa se ha completado.", next="/ops/admin" if target == "a.carter" else None)

@app.route("/ops/admin")
@ops_require
def ops_admin():
    if not session.get("admin_review"): return jsonify(error="account_review_required"), 403
    return jsonify(status="success", area="Área administrativa de Novera Group", flag=FLAG)

# =========================================================================
# PLATAFORMA DE ENTRENAMIENTO ESTILO HACK THE BOX / TRYHACKME
# =========================================================================

@app.route("/help")
def help_home():
    uid = get_student_uid()
    done = done_ids(uid)
    nxt = next_id(uid)
    pct = int(len(done) / len(DESAFÍOS) * 100)
    current_mode = session.get("mode", "guided")
    mode_obj = MODES_INFO.get(current_mode, MODES_INFO["guided"])
    u = user()
    student_label = f"Estudiante ({u['first_name']})" if u else "Estudiante (Acceso directo sin login)"

    # Generación de módulos y tareas secuenciales
    modules_html = ""
    for mid, mname in MODULES.items():
        items = [c for c in DESAFÍOS if c[1] == mid]
        tasks_html = ""
        for c in items:
            cid = c[0]
            isdone = cid in done
            isnext = cid == nxt
            openable = isdone or isnext

            if isdone:
                badge = '<span class="badge done">✓ Completada</span>'
                link = f'<a href="/help/challenge/{cid}"><strong>Q{cid:02} · {c[2]}</strong></a>'
            elif isnext:
                badge = '<span class="badge active">► En curso</span>'
                link = f'<a href="/help/challenge/{cid}" style="color:var(--cyan)"><strong>Q{cid:02} · {c[2]}</strong></a>'
            else:
                badge = '<span class="badge locked">🔒 Bloqueada</span>'
                link = f'<span class="muted">Q{cid:02} · {c[2]}</span>'

            btn_action = f'<a href="/help/challenge/{cid}" class="btn small {"green" if isdone else ("" if isnext else "secondary disabled")}">' + ("Repasar" if isdone else ("Comenzar" if isnext else "Bloqueado")) + '</a>'

            tasks_html += f"""
            <div class="task-row">
              <div class="task-left">
                <span class="task-num">Q{cid:02}</span>
                <div>{link}<div class="small muted">{c[3]}</div></div>
              </div>
              <div style="display:flex;align-items:center;gap:14px">
                {badge}
                <span class="small muted">{c[5]} pts</span>
                {btn_action}
              </div>
            </div>"""

        modules_html += f"""
        <div class="card" style="margin-top:20px;padding:0;overflow:hidden">
          <div style="padding:16px 20px;background:#0d1829;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center">
            <div>
              <div class="eyebrow">MÓDULO {mid:02}</div>
              <h2 style="margin:2px 0 0;font-size:18px">{mname}</h2>
            </div>
            <span class="badge">{sum(1 for c in items if c[0] in done)}/{len(items)} Tareas</span>
          </div>
          <div>{tasks_html}</div>
        </div>"""

    has_flag = session.get("final_done", False)
    if has_flag:
        fin = '<a class="btn green" href="/help/final">✓ Flag Capturada (Ver resultado)</a>'
    else:
        fin = '<a class="btn green" href="/help/final">🏆 Enviar Flag de Administrador →</a>'

    instructions_html = """
    <div class="card" style="margin-top:20px;border-left:4px solid var(--cyan)">
      <div class="eyebrow" style="color:var(--cyan)">📖 INSTRUCCIONES DEL LABORATORIO</div>
      <h2 style="margin:4px 0 10px">¿Cómo empezar y resolver las tareas?</h2>
      <div class="grid two" style="margin:12px 0;gap:16px">
        <div style="background:#09121f;padding:16px;border-radius:10px;border:1px solid var(--line)">
          <h3 style="margin-top:0;color:var(--blue)">1. Interceptar el tráfico con Burp Suite</h3>
          <p class="muted small" style="margin:0">
            Abre Burp Suite y arranca el <strong>navegador integrado</strong> (<i>Proxy &gt; Open browser</i>).<br>
            La aplicación web que debes auditar es <strong>PeopleHub</strong>: <a href="http://127.0.0.1:8010/" target="_blank" style="color:var(--cyan);font-weight:700">http://127.0.0.1:8010/ ↗</a>.
          </p>
        </div>
        <div style="background:#09121f;padding:16px;border-radius:10px;border:1px solid var(--line)">
          <h3 style="margin-top:0;color:var(--green)">2. Avance secuencial por objetivos</h3>
          <p class="muted small" style="margin:0">
            Empieza por la tarea <strong>Q01</strong>. Cada tarea te pide una evidencia que debes obtener con Burp Suite (métodos HTTP, parámetros, endpoints de API o credenciales ocultas).<br>
            Introduce la respuesta guiándote por la máscara de asteriscos <code>**</code>. Al acertar, se desbloquea automáticamente la siguiente tarea.
          </p>
        </div>
      </div>
      <div style="background:#09121f;padding:12px 16px;border-radius:8px;font-size:13px;color:var(--muted);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <span>💡 <strong>Consejo metodológico:</strong> Puedes activar el <strong>Modo Aprendizaje</strong> para ver consejos paso a paso sobre qué herramientas de Burp utilizar en cada reto.</span>
        <a href="/help/settings" class="btn secondary small">Configurar Nivel de Ayuda</a>
      </div>
    </div>
    """

    body = f"""
    <section class="hero">
      <div class="eyebrow">Plataforma de Entrenamiento · Novera Group</div>
      <h1>Sala: PeopleHub Pentesting con Burp Suite</h1>
      <p class="muted">Bienvenido/a, <strong>{student_label}</strong>. Investiga el portal PeopleHub a través de Burp Suite, responde a las preguntas secuenciales y registra tus evidencias.</p>
      
      <!-- Banner de Nivel de Ayuda Actual -->
      <div style="background:#091424;border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:18px 0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
        <div style="display:flex;align-items:center;gap:12px">
          <span style="font-size:26px">{mode_obj["icon"]}</span>
          <div>
            <div style="font-size:14px;font-weight:700">Nivel de ayuda: <span style="color:{mode_obj['color']}">{mode_obj["name"]}</span> <span class="badge">{mode_obj["badge"]}</span></div>
            <div class="small muted">{mode_obj["desc"]}</div>
          </div>
        </div>
        <a href="/help/settings" class="btn secondary small">⚙️ Cambiar nivel de ayuda</a>
      </div>

      <div class="grid">
        <div><div class="small muted">PROGRESO GENERAL</div><h2>{pct}%</h2></div>
        <div><div class="small muted">TAREAS COMPLETADAS</div><h2>{len(done)} / {len(DESAFÍOS)}</h2></div>
        <div><div class="small muted">PUNTUACIÓN OBTENIDA</div><h2 style="color:var(--cyan)">{score(uid)} pts</h2></div>
      </div>
      <div class="bar"><span style="width:{pct}%"></span></div>
    </section>

    {instructions_html}

    {modules_html}

    <div class="card" style="margin-top:24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;border-left:4px solid var(--yellow)">
      <div>
        <div class="eyebrow" style="color:var(--yellow)">OBJETIVO FINAL · ACCESO DIRECTO PERMANENTE</div>
        <h2>Flag de Administrador (People Operations)</h2>
        <p class="muted small">¿Has conseguido extraer la flag de <code>/ops/admin</code> directamente o por otra vía? Puedes validarla aquí en cualquier momento sin necesidad de haber completado los pasos previos.</p>
      </div>
      <div>{fin}</div>
    </div>
    
    <div style="text-align:right;margin-top:16px">
      <form method="post" action="/help/reset" onsubmit="return confirm('¿Seguro que deseas reiniciar tu progreso? Se borrarán tus respuestas y evidencias.');" style="display:inline">
        <button class="btn secondary small" style="color:var(--red)">Reiniciar mi progreso</button>
      </form>
    </div>
    """
    return render("Plataforma de Retos | OSCPT-Burp-Trainer", body, True)

@app.route("/help/settings", methods=["GET","POST"])
def settings():
    msg = ""
    if request.method == "POST":
        m = request.form.get("mode", "guided")
        if m in MODES_INFO:
            session["mode"] = m
            msg = f"Nivel de ayuda actualizado a <strong>{MODES_INFO[m]['name']}</strong>."
    
    current_mode = session.get("mode", "guided")
    
    cards_html = ""
    for mid, info in MODES_INFO.items():
        is_sel = (mid == current_mode)
        features_list = "".join(f"<li>{feat}</li>" for feat in info["features"])
        btn = f'<span class="badge done" style="width:100%;justify-content:center;padding:8px">✓ Nivel Activo</span>' if is_sel else f'<form method="post" style="margin:0"><input type="hidden" name="mode" value="{mid}"><button class="btn secondary" style="width:100%">Seleccionar este modo</button></form>'
        
        cards_html += f"""
        <div class="mode-card {"selected" if is_sel else ""}">
          <div>
            <div style="display:flex;justify-content:space-between;align-items:start">
              <span style="font-size:32px">{info["icon"]}</span>
              <span class="badge" style="background:{info['color']}22;color:{info['color']};border:1px solid {info['color']}44">{info["badge"]}</span>
            </div>
            <h2 style="margin:12px 0 6px">{info["name"]}</h2>
            <p class="muted small" style="min-height:48px">{info["desc"]}</p>
            <div style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-top:14px">Qué incluye:</div>
            <ul>{features_list}</ul>
          </div>
          <div>
            <div class="small muted" style="margin-bottom:12px;border-top:1px solid var(--line);padding-top:10px">
              <b>Penalización:</b> {info["penalty"]}
            </div>
            {btn}
          </div>
        </div>"""

    body = f"""
    <p><a href="/help">← Volver al mapa de tareas</a></p>
    <section class="hero">
      <div class="eyebrow">Configuración Pedagógica</div>
      <h1>Nivel de Ayuda del Laboratorio</h1>
      <p class="muted">Elige el tipo de experiencia que prefieres para practicar con Burp Suite. Puedes cambiar de nivel en cualquier momento sin perder tu progreso ni tus evidencias acumuladas.</p>
      {("<div class=\"alert success\">"+msg+"</div>") if msg else ""}
    </section>

    <div class="modes-grid">{cards_html}</div>

    <div class="card" style="margin-top:20px">
      <h3>¿Cuál es el modo recomendado para mí?</h3>
      <p class="muted small">
        • Si es tu primera vez usando Burp Suite (Proxy, Repeater, Target) te recomendamos empezar con el <strong>Modo Aprendizaje</strong>.<br>
        • Si ya conoces los fundamentos de Burp y quieres resolver retos a tu ritmo con opción a pistas si te bloqueas, usa el <strong>Modo Guiado</strong>.<br>
        • Si te estás preparando para certificaciones como <strong>OSCP, OSCPT, eWPT</strong> y quieres una simulación real de examen, activa el <strong>Modo Autónomo</strong>.
      </p>
    </div>
    """
    return render("Nivel de Ayuda | OSCPT-Burp-Trainer", body, True)

@app.route("/help/challenge/<int:cid>", methods=["GET","POST"])
def challenge(cid):
    c = next((x for x in DESAFÍOS if x[0] == cid), None)
    if not c: abort(404)
    uid = get_student_uid()
    done = done_ids(uid)
    nxt = next_id(uid)
    
    # Restricción secuencial: solo se accede si está completado o es el siguiente
    if cid not in done and cid != nxt:
        return redirect("/help")

    message = ""; kind = ""
    if request.method == "POST":
        ans = request.form.get("answer", "").strip().strip("`").lower()
        if ans in [x.lower() for x in c[4]]:
            if cid not in done:
                nh = db().execute("SELECT COUNT(*) n FROM hints WHERE user_id=? AND challenge_id=?", (uid, cid)).fetchone()["n"]
                db().execute("INSERT OR IGNORE INTO progress VALUES(?,?,?,?)", (uid, cid, now(), nh))
                db().commit()
                done.add(cid)
            message = "¡Respuesta correcta! Tarea completada con éxito."
            kind = "success"
        else:
            message = "Respuesta incorrecta. Revisa el tráfico interceptado en Burp e inténtalo de nuevo."
            kind = "error"

    is_completed = cid in done
    used_hints = {r["level"] for r in db().execute("SELECT level FROM hints WHERE user_id=? AND challenge_id=?", (uid, cid))}
    mode = session.get("mode", "guided")
    
    # Máscara visual estilo TryHackMe
    canonical_answer = c[4][0]
    mask_str = get_mask(canonical_answer)
    
    # Burp Suite Methodology Tip
    tip_info = BURP_TIPS.get(cid, ("Burp Suite Proxy & Repeater", "Usa Burp Proxy para interceptar el tráfico y Burp Repeater para enviar peticiones manipuladas."))
    burp_tip_html = ""
    if mode == "learning":
        burp_tip_html = f"""
        <div class="burp-box">
          <div class="eyebrow" style="color:var(--blue);margin-bottom:4px">🛠️ GUÍA BURP SUITE · {tip_info[0]}</div>
          <p style="margin:0;font-size:14px;color:#dbeafe">{tip_info[1]}</p>
        </div>"""

    # Bloque de Pistas
    hints_html = ""
    if mode == "autonomous":
        hints_html = '<div class="alert warning" style="margin-top:14px">🔒 <b>Pistas bloqueadas:</b> En Modo Autónomo / Examen las pistas están desactivadas para simular una prueba real.</div>'
    else:
        hint_cards = ""
        penalty_labels = ["-10% pts", "-25% pts", "-40% pts"]
        for level, h in enumerate(c[6], 1):
            is_revealed = level in used_hints
            if is_revealed:
                hint_cards += f"""
                <details class="hint-card" open>
                  <summary class="hint-summary" style="color:var(--cyan)"><span>💡 Pista {level} (Desbloqueada)</span> <span>✓</span></summary>
                  <div class="hint-content">{h}</div>
                </details>"""
            else:
                cost_text = f" ({penalty_labels[level-1]})" if mode == "guided" else " (sin penalización)"
                hint_cards += f"""
                <div class="hint-card" style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center">
                  <span class="small muted">💡 Pista {level}{cost_text}</span>
                  <form method="post" action="/help/hint/{cid}/{level}" style="margin:0">
                    <button class="btn secondary small">Desbloquear Pista {level}</button>
                  </form>
                </div>"""
        hints_html = f'<div style="margin-top:18px"><div class="eyebrow" style="margin-bottom:8px">SISTEMA DE PISTAS ({len(used_hints)}/3 USADAS)</div>{hint_cards}</div>'

    # Navegación entre retos
    prev_link = f'<a href="/help/challenge/{cid-1}" class="btn secondary small">← Q{cid-1:02} Anterior</a>' if cid > 1 else '<span class="btn secondary small disabled">← Anterior</span>'
    next_unlocked = (cid in done) or ((cid + 1) in done)
    if cid < len(DESAFÍOS):
        next_link = f'<a href="/help/challenge/{cid+1}" class="btn {"green" if is_completed else "secondary"} small">Q{cid+1:02} Siguiente →</a>' if next_unlocked else '<span class="btn secondary small disabled">🔒 Q' + f'{cid+1:02} Bloqueada</span>'
    else:
        next_link = '<a href="/help/final" class="btn green small">🏆 Objetivo Final →</a>' if len(done) == len(DESAFÍOS) else '<span class="btn secondary small disabled">🔒 Objetivo Final</span>'

    # Feedback de respuesta correcta / formulario
    status_badge = '<span class="badge done">✓ Tarea Completada</span>' if is_completed else '<span class="badge active">► En curso</span>'
    
    body = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
      <p style="margin:0"><a href="/help">← Mapa de Tareas</a> · <span class="badge">Módulo {c[1]:02} · {MODULES[c[1]]}</span></p>
      <div>{status_badge} <span class="badge">{c[5]} puntos</span></div>
    </div>

    <div class="challenge-grid">
      <!-- Columna Izquierda: Enunciado, Consejos de Burp y Pistas -->
      <div>
        <div class="thm-panel">
          <div class="task-header">
            <div class="eyebrow">TAREA Q{cid:02}</div>
            <span class="small muted">Dificultad: Guiada</span>
          </div>
          <h1 style="font-size:24px;margin:6px 0 14px">{c[2]}</h1>
          <div style="font-size:16px;font-weight:600;color:#fff;background:#0d1829;border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:12px 0">
            {c[3]}
          </div>

          {burp_tip_html}
          {hints_html}
        </div>
      </div>

      <!-- Columna Derecha: Formulario de Respuesta con Máscara Estilo TryHackMe -->
      <div>
        <div class="thm-panel" style="position:sticky;top:20px">
          <div class="eyebrow" style="margin-bottom:8px">ENVÍO DE RESPUESTA</div>
          <h3 style="margin-top:0">Introduce la evidencia encontrada</h3>
          <p class="muted small">Investiga con Burp Suite e introduce la respuesta exacta solicitada.</p>

          <!-- Máscara de longitud y caracteres con formato THM -->
          <div class="thm-mask-box">
            <div>
              <div class="small muted" style="font-size:11px;text-transform:uppercase;letter-spacing:.05em">Formato de respuesta:</div>
              <div class="thm-mask">{mask_str}</div>
            </div>
            <span class="badge" title="Cantidad de caracteres">{len(canonical_answer)} caracteres</span>
          </div>

          {("<div class=\"alert "+kind+"\">"+message+"</div>") if message else ""}
          {("<div class=\"alert success\">✓ ¡Has completado esta tarea! Puedes continuar con la siguiente.</div>") if is_completed and not message else ""}

          <form method="post" style="margin-top:14px">
            <label>Tu respuesta</label>
            <div class="thm-input-group">
              <input name="answer" placeholder="{mask_str}" required autocomplete="off" autofocus>
              <button class="btn green" style="white-space:nowrap">Enviar</button>
            </div>
          </form>

          <div style="margin-top:20px;border-top:1px solid var(--line);padding-top:14px;display:flex;justify-content:space-between;align-items:center">
            <span class="small muted"><a href="/help/evidence">📝 Abrir registro de evidencias</a></span>
            <span class="small muted"><a href="/help/settings">Modo: {MODES_INFO.get(mode,{}).get('name','')}</a></span>
          </div>

          <div class="thm-nav">
            {prev_link}
            {next_link}
          </div>
        </div>
      </div>
    </div>
    """
    return render(f"Q{cid:02} · {c[2]} | Retos Burp", body, True)

@app.route("/help/hint/<int:cid>/<int:level>", methods=["POST"])
def hint(cid, level):
    if level not in (1, 2, 3): abort(404)
    uid = get_student_uid()
    if session.get("mode", "guided") != "autonomous":
        db().execute("INSERT OR IGNORE INTO hints VALUES(?,?,?,?)", (uid, cid, level, now()))
        db().commit()
    return redirect(f"/help/challenge/{cid}")

@app.route("/help/evidence", methods=["GET","POST"])
def evidence():
    uid = get_student_uid()
    if request.method == "POST":
        note = request.form.get("note", "").strip()[:2000]
        if note:
            db().execute("INSERT INTO evidence(user_id,note,created_at) VALUES(?,?,?)", (uid, note, now()))
            db().commit()
        return redirect("/help/evidence")
    rows = db().execute("SELECT note,created_at FROM evidence WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    notes = "".join(f'<div class="alert" style="margin-bottom:12px"><small class="muted">{r["created_at"]}</small><br><div style="margin-top:6px">{r["note"]}</div></div>' for r in rows) or '<p class="muted">Todavía no has registrado ninguna observación.</p>'
    return render("Registro de Evidencias | Laboratorio Burp", f'<p><a href="/help">← Volver al mapa de tareas</a></p><div class="card"><h1>Registro de evidencias del alumno</h1><p class="muted">Anota parámetros descubiertos, credenciales, cookies o notas de pentesting para consultarlas durante las tareas.</p><form method="post"><label>Nueva observación</label><textarea name="note" rows="4" placeholder="Ej: Descubierto parámetro username en /login, devuelve 401 si la cuenta existe..." required></textarea><button class="btn">Guardar en mi registro</button></form></div><div class="card" style="margin-top:20px"><h2>Historial de notas guardadas</h2>{notes}</div>', True)

@app.route("/help/reset", methods=["POST"])
def reset():
    uid = get_student_uid()
    for table in ("progress", "hints", "evidence"):
        db().execute(f"DELETE FROM {table} WHERE user_id=?", (uid,))
    db().commit()
    session.pop("final_done", None)
    return redirect("/help")

@app.route("/help/final", methods=["GET","POST"])
def final():
    uid = get_student_uid()
    done = done_ids(uid)
    all_done = len(done) == len(DESAFÍOS)
    msg = ""
    if request.method == "POST":
        flag_val = request.form.get("flag", "").strip()
        if flag_val in (FLAG, "OSCPBT{n0v3r4_p30pl3hub_c0mpl3t3d}"):
            session["final_done"] = True
            if all_done:
                msg = "¡Enhorabuena! Bandera correcta. Has completado el 100% de las 23 tareas y la evaluación final del laboratorio."
            else:
                msg = f"¡Enhorabuena! Flag de Administrador aceptada ({len(done)}/23 tareas previas resueltas). Has conseguido comprometer la cuenta administrativa y obtener la flag directamente."
        else:
            msg = "Bandera incorrecta. Asegúrate de haber completado la revisión de cuenta en /ops/api/account-review y acceder a /ops/admin."
    
    is_done = session.get("final_done", False)

    return render("Flag de Administrador | OSCPT-Burp-Trainer", f"""
    <p><a href="/help">← Volver al mapa de tareas</a></p>
    <div class="card form" style="max-width:680px">
      <div class="eyebrow" style="color:var(--yellow)">🏆 OBJETIVO PRINCIPAL: ÁREA ADMINISTRATIVA</div>
      <h1 style="margin:8px 0 12px">Flag de Administrador</h1>
      <p class="muted">
        Este apartado está <strong>siempre abierto</strong>. Si has conseguido acceder al área administrativa (<code>/ops/admin</code>) directamente, explotando la API o por cualquier otro camino, puedes validar la bandera aquí en cualquier momento sin necesidad de haber completado todas las tareas del mapa.
      </p>

      <div class="thm-mask-box" style="margin:16px 0">
        <div>
          <div class="small muted" style="font-size:11px;text-transform:uppercase;letter-spacing:.05em">Formato de la bandera:</div>
          <div class="thm-mask">OSCPBT{{************************}}</div>
        </div>
        <span class="badge">32 caracteres</span>
      </div>

      {("<div class=\"alert "+('success' if is_done else 'error')+"\">"+msg+"</div>") if msg else ""}
      {("<div class=\"alert success\">✓ ¡Ya has validado con éxito la flag de Administrador de este laboratorio!</div>") if is_done and not msg else ""}

      <form method="post" style="margin-top:14px">
        <label>Bandera final (Flag)</label>
        <div class="thm-input-group">
          <input name="flag" required placeholder="OSCPBT{{...}}" autofocus value="{FLAG if is_done else ''}">
          <button class="btn green" style="white-space:nowrap">{"Validar de nuevo" if is_done else "Enviar Flag"}</button>
        </div>
      </form>
      
      <p class="small muted" style="margin-top:20px;text-align:center">
        ¿Aún te quedan tareas por resolver? <a href="/help">Volver al mapa de tareas para seguir practicando</a>
      </p>
    </div>
    """, True)

@app.route("/health")
def health(): return jsonify(status="ok", application="OSCPT-Burp-Trainer")

@app.errorhandler(404)
def not_found(_): return jsonify(error="not_found"), 404

if __name__ == "__main__":
    init_db()
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    print("\n==================================================")
    print("             OSCPT-BURP-TRAINER")
    print("==================================================")
    print("[+] Base de datos SQLite inicializada:", DB)
    print("[+] PeopleHub:     http://localhost:8010/")
    print("[+] Sala de Retos: http://localhost:8010/help")
    print("[+] Estado:        http://127.0.0.1:8010/health")
    print(f"[+] Recarga en vivo (Debug): {'Activada' if debug_mode else 'Desactivada'}")
    print("[*] Escuchando en el puerto 8010. Pulsa CTRL+C para detener.\n")
    app.run(host=HOST, port=PORT, debug=debug_mode, threaded=True)
