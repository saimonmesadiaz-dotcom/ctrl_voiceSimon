import json
import re
import unicodedata
import uuid

import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
from bokeh.models import Button, CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events


# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="WoWy | Garage Control",
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
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# MQTT
# ============================================================
def get_mqtt_client():
    client = st.session_state.mqtt_client
    if client is not None and client.is_connected():
        return client

    try:
        # Compatible con paho-mqtt 2.x
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id="WoWy_" + uuid.uuid4().hex[:8],
            protocol=mqtt.MQTTv311,
        )
        client.connect(BROKER, PORT, keepalive=45)
        client.loop_start()
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
