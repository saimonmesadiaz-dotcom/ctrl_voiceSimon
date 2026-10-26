
import json
import uuid
import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt

from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from streamlit_bokeh_events import streamlit_bokeh_events

# ==================================================
# CONFIGURACIÓN
# ==================================================

st.set_page_config(
    page_title="Garage Control | Interactive Systems",
    page_icon="🏎️",
    layout="wide"
)

BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC = "SimonArt"

# ==================================================
# ESTADO DE LA APLICACIÓN
# ==================================================

if "doors_open" not in st.session_state:
    st.session_state.doors_open = False

if "lights_on" not in st.session_state:
    st.session_state.lights_on = False

if "last_command" not in st.session_state:
    st.session_state.last_command = "Sistema preparado"

if "mqtt_client" not in st.session_state:
    st.session_state.mqtt_client = None

if "mqtt_connected" not in st.session_state:
    st.session_state.mqtt_connected = False

if "processed_voice" not in st.session_state:
    st.session_state.processed_voice = ""

# ==================================================
# MQTT
# ==================================================

def conectar_mqtt():
    """Crea una conexión MQTT persistente para esta sesión."""
    try:
        client = mqtt.Client(
            client_id="GarageUI_" + uuid.uuid4().hex[:8]
        )
        client.connect(BROKER, PORT, 60)
        client.loop_start()

        st.session_state.mqtt_client = client
        st.session_state.mqtt_connected = True
        return True

    except Exception as error:
        st.session_state.mqtt_connected = False
        st.session_state.mqtt_error = str(error)
        return False


def enviar_comando(comando):
    """Envía el formato que espera el ESP32 de Wokwi."""
    client = st.session_state.mqtt_client

    if client is None or not client.is_connected():
        st.session_state.mqtt_connected = False
        st.error("No hay conexión MQTT. Revisa el broker.")
        return False

    payload = json.dumps(
        {"Act1": comando},
        ensure_ascii=False
    )

    result = client.publish(TOPIC, payload, qos=0)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        st.session_state.last_command = comando
        st.session_state.mqtt_connected = True
        return True

    st.error("No fue posible publicar el comando.")
    return False


if (
    st.session_state.mqtt_client is None
    or not st.session_state.mqtt_client.is_connected()
):
    conectar_mqtt()

# ==================================================
# INTERPRETACIÓN DE VOZ
# ==================================================

def interpretar_comando(texto):
    """
    Convierte frases habladas en los textos exactos
    que reconoce el código de Wokwi.
    """
    texto = texto.lower().strip()
    texto = texto.replace("á", "a").replace("é", "e")
    texto = texto.replace("í", "i").replace("ó", "o")
    texto = texto.replace("ú", "u")

    # Puerta
    if (
        "abre la puerta" in texto
        or "abrir la puerta" in texto
        or "open the door" in texto
        or "open door" in texto
    ):
        return "abre la puerta", "door_open"

    if (
        "cierra la puerta" in texto
        or "cerrar la puerta" in texto
        or "close the door" in texto
        or "close door" in texto
    ):
        return "Cierra la puerta", "door_close"

    # Luces
    if (
        "enciende las luces" in texto
        or "encender las luces" in texto
        or "prende las luces" in texto
        or "turn on the lights" in texto
        or "lights on" in texto
    ):
        return "enciende las luces", "lights_on"

    if (
        "apaga las luces" in texto
        or "apagar las luces" in texto
        or "turn off the lights" in texto
        or "lights off" in texto
    ):
        return "apaga las luces", "lights_off"

    return None, None


def ejecutar_accion(accion):
    """Actualiza la interfaz y envía el comando MQTT."""
    comandos = {
        "door_open": ("abre la puerta", True, None),
        "door_close": ("Cierra la puerta", False, None),
        "lights_on": ("enciende las luces", None, True),
        "lights_off": ("apaga las luces", None, False),
    }

    if accion not in comandos:
        return

    comando, puertas, luces = comandos[accion]

    if enviar_comando(comando):
        if puertas is not None:
            st.session_state.doors_open = puertas
        if luces is not None:
            st.session_state.lights_on = luces

# ==================================================
# ESTILO VISUAL
# ==================================================

