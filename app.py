import json
import re
import unicodedata
import uuid

import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
from bokeh.models import Button, CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from streamlit_autorefresh import st_autorefresh

# Refresco periódico para mantener actualizado el estado del ESP32.
st_autorefresh(interval=3000, key="garage_status_refresh")


# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Garage Control | Interactive Systems",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC = "SimonArt"

# ============================================================
# ESTADO
# ============================================================
defaults = {
    "doors_open": False,
    "lights_on": False,
    "last_command": "Sistema preparado",
    "mqtt_client": None,
    "mqtt_connected": False,
    "mqtt_error": "",
    "last_voice_text": "",
    "voice_message": "",
    "esp32_online": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# MQTT
# ============================================================
def _on_mqtt_message(client, userdata, msg):
    """Recibe el heartbeat publicado por el ESP32 en Wokwi."""
    if msg.topic == f"{TOPIC}/status":
        value = msg.payload.decode("utf-8", errors="ignore").strip().lower()
        st.session_state.esp32_online = (value == "online")


def get_mqtt_client():
    client = st.session_state.mqtt_client
    if client is not None and client.is_connected():
        return client

    try:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id="GarageUI_" + uuid.uuid4().hex[:8],
            protocol=mqtt.MQTTv311,
        )
        client.on_message = _on_mqtt_message
        client.connect(BROKER, PORT, keepalive=45)
        client.loop_start()

        # Espera breve por el CONNACK; evita marcar conectado antes de tiempo.
        import time
        deadline = time.time() + 4
        while not client.is_connected() and time.time() < deadline:
            time.sleep(0.1)

        if not client.is_connected():
            raise ConnectionError("El broker no confirmó la conexión MQTT en 4 segundos.")

        client.subscribe(f"{TOPIC}/status", qos=0)
        st.session_state.mqtt_client = client
        st.session_state.mqtt_connected = True
        st.session_state.mqtt_error = ""
        return client
    except Exception as exc:
        st.session_state.mqtt_connected = False
        st.session_state.mqtt_error = str(exc)
        return None


def enviar_mqtt(comando):
    client = get_mqtt_client()
    if client is None:
        st.session_state.last_command = f"Error de conexión: {comando}"
        return False

    payload = json.dumps({"Act1": comando}, ensure_ascii=False)
    try:
        info = client.publish(TOPIC, payload, qos=0, retain=False)
        info.wait_for_publish(timeout=3)
        if info.rc == mqtt.MQTT_ERR_SUCCESS and info.is_published():
            st.session_state.mqtt_connected = True
            st.session_state.last_command = comando
            return True
        st.session_state.mqtt_connected = False
        st.session_state.mqtt_error = "El broker no confirmó la publicación."
        return False
    except Exception as exc:
        st.session_state.mqtt_connected = False
        st.session_state.mqtt_error = str(exc)
        return False


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower().strip())
    return "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")


def interpretar_comando(texto):
    frase = normalizar(texto)
    if any(x in frase for x in (
        "abre la puerta", "abrir la puerta", "abre la puerta del carro",
        "abre la puerta del coche", "open the door", "open door",
    )):
        return "door_open"
    if any(x in frase for x in (
        "cierra la puerta", "cerrar la puerta", "cierra la puerta del carro",
        "cierra la puerta del coche", "close the door", "close door",
    )):
        return "door_close"
    if any(x in frase for x in (
        "enciende las luces", "encender las luces", "prende las luces",
        "prender las luces", "turn on the lights", "lights on",
    )):
        return "lights_on"
    if any(x in frase for x in (
        "apaga las luces", "apagar las luces", "turn off the lights", "lights off",
    )):
        return "lights_off"
    return None


def ejecutar_accion(accion):
    acciones = {
        "door_open": ("abre la puerta", "doors_open", True),
        "door_close": ("Cierra la puerta", "doors_open", False),
        "lights_on": ("enciende las luces", "lights_on", True),
        "lights_off": ("apaga las luces", "lights_on", False),
    }
    if accion not in acciones:
        return False

    comando, state_key, new_value = acciones[accion]
    if enviar_mqtt(comando):
        st.session_state[state_key] = new_value
        return True
    return False


