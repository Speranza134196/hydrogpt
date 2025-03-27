import streamlit as st
import openai
import math
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# CONFIGURAZIONE
st.set_page_config(page_title="HydroGPT", page_icon="💧")
st.title("💧 HydroGPT – Assistente per l'efficienza idrica ed energetica")

# API KEY (richiesta input da utente o da variabile ambiente)
openai.api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else st.text_input("Inserisci la tua OpenAI API Key", type="password")

# SIDEBAR DATI INGEGNERISTICI
st.sidebar.header("📊 Inserisci i dati dell'impianto")
portata = st.sidebar.number_input("Portata media (l/s)", min_value=0.0, value=50.0)
salto = st.sidebar.number_input("Salto idraulico disponibile (m)", min_value=0.0, value=80.0)
perdite = st.sidebar.slider("% Perdite nella rete", 0, 100, 18)
piezometrico = st.sidebar.number_input("Cielo piezometrico attuale (m)", min_value=0.0, value=120.0)

# CARICAMENTO FILE EXCEL
st.sidebar.markdown("---")
st.sidebar.subheader("📂 Carica un file Excel (opzionale)")
uploaded_file = st.sidebar.file_uploader("File Excel con dati impianto", type=["xls", "xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("📄 Dati caricati da file Excel")
    st.write(df)

# CALCOLO ENERGETICO BASE
def calcola_potenza(portata_l_s, salto_m, rendimento=0.7):
    portata_m3_s = portata_l_s / 1000
    g = 9.81
    densita = 1000  # kg/m3
    potenza = portata_m3_s * salto_m * g * densita * rendimento
    return potenza / 1000  # kW

potenza_base = calcola_potenza(portata, salto * (1 - perdite / 100))

# GRAFICO EFFICIENZA
st.subheader("📈 Curva salto vs potenza stimata")
salti = list(range(10, 151, 10))
potenze = [calcola_potenza(portata, s * (1 - perdite / 100)) for s in salti]
fig, ax = plt.subplots()
ax.plot(salti, potenze, marker='o')
ax.set_xlabel("Salto idraulico (m)")
ax.set_ylabel("Potenza stimata (kW)")
ax.set_title("Curva di efficienza dell'impianto")
st.pyplot(fig)

# CONVERSAZIONE
st.subheader("💬 Chat con HydroGPT")

if "history" not in st.session_state:
    st.session_state.history = []

user_input = st.text_input("Scrivi una domanda o chiedi una simulazione...")

if user_input:
    context = """
    Sei HydroGPT, un assistente tecnico intelligente per l’efficienza idrica.
    Aiuti gli utenti a ridurre le perdite nei sistemi idrici, ottimizzare la produzione idroelettrica
    tramite l’analisi di portata, salto idrico e cielo piezometrico.
    Dai suggerimenti anche sul tipo di turbina e sulle soluzioni più adatte in acquedotto.

    Dati impianto:
    - Portata media: {:.1f} l/s
    - Salto idraulico disponibile: {:.1f} m
    - Perdite rete: {}%
    - Cielo piezometrico attuale: {:.1f} m
    - Potenza stimata: {:.2f} kW

    Rispondi in modo tecnico ma comprensibile, in italiano.
    """.format(portata, salto, perdite, piezometrico, potenza_base)

    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": user_input},
    ]

    with st.spinner("HydroGPT sta analizzando i dati..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages
            )
            reply = response.choices[0].message.content
            st.session_state.history.append((user_input, reply))
        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {e}")

# STAMPA CONVERSAZIONE
for user_msg, bot_reply in reversed(st.session_state.history):
    st.markdown(f"**Tu:** {user_msg}")
    st.markdown(f"**HydroGPT:** {bot_reply}")

# GENERA REPORT PDF
st.subheader("📄 Genera report PDF")
if st.button("Crea report"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Report tecnico HydroGPT", ln=True, align="C")
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=f"Portata media: {portata} l/s\nSalto disponibile: {salto} m\nPerdite: {perdite}%\nCielo piezometrico: {piezometrico} m\nPotenza stimata: {potenza_base:.2f} kW")
    if st.session_state.history:
        pdf.ln(10)
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, txt="Conversazione con HydroGPT", ln=True)
        pdf.set_font("Arial", size=11)
        for user_msg, bot_reply in st.session_state.history:
            pdf.multi_cell(0, 10, txt=f"Tu: {user_msg}\nHydroGPT: {bot_reply}\n")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        pdf.output(tmpfile.name)
        st.download_button(label="📥 Scarica il report PDF", file_name="hydrogpt_report.pdf", mime="application/pdf", data=open(tmpfile.name, "rb").read())