st.markdown("""
<style>
.stApp {
    background:
      radial-gradient(ellipse at 50% 0%, #40202b 0%, transparent 50%),
      linear-gradient(140deg, #100b10, #261019 60%, #100b10);
    color: #fff2dc;
}

.block-container {
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    color: #f4c65e !important;
}

p, label {
    color: #f2dfd4;
}

div.stButton > button {
    width: 100%;
    min-height: 50px;
    border-radius: 12px;
    border: 1px solid #c99b42;
    background: linear-gradient(135deg, #681c30, #3b111e);
    color: #fff5dc;
    font-weight: 700;
    transition: all .2s ease;
}

div.stButton > button:hover {
    border-color: #ffe38b;
    background: linear-gradient(135deg, #9b2941, #64192c);
    color: white;
    transform: translateY(-1px);
}

div[data-testid="stAlert"] {
    border-radius: 12px;
}

.eyebrow {
    color: #d7a94d;
    font-size: 12px;
    letter-spacing: 4px;
    font-weight: 700;
}

.panel {
    background: rgba(255,255,255,.045);
    border: 1px solid rgba(224,175,89,.28);
    border-radius: 18px;
    padding: 20px;
}

.muted {
    color: #c6aaa9;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# ENCABEZADO
# ==================================================

st.markdown(
    '<div class="eyebrow">INTERACTIVE AUTOMOTIVE SYSTEM</div>',
    unsafe_allow_html=True
)

st.title("GARAGE CONTROL")
st.write("Control por voz · Simulación visual · ESP32 + MQTT")

if st.session_state.mqtt_connected:
    st.success("MQTT conectado · " + BROKER)
else:
    st.warning("MQTT desconectado. Comprueba la conexión y vuelve a ejecutar la aplicación.")
    if st.button("REINTENTAR CONEXIÓN"):
        conectar_mqtt()
        st.rerun()

# ==================================================
# SIMULACIÓN DEL CARRO
# ==================================================

puertas_abiertas = st.session_state.doors_open
luces_encendidas = st.session_state.lights_on

angulo_puerta = -52 if puertas_abiertas else 0
color_faro = "#fff3a0" if luces_encendidas else "#63545b"
filtro_faro = "url(#headlightGlow)" if luces_encendidas else ""

car_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{
  margin: 0;
  background: transparent;
  font-family: Arial, sans-serif;
}}
.scene {{
  box-sizing: border-box;
  width: 100%;
  padding: 20px 10px 12px;
  border: 1px solid #694333;
  border-radius: 22px;
  background:
    radial-gradient(ellipse at 50% 65%, #542432 0%, #28131d 48%, #160c12 100%);
  overflow: hidden;
}}
.kicker {{
  color: #d6b26c;
  text-align: center;
  letter-spacing: 4px;
  font-size: 11px;
}}
svg {{
  display: block;
  width: 100%;
  height: auto;
  max-height: 340px;
}}
.wheel {{
  transform-box: fill-box;
  transform-origin: center;
}}
.door {{
  transform-box: view-box;
  transform-origin: 405px 160px;
  transition: transform 900ms cubic-bezier(.2,.7,.2,1);
}}
.status {{
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 4px 2px;
}}
.pill {{
  color: #f9df9b;
  background: #321923;
  border: 1px solid #76503e;
  border-radius: 99px;
  padding: 9px 14px;
  font-size: 12px;
  letter-spacing: 1px;
}}
</style>
</head>
<body>
<div class="scene">
  <div class="kicker">LIVE VEHICLE SIMULATION</div>

  <svg viewBox="0 0 800 330" role="img"
       aria-label="Carro deportivo animado">
    <defs>
      <linearGradient id="carPaint" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#ff6870"/>
        <stop offset="42%" stop-color="#c32240"/>
        <stop offset="100%" stop-color="#5b1028"/>
      </linearGradient>
      <linearGradient id="windowGlass" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#b9d8dd"/>
        <stop offset="100%" stop-color="#263745"/>
      </linearGradient>
      <filter id="headlightGlow" x="-200%" y="-200%"
              width="400%" height="400%">
        <feGaussianBlur stdDeviation="8" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>

    <ellipse cx="407" cy="269" rx="300" ry="23"
             fill="#000" opacity=".6"/>

    <!-- Carro -->
    <path d="M91 224 L115 191 Q131 177 193 167
             L281 108 Q308 88 360 89 L473 94
             Q514 97 552 142 L652 170
             Q689 182 708 215 L699 240
             L102 240 Z"
          fill="url(#carPaint)" stroke="#ff8a88" stroke-width="3"/>

    <!-- Ventanas -->
    <path d="M244 157 L300 112 Q319 101 355 103
             L356 157 Z"
          fill="url(#windowGlass)" stroke="#f1c4b3" stroke-width="3"/>
    <path d="M372 103 L467 108 Q499 112 529 157
             L372 157 Z"
          fill="url(#windowGlass)" stroke="#f1c4b3" stroke-width="3"/>

    <!-- Detalles de carrocería -->
    <path d="M360 99 L360 224" stroke="#f4b7a5"
          stroke-width="3" opacity=".8"/>
    <path d="M128 196 L218 184 L204 198 L120 210 Z"
          fill="#f5c65e" opacity=".65"/>
    <path d="M615 178 L664 194 L681 211 L625 205 Z"
          fill="{color_faro}" filter="{filtro_faro}"/>
    <path d="M104 214 L151 210 L146 226 L103 226 Z"
          fill="#ff334c"/>
    <path d="M109 241 L696 241" stroke="#e9bd60"
          stroke-width="3" opacity=".8"/>

    <!-- Ruedas -->
    <g class="wheel">
      <circle cx="228" cy="236" r="47" fill="#0b0b0e"/>
      <circle cx="228" cy="236" r="29" fill="#8d8885"/>
      <circle cx="228" cy="236" r="17" fill="#29252a"/>
      <circle cx="598" cy="236" r="47" fill="#0b0b0e"/>
      <circle cx="598" cy="236" r="29" fill="#8d8885"/>
      <circle cx="598" cy="236" r="17" fill="#29252a"/>
    </g>

    <!-- Puerta animada -->
    <g class="door" style="transform: rotate({angulo_puerta}deg)">
      <path d="M373 160 L500 160 L530 215 L373 216 Z"
            fill="#a91935" stroke="#ffd2b5" stroke-width="3"/>
      <path d="M394 175 L466 175"
            stroke="#e99d96" stroke-width="3"/>
      <rect x="477" y="190" width="17" height="5"
            rx="2" fill="#f9d8a9"/>
    </g>

    <!-- Reflejos -->
    <path d="M274 166 L539 166" stroke="#ffb3a7"
          stroke-width="2" opacity=".5"/>
  </svg>

  <div class="status">
    <div class="pill">DOORS: {"OPEN" if puertas_abiertas else "CLOSED"}</div>
    <div class="pill">LIGHTS: {"ON" if luces_encendidas else "OFF"}</div>
  </div>
</div>
</body>
</html>
"""

components.html(car_html, height=390, scrolling=False)

# ==================================================
# CONTROLES MANUALES
# ==================================================

st.markdown("## Vehicle controls")
col_puertas, col_luces = st.columns(2)

with col_puertas:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("🚪 Door system")

    if st.button("OPEN DOOR", key="open_door"):
        ejecutar_accion("door_open")
        st.rerun()

    if st.button("CLOSE DOOR", key="close_door"):
        ejecutar_accion("door_close")
        st.rerun()

    estado_puerta = "OPEN" if st.session_state.doors_open else "CLOSED"
    st.markdown(
        f'<p class="muted">Door status: {estado_puerta}</p>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col_luces:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("💡 Lighting system")

    if st.button("TURN LIGHTS ON", key="turn_lights_on"):
        ejecutar_accion("lights_on")
        st.rerun()

    if st.button("TURN LIGHTS OFF", key="turn_lights_off"):
        ejecutar_accion("lights_off")
        st.rerun()

    estado_luces = "ON" if st.session_state.lights_on else "OFF"
    st.markdown(
        f'<p class="muted">Lights status: {estado_luces}</p>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ==================================================
# CONTROL POR VOZ
# ==================================================

st.markdown("---")
st.markdown("## 🎙️ Voice control")
st.write(
    "Pulsa el botón de escucha y di uno de los comandos disponibles. "
    "Permite el acceso al micrófono si el navegador lo solicita."
)

st.caption(
    "Comandos: «abre la puerta», «cierra la puerta», "
    "«enciende las luces» y «apaga las luces»."
)

voice_button = Button(label="🎙️ START LISTENING", width=260)

voice_button.js_on_event(
    "button_click",
    CustomJS(code="""
        const SpeechRecognition =
            window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            document.dispatchEvent(
                new CustomEvent("VOICE_ERROR", {
                    detail: "Este navegador no soporta reconocimiento de voz."
                })
            );
        } else {
            const recognition = new SpeechRecognition();
            recognition.lang = "es-CO";
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            recognition.onresult = function(event) {
                const text = event.results[0][0].transcript;
                document.dispatchEvent(
                    new CustomEvent("GET_TEXT", {detail: text})
                );
            };

            recognition.onerror = function(event) {
                document.dispatchEvent(
                    new CustomEvent("VOICE_ERROR", {
                        detail: event.error
                    })
                );
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
    debounce_time=0
)

if voice_result:
    if "VOICE_ERROR" in voice_result:
        st.warning(
            "No se pudo usar el micrófono: "
            + str(voice_result["VOICE_ERROR"])
        )

    if "GET_TEXT" in voice_result:
        frase = str(voice_result["GET_TEXT"]).strip()

        if frase and frase != st.session_state.processed_voice:
            st.session_state.processed_voice = frase
            st.write("Has dicho: **" + frase + "**")

            comando, accion = interpretar_comando(frase)

            if accion:
                ejecutar_accion(accion)
                st.rerun()
            else:
                st.warning(
                    "No reconocí ese comando. Intenta decir "
                    "«abre la puerta», «cierra la puerta», "
                    "«enciende las luces» o «apaga las luces»."
                )

# ==================================================
# ESTADO Y AYUDA
# ==================================================

st.markdown("---")
st.markdown("### System information")
st.write("**Broker:**", BROKER)
st.write("**Topic:**", TOPIC)
st.write("**Último comando:**", st.session_state.last_command)

st.caption(
    "Prototipo académico. La animación es visual; "
    "el movimiento físico se ejecuta en el ESP32."
)
