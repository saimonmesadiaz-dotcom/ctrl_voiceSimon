
import json
import re
import unicodedata

import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt

from bokeh.models import Button, CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events


# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

st.set_page_config(
    page_title="WoWy | Control inteligente",
    page_icon="🚘",
    layout="wide"
)

BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC = "SimonArt"  # Debe coincidir con client.subscribe() en Wokwi


# --------------------------------------------------
# ESTADO DE LA SIMULACIÓN
# --------------------------------------------------

if "puerta_abierta" not in st.session_state:
    st.session_state.puerta_abierta = False

if "luces_encendidas" not in st.session_state:
    st.session_state.luces_encendidas = False

if "ultima_orden" not in st.session_state:
    st.session_state.ultima_orden = "Esperando una orden"

if "mensaje_mqtt" not in st.session_state:
    st.session_state.mensaje_mqtt = "Listo para conectar"


# --------------------------------------------------
# MQTT
# --------------------------------------------------

def enviar_mqtt(orden):
    """Envía al ESP32 el JSON que espera su callback."""

    payload = json.dumps({"Act1": orden})

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION1,
        client_id="WoWyStreamlit"
    )

    try:
        client.connect(BROKER, PORT, keepalive=30)
        client.loop_start()

        info = client.publish(TOPIC, payload, qos=0)
        info.wait_for_publish(timeout=3)

        if info.is_published():
            st.session_state.mensaje_mqtt = (
                f"Orden enviada: {orden}"
            )
        else:
            st.session_state.mensaje_mqtt = (
                "No se confirmó la publicación MQTT."
            )

        client.loop_stop()
        client.disconnect()

    except Exception as error:
        st.session_state.mensaje_mqtt = (
            f"Error MQTT: {error}"
        )


# --------------------------------------------------
# INTERPRETACIÓN DE LAS ÓRDENES
# --------------------------------------------------

def normalizar(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)

    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


def interpretar_orden(texto):
    """
    Actualiza la simulación y publica la orden
    que reconoce el programa del ESP32.
    """

    orden = normalizar(texto)

    if any(frase in orden for frase in [
        "enciende las luces",
        "prende las luces",
        "encender las luces",
        "prender las luces"
    ]):
        st.session_state.luces_encendidas = True
        st.session_state.ultima_orden = "Luces encendidas"
        enviar_mqtt("enciende las luces")

    elif any(frase in orden for frase in [
        "apaga las luces",
        "apagar las luces"
    ]):
        st.session_state.luces_encendidas = False
        st.session_state.ultima_orden = "Luces apagadas"
        enviar_mqtt("apaga las luces")

    elif any(frase in orden for frase in [
        "abre la puerta",
        "abrir la puerta",
        "abre la puerta del carro",
        "abre la puerta del coche"
    ]):
        st.session_state.puerta_abierta = True
        st.session_state.ultima_orden = "Puerta abierta"
        enviar_mqtt("abre la puerta")

    elif any(frase in orden for frase in [
        "cierra la puerta",
        "cerrar la puerta",
        "cierra la puerta del carro",
        "cierra la puerta del coche"
    ]):
        st.session_state.puerta_abierta = False
        st.session_state.ultima_orden = "Puerta cerrada"
        enviar_mqtt("Cierra la puerta")

    else:
        st.session_state.ultima_orden = (
            f"No reconocí la orden: {texto}"
        )


# --------------------------------------------------
# INTERFAZ
# --------------------------------------------------