# Attempt connection when app loads. Buttons allow retry if broker isn't ready.
get_mqtt_client()

# ============================================================
# ESTILOS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
  --bg: #100d0b;
  --panel: #1b1514;
  --panel2: #261b19;
  --line: rgba(245,197,94,.18);
  --text: #fff4dc;
  --muted: #c1aaa0;
  --red: #f2c14e;
  --red2: #b88624;
  --gold: #ffe08a;
}
html, body, [class*="css"] {
  font-family: 'Manrope', sans-serif;
}
.stApp {
  background:
    radial-gradient(ellipse at 78% 0%, rgba(151,72,28,.22), transparent 38%),
    radial-gradient(ellipse at 8% 35%, rgba(184,134,36,.10), transparent 34%),
    linear-gradient(145deg, #100d0b 0%, #241715 54%, #120e0d 100%);
  color: var(--text);
}
.block-container {
  max-width: 1380px;
  padding-top: 2rem;
  padding-bottom: 3rem;
}
h1, h2, h3, p, label { color: var(--text); }
h1 { letter-spacing: -1.5px; font-weight: 800 !important; }
h2, h3 { letter-spacing: -.5px; }
[data-testid="stCaptionContainer"], .muted { color: var(--muted) !important; }
.eyebrow {
  font: 500 11px 'DM Mono', monospace;
  color: var(--red);
  letter-spacing: 3px;
  text-transform: uppercase;
}
.hero-title {
  font-size: clamp(34px, 4.5vw, 58px);
  line-height: 1.02;
  font-weight: 800;
  letter-spacing: -2.5px;
  margin: 7px 0 10px 0;
}
.hero-sub {
  color: var(--muted);
  font-size: 14px;
  max-width: 640px;
}
.panel {
  background: linear-gradient(145deg, rgba(25,30,41,.96), rgba(16,19,27,.96));
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 22px;
  height: 100%;
}
.section-label {
  color: var(--muted);
  font: 500 11px 'DM Mono', monospace;
  letter-spacing: 2px;
  text-transform: uppercase;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 99px;
  background: rgba(255,255,255,.045);
  border: 1px solid var(--line);
  color: #dce1e9;
  font: 500 11px 'DM Mono', monospace;
  letter-spacing: .5px;
}
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  display: inline-block;
}
div.stButton > button {
  width: 100%;
  min-height: 48px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.12);
  background: #202532;
  color: #f4f5f7;
  font-weight: 700;
  transition: transform .18s ease, box-shadow .18s ease,
              background .18s ease, border-color .18s ease;
}
div.stButton > button:hover {
  transform: translateY(-2px);
  background: #2a303e;
  border-color: rgba(242,193,78,.85);
  color: white;
  box-shadow: 0 8px 22px rgba(0,0,0,.30);
}
div.stButton > button:active {
  transform: translateY(0) scale(.985);
}
div.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #f5d16a, #b88624);
  border-color: #f5d16a;
  color: white;
}
div.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #ffe38b, #d5a334);
  box-shadow: 0 8px 24px rgba(242,193,78,.22);
}
div[data-testid="stAlert"] { border-radius: 12px; }
hr { border-color: var(--line); }
div[data-testid="stMetric"] {
  background: rgba(255,255,255,.035);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px 16px;
}
div[data-testid="stMetricLabel"] { color: var(--muted); }
div[data-testid="stMetricValue"] { color: var(--text); }
.voice-card {
  display:flex; align-items:center; gap:14px; padding:16px;
  border:1px solid rgba(245,197,94,.28); border-radius:16px;
  background:linear-gradient(135deg, rgba(245,197,94,.09), rgba(255,255,255,.025));
  margin:8px 0 12px;
}
.voice-icon { display:flex; align-items:center; justify-content:center; flex:0 0 44px;
  width:44px; height:44px; border-radius:14px; color:#2a1a0b;
  background:linear-gradient(135deg,#ffe38b,#c18a24); font-size:24px; font-weight:800;
}
.voice-card-title { color:#fff0c7; font-weight:800; font-size:15px; }
.voice-card-sub { color:#c6aaa0; font-size:12px; margin-top:3px; }
.voice-note {
  padding: 12px 14px;
  border: 1px solid var(--line);
  background: rgba(255,224,138,.045);
  border-radius: 12px;
  color: var(--muted);
  font-size: 13px;
}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# ENCABEZADO
# ============================================================
st.markdown('<div class="eyebrow">INTERACTIVE AUTOMOTIVE SYSTEMS / 001</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">GARAGE <span style="color:#f2c14e">CONTROL.</span></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Una interfaz multimodal para controlar funciones del vehículo '
    'con voz o con controles directos. Streamlit · MQTT · ESP32</div>',
    unsafe_allow_html=True,
)
st.write("")

connection_col, topic_col, mode_col = st.columns([1.2, 1.2, 1.5])
with connection_col:
    if st.session_state.mqtt_connected:
        st.markdown('<div class="status-pill"><span class="status-dot" style="background:#42d392"></span> BROKER MQTT CONECTADO</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill"><span class="status-dot" style="background:#ff6b6b"></span> BROKER MQTT DESCONECTADO</div>', unsafe_allow_html=True)
    if st.session_state.mqtt_connected and st.session_state.esp32_online:
        st.markdown('<div class="status-pill" style="margin-top:8px"><span class="status-dot" style="background:#42d392"></span> ESP32 / WOKWI EN LÍNEA</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill" style="margin-top:8px"><span class="status-dot" style="background:#f2c14e"></span> ESP32 / WOKWI SIN HEARTBEAT</div>', unsafe_allow_html=True)
with topic_col:
    st.markdown(f'<div class="status-pill">TOPIC&nbsp; / &nbsp;{TOPIC}</div>', unsafe_allow_html=True)
with mode_col:
    st.markdown('<div class="status-pill">SISTEMA&nbsp; / &nbsp; CONTROL LOCAL + VOZ</div>', unsafe_allow_html=True)

if not st.session_state.mqtt_connected:
    with st.expander("Problemas de conexión MQTT", expanded=False):
        st.write("Broker:", BROKER, "· Puerto:", PORT)
        if st.session_state.mqtt_error:
            st.code(st.session_state.mqtt_error)
        if st.button("Reintentar conexión", key="retry_mqtt"):
            get_mqtt_client()
            st.rerun()

st.write("")
left, right = st.columns([1.55, 1], gap="large")

# ============================================================
# COCHE SVG: HOVER + PUERTA + LUCES
# ============================================================
with left:
    doors_open = st.session_state.doors_open
    lights_on = st.session_state.lights_on

    door_transform = "rotate(-48 365 176)" if doors_open else "rotate(0 365 176)"
    headlight = "#fff3b0" if lights_on else "#5b6676"
    glow = "url(#lightGlow)" if lights_on else "none"
    light_opacity = "0.28" if lights_on else "0"

    car_html = f"""
    <!doctype html><html><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      * {{ box-sizing: border-box; }}
      body {{ margin:0; background:transparent; color:#f4f5f7; font-family:Manrope,Arial,sans-serif; }}
      .garage {{
        border:1px solid rgba(245,197,94,.22); border-radius:22px;
        background: radial-gradient(ellipse at 50% 75%, #3a2520 0%, #241816 53%, #15100f 100%);
        padding:20px 18px 16px; overflow:hidden;
        box-shadow: inset 0 1px rgba(255,255,255,.035);
      }}
      .topline {{ display:flex; justify-content:space-between; align-items:center; gap:12px; }}
      .eyebrow {{ color:#c5a96b; font:11px monospace; letter-spacing:2px; }}
      .scene-title {{ margin-top:5px; font-size:19px; font-weight:800; letter-spacing:-.4px; }}
      .live {{ font:10px monospace; letter-spacing:1px; color:#ffe08a; border:1px solid rgba(245,197,94,.35); background:rgba(245,197,94,.08); border-radius:99px; padding:7px 9px; white-space:nowrap; }}
      svg {{ width:100%; height:auto; display:block; margin:4px auto 0; overflow:visible; }}
      .car-body {{ transition: filter .3s ease; }}
      .car-group {{ transform-origin:center; transition:transform .35s ease; }}
      .car-group:hover {{ transform:translateY(-3px); }}
      .door {{ transform-origin:365px 176px; transition:transform .85s cubic-bezier(.2,.8,.2,1); }}
      .wheel {{ transition:filter .25s ease; }}
      .car-group:hover .wheel {{ filter:brightness(1.18); }}
      .light-beam {{ transition:opacity .35s ease; }}
      .readouts {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
      .readout {{ background:rgba(12,8,7,.42); border:1px solid rgba(245,197,94,.13); border-radius:13px; padding:12px 14px; }}
      .label {{ color:#bca58b; font:10px monospace; letter-spacing:1.7px; }}
      .value {{ color:#f2f3f6; font-size:13px; font-weight:800; margin-top:6px; }}
      .value.red {{ color:#ffe08a; }} .value.gold {{ color:#ffe39a; }}
      .bottomline {{ display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-top:13px; color:#727d8f; font:10px monospace; letter-spacing:1px; }}
      @media(max-width:520px) {{ .garage {{padding:14px 10px}} .scene-title {{font-size:16px}} }}
    </style></head><body>
    <div class="garage">
      <div class="topline">
        <div><div class="eyebrow">LIVE VEHICLE SIMULATION</div><div class="scene-title">Redline / R-01</div></div>
        <div class="live">● SIMULATION ACTIVE</div>
      </div>
      <svg viewBox="0 0 800 340" role="img" aria-label="Deportivo rojo con puerta y luces animadas">
        <defs>
          <linearGradient id="paint" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#ff6673"/><stop offset="32%" stop-color="#e32c46"/>
            <stop offset="75%" stop-color="#a8132e"/><stop offset="100%" stop-color="#5c0c20"/>
          </linearGradient>
          <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#d2e8ec"/><stop offset="45%" stop-color="#66808f"/><stop offset="100%" stop-color="#202b37"/>
          </linearGradient>
          <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#f2c14e" stop-opacity=".22"/><stop offset="100%" stop-color="#f2c14e" stop-opacity="0"/>
          </linearGradient>
          <filter id="lightGlow" x="-200%" y="-200%" width="400%" height="400%">
            <feGaussianBlur stdDeviation="7" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="10"/>
          </filter>
        </defs>
        <ellipse cx="405" cy="273" rx="290" ry="24" fill="#000" opacity=".65"/>
        <ellipse cx="600" cy="249" rx="150" ry="34" fill="url(#floor)" opacity=".9"/>
        <g class="car-group">
          <!-- Body -->
          <path class="car-body" d="M83 225 L104 196 Q119 179 177 169 L260 111 Q285 91 333 91 L467 96 Q505 99 542 140 L640 166 Q680 177 708 211 L701 239 L91 242 Z"
            fill="url(#paint)" stroke="#ffe08a" stroke-width="2.5"/>
          <!-- Window glass -->
          <path d="M242 157 L292 116 Q310 103 340 105 L350 157 Z" fill="url(#glass)" stroke="#f6d991" stroke-width="2.5"/>
          <path d="M365 105 L464 110 Q492 114 523 157 L365 157 Z" fill="url(#glass)" stroke="#f6d991" stroke-width="2.5"/>
          <!-- Windshield reflection -->
          <path d="M305 115 L337 110 L343 150 L270 150 Z" fill="#fff" opacity=".09"/>
          <!-- Hood and sculpted lines -->
          <path d="M365 100 L365 226" stroke="#f7d47a" stroke-width="2.5" opacity=".65"/>
          <path d="M113 197 L216 182 L198 198 L121 211 Z" fill="#ff9da5" opacity=".5"/>
          <path d="M391 169 L544 169" stroke="#f2c14e" stroke-width="2" opacity=".45"/>
          <path d="M104 240 L699 240" stroke="#ffe08a" stroke-width="2" opacity=".65"/>
          <!-- Wheels -->
          <g class="wheel">
            <circle cx="222" cy="237" r="47" fill="#080a0f" stroke="#424653" stroke-width="3"/>
            <circle cx="222" cy="237" r="30" fill="#9ca1aa"/><circle cx="222" cy="237" r="23" fill="#353a45"/>
            <circle cx="222" cy="237" r="8" fill="#c7cbd2"/>
            <path d="M222 215 V259 M200 237 H244 M206 221 L238 253 M238 221 L206 253" stroke="#aeb4be" stroke-width="3"/>
            <circle cx="598" cy="237" r="47" fill="#080a0f" stroke="#424653" stroke-width="3"/>
            <circle cx="598" cy="237" r="30" fill="#9ca1aa"/><circle cx="598" cy="237" r="23" fill="#353a45"/>
            <circle cx="598" cy="237" r="8" fill="#c7cbd2"/>
            <path d="M598 215 V259 M576 237 H620 M582 221 L614 253 M614 221 L582 253" stroke="#aeb4be" stroke-width="3"/>
          </g>
          <!-- Headlights and light beams -->
          <path d="M628 177 L668 191 L686 207 L639 201 Z" fill="{headlight}" filter="{glow}"/>
          <path class="light-beam" d="M670 191 L790 158 L790 239 L670 207 Z" fill="#fff1a0" opacity="{light_opacity}"/>
          <path d="M99 212 L143 207 L139 224 L98 226 Z" fill="#ff4057"/>
          <path d="M95 213 L120 210" stroke="#ffbdc4" stroke-width="3"/>
          <!-- Door hinged on front edge -->
          <g class="door" style="transform:{door_transform}">
            <path d="M365 160 L493 160 L520 215 L365 216 Z" fill="#b51b35" stroke="#ffc1c5" stroke-width="2.5"/>
            <path d="M382 174 L460 174" stroke="#f2c14e" stroke-width="2.5"/>
            <rect x="467" y="188" width="18" height="5" rx="2.5" fill="#ffe0d4"/>
            <path d="M368 164 L368 211" stroke="#681023" stroke-width="2"/>
          </g>
          <!-- Mirrors and trim -->
          <path d="M522 153 L548 159 L543 169 L522 166 Z" fill="#b51b35" stroke="#ff8b98" stroke-width="2"/>
          <path d="M121 228 L160 228" stroke="#f9c7c8" stroke-width="2" opacity=".6"/>
        </g>
      </svg>
      <div class="readouts">
        <div class="readout"><div class="label">DOOR SYSTEM</div><div class="value {'red' if doors_open else ''}">{"OPEN / 180°" if doors_open else "CLOSED / 90°"}</div></div>
        <div class="readout"><div class="label">LIGHTING SYSTEM</div><div class="value {'gold' if lights_on else ''}">{"HEADLIGHTS ON" if lights_on else "HEADLIGHTS OFF"}</div></div>
      </div>
      <div class="bottomline"><span>GARAGE CONTROL / PROTOTYPE</span><span>ESP32 + MQTT</span></div>
    </div></body></html>
    """
    components.html(car_html, height=470, scrolling=False)
    st.caption("Vista conceptual: los cambios gráficos reflejan las órdenes enviadas, no una lectura física del servo.")

# ============================================================
# CONTROLES
# ============================================================
with right:
    st.markdown('<div class="section-label">CONTROL CENTER / 01</div>', unsafe_allow_html=True)
    st.subheader("Control del vehículo")
    st.markdown('<div class="voice-note">Usa los controles manuales o activa el reconocimiento de voz. Cada acción se envía al ESP32 por MQTT.</div>', unsafe_allow_html=True)
    st.write("")

    st.markdown("**PUERTAS**")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("↗ Abrir", key="open_door", type="primary", use_container_width=True):
            if ejecutar_accion("door_open"):
                st.rerun()
            else:
                st.error("No se pudo enviar la orden. Revisa la conexión MQTT.")
    with c2:
        if st.button("↙ Cerrar", key="close_door", use_container_width=True):
            if ejecutar_accion("door_close"):
                st.rerun()
            else:
                st.error("No se pudo enviar la orden. Revisa la conexión MQTT.")

    st.write("")
    st.markdown("**ILUMINACIÓN**")
    c3, c4 = st.columns(2)
    with c3:
        if st.button("☼ Encender", key="btn_lights_on", type="primary", use_container_width=True):
            if ejecutar_accion("lights_on"):
                st.rerun()
            else:
                st.error("No se pudo enviar la orden. Revisa la conexión MQTT.")
    with c4:
        if st.button("◐ Apagar", key="btn_lights_off", use_container_width=True):
            if ejecutar_accion("lights_off"):
                st.rerun()
            else:
                st.error("No se pudo enviar la orden. Revisa la conexión MQTT.")

    st.write("")
    st.markdown("---")
    st.markdown('<div class="section-label">VOICE INTERFACE / 02</div>', unsafe_allow_html=True)
    st.subheader("Control por voz")
    st.caption("Di una orden breve en español. Ej.: «abre la puerta» o «enciende las luces».")

    st.markdown('<div class="voice-card"><div class="voice-icon">◉</div><div><div class="voice-card-title">Habla con tu vehículo</div><div class="voice-card-sub">Pulsa el botón y di una orden. El micrófono se activa solo durante la escucha.</div></div></div>', unsafe_allow_html=True)
    voice_button = Button(label="🎙  INICIAR RECONOCIMIENTO DE VOZ", width=360, height=54, button_type="warning")
    voice_button.js_on_event(
        "button_click",
        CustomJS(code="""
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                document.dispatchEvent(new CustomEvent("VOICE_ERROR", {detail: "Tu navegador no admite reconocimiento de voz."}));
            } else {
                const recognition = new SpeechRecognition();
                recognition.lang = "es-CO";
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.maxAlternatives = 1;
                recognition.onresult = function(event) {
                    document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: event.results[0][0].transcript}));
                };
                recognition.onerror = function(event) {
                    document.dispatchEvent(new CustomEvent("VOICE_ERROR", {detail: event.error}));
                };
                recognition.start();
            }
        """)
    )
    voice_result = streamlit_bokeh_events(
        voice_button,
        events="GET_TEXT,VOICE_ERROR",
        key="voice_listener",
        refresh_on_update=True,
        override_height=70,
        debounce_time=0,
    )

    if voice_result:
        if "VOICE_ERROR" in voice_result:
            st.warning("No se pudo usar el micrófono: " + str(voice_result["VOICE_ERROR"]))
        if "GET_TEXT" in voice_result:
            frase = str(voice_result["GET_TEXT"]).strip()
            if frase and frase != st.session_state.last_voice_text:
                st.session_state.last_voice_text = frase
                accion = interpretar_comando(frase)
                st.session_state.voice_message = frase
                if accion:
                    if ejecutar_accion(accion):
                        st.rerun()
                    else:
                        st.error("Se reconoció la voz, pero no se pudo enviar por MQTT.")
                else:
                    st.warning(f"No reconocí «{frase}». Prueba con una de las cuatro órdenes disponibles.")

    if st.session_state.voice_message:
        st.markdown(f'<div class="voice-note">Última frase detectada: <b>{st.session_state.voice_message}</b></div>', unsafe_allow_html=True)

# ============================================================
# ESTADO INFERIOR
# ============================================================
st.write("")
st.markdown("---")
st.markdown('<div class="section-label">SYSTEM STATUS / 03</div>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Puerta", "Abierta" if st.session_state.doors_open else "Cerrada")
with m2:
    st.metric("Luces", "Encendidas" if st.session_state.lights_on else "Apagadas")
with m3:
    st.metric("Broker MQTT", "Conectado" if st.session_state.mqtt_connected else "Desconectado")
with m4:
    st.metric("ESP32 / Wokwi", "En línea" if st.session_state.esp32_online else "Sin señal")
st.caption(f"Broker: {BROKER}:{PORT}  ·  Tópico: {TOPIC}  ·  Última orden enviada: {st.session_state.last_command}")