st.markdown("""
<style>
.stApp {
    background: #10151d;
    color: #edf2f7;
}
h1, h2, h3, p, label {
    color: #edf2f7;
}
div.stButton > button {
    border-radius: 12px;
    min-height: 46px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

st.title("WoWy")
st.caption("INTERFACES MULTIMODALES · CONTROL POR VOZ")

st.markdown(
    "Controla un automóvil mediante comandos de voz "
    "o utilizando los controles manuales."
)

col_car, col_controls = st.columns([1.65, 1], gap="large")


# --------------------------------------------------
# AUTOMÓVIL ANIMADO
# --------------------------------------------------

with col_car:

    puerta = st.session_state.puerta_abierta
    luces = st.session_state.luces_encendidas

    puerta_transform = (
        "rotate(-58 205 151)" if puerta
        else "rotate(0 205 151)"
    )

    luz_color = "#fff3a3" if luces else "#566273"
    luz_glow = (
        "0 0 20px #ffe878"
        if luces else "none"
    )

    svg = """
    <div style="
        background:linear-gradient(145deg,#202b3a,#141b26);
        border:1px solid #344254;
        border-radius:24px;
        padding:20px;
        color:#edf2f7;
        font-family:Arial,sans-serif;
    ">
      <div style="display:flex;justify-content:space-between;
                  align-items:center;gap:10px">
        <div>
          <div style="font-size:12px;color:#91a4bc;
                      letter-spacing:2px">WOWY GARAGE</div>
          <div style="font-size:22px;font-weight:bold">
            Vehículo inteligente
          </div>
        </div>
        <div style="background:#29384a;border-radius:20px;
                    padding:8px 12px;font-size:12px">
          SIMULACIÓN 2D
        </div>
      </div>

      <svg viewBox="0 0 440 230" width="100%"
           xmlns="http://www.w3.org/2000/svg"
           style="margin-top:12px">
        <defs>
          <linearGradient id="body" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#55c7e8"/>
            <stop offset="100%" stop-color="#176b9a"/>
          </linearGradient>
          <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#c9f3ff"/>
            <stop offset="100%" stop-color="#426c88"/>
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="5" result="blur"/>
            <feMerge>
              <feMergeNode in="blur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        <ellipse cx="220" cy="185" rx="168" ry="17"
                 fill="#05090f" opacity=".65"/>

        <!-- Carrocería -->
        <path d="M47 150 L58 119 Q65 108 91 103
                 L132 64 Q144 49 167 48
                 L260 48 Q281 51 296 72
                 L329 111 L374 123 Q390 128 392 147
                 L390 165 L48 165 Z"
              fill="url(#body)" stroke="#83ddf4" stroke-width="2"/>

        <!-- Ventanas -->
        <path d="M143 66 L168 57 L207 57 L207 99 L112 99 Z"
              fill="url(#glass)" stroke="#a7e8f8" stroke-width="2"/>
        <path d="M215 57 L258 58 Q272 60 284 79 L300 99 L215 99 Z"
              fill="url(#glass)" stroke="#a7e8f8" stroke-width="2"/>

        <!-- Capó -->
        <path d="M302 106 L350 119 L376 130 L329 131 Z"
              fill="#2388b5" opacity=".9"/>

        <!-- Ruedas -->
        <circle cx="117" cy="160" r="30" fill="#080c12"/>
        <circle cx="117" cy="160" r="17" fill="#8495a7"/>
        <circle cx="117" cy="160" r="8" fill="#263547"/>
        <circle cx="322" cy="160" r="30" fill="#080c12"/>
        <circle cx="322" cy="160" r="17" fill="#8495a7"/>
        <circle cx="322" cy="160" r="8" fill="#263547"/>

        <!-- Puerta animada -->
        <g id="door" style="transform-origin:205px 151px;
             transform:DOOR_TRANSFORM;
             transition:transform .9s cubic-bezier(.2,.8,.2,1)">
          <path d="M135 104 L207 104 L207 151 L135 151 Z"
                fill="#2387b3" stroke="#a2e9fa" stroke-width="2"/>
          <path d="M145 110 L197 110" stroke="#8ddff4"
                stroke-width="2" opacity=".6"/>
          <rect x="181" y="115" width="14" height="3"
                rx="1.5" fill="#d9f8ff"/>
        </g>

        <!-- Faros -->
        <path d="M358 124 L382 132 L381 142 L359 138 Z"
              fill="LIGHT_COLOR" filter="LIGHT_FILTER"/>
        <path d="M59 127 L72 123 L75 133 L59 137 Z"
              fill="#e75b62"/>

        <!-- Luces proyectadas -->
        <path d="M381 132 L423 114 L423 157 L381 139 Z"
              fill="#fff1a0" opacity="LIGHT_OPACITY"/>

        <text x="220" y="218" text-anchor="middle"
              fill="#90a6bf" font-size="11" letter-spacing="3">
          WOWY · SMART MOBILITY
        </text>
      </svg>

      <div style="display:grid;grid-template-columns:1fr 1fr;
                  gap:10px;margin-top:8px">
        <div style="background:#111a26;border-radius:12px;padding:13px">
          <div style="font-size:11px;color:#91a4bc">PUERTA</div>
          <div style="font-weight:bold;color:DOOR_STATUS_COLOR">
            DOOR_STATUS
          </div>
        </div>
        <div style="background:#111a26;border-radius:12px;padding:13px">
          <div style="font-size:11px;color:#91a4bc">ILUMINACIÓN</div>
          <div style="font-weight:bold;color:LIGHT_STATUS_COLOR">
            LIGHT_STATUS
          </div>
        </div>
      </div>
    </div>
    """

    svg = svg.replace("DOOR_TRANSFORM", puerta_transform)
    svg = svg.replace("LIGHT_COLOR", luz_color)
    svg = svg.replace(
        "LIGHT_FILTER",
        "url(#glow)" if luces else "none"
    )
    svg = svg.replace(
        "LIGHT_OPACITY", "0.35" if luces else "0"
    )
    svg = svg.replace(
        "DOOR_STATUS",
        "ABIERTA" if puerta else "CERRADA"
    )
    svg = svg.replace(
        "DOOR_STATUS_COLOR",
        "#55d6a2" if puerta else "#a6b7ca"
    )
    svg = svg.replace(
        "LIGHT_STATUS",
        "ENCENDIDAS" if luces else "APAGADAS"
    )
    svg = svg.replace(
        "LIGHT_STATUS_COLOR",
        "#ffe878" if luces else "#a6b7ca"
    )

    components.html(svg, height=430, scrolling=False)

    st.caption(
        "La animación representa el estado lógico de los controles; "
        "no es una lectura física de los sensores del ESP32."
    )


# --------------------------------------------------
# CONTROLES
# --------------------------------------------------

with col_controls:

    st.subheader("Panel de control")

    st.markdown("**Control por voz**")

    st.write("Presiona el botón y di una de estas órdenes:")
    st.caption(
        "Abre la puerta · Cierra la puerta · "
        "Enciende las luces · Apaga las luces"
    )

    stt_button = Button(
        label="🎙️ Hablar",
        width=250
    )

    stt_button.js_on_event(
        "button_click",
        CustomJS(code="""
            const SpeechRecognition =
                window.SpeechRecognition ||
                window.webkitSpeechRecognition;

            if (!SpeechRecognition) {
                document.dispatchEvent(
                    new CustomEvent("GET_TEXT", {
                        detail: "ERROR_NAVEGADOR"
                    })
                );
            } else {
                const recognition = new SpeechRecognition();
                recognition.lang = "es-CO";
                recognition.continuous = false;
                recognition.interimResults = false;

                recognition.onresult = function(event) {
                    const value =
                        event.results[0][0].transcript;

                    document.dispatchEvent(
                        new CustomEvent("GET_TEXT", {
                            detail: value
                        })
                    );
                };

                recognition.onerror = function() {
                    document.dispatchEvent(
                        new CustomEvent("GET_TEXT", {
                            detail: "ERROR_VOZ"
                        })
                    );
                };

                recognition.start();
            }
        """)
    )

    result = streamlit_bokeh_events(
        stt_button,
        events="GET_TEXT",
        key="listen",
        refresh_on_update=True,
        override_height=75,
        debounce_time=0
    )

    if result and "GET_TEXT" in result:
        texto = result["GET_TEXT"]

        if texto == "ERROR_NAVEGADOR":
            st.error(
                "Tu navegador no admite reconocimiento de voz. "
                "Prueba Chrome o Edge."
            )
        elif texto == "ERROR_VOZ":
            st.warning(
                "No se pudo reconocer la voz. "
                "Verifica el permiso del micrófono e inténtalo de nuevo."
            )
        else:
            st.write(f"Escuché: **{texto}**")
            interpretar_orden(texto)
            st.rerun()

    st.divider()
    st.markdown("**Controles manuales**")

    if st.button("🚪 Abrir puerta", use_container_width=True):
        interpretar_orden("abre la puerta")
        st.rerun()

    if st.button("🚪 Cerrar puerta", use_container_width=True):
        interpretar_orden("cierra la puerta")
        st.rerun()

    if st.button("💡 Encender luces", use_container_width=True):
        interpretar_orden("enciende las luces")
        st.rerun()

    if st.button("🌑 Apagar luces", use_container_width=True):
        interpretar_orden("apaga las luces")
        st.rerun()

    st.divider()

    st.markdown("**Última acción**")
    st.info(st.session_state.ultima_orden)

    st.caption(st.session_state.mensaje_mqtt)


st.divider()
st.caption(
    "WoWy · Interfaces Multimodales · "
    "Streamlit + MQTT + ESP32"
)
