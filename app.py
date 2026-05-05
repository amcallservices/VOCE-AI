import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import io

# --- CONFIGURAZIONE CHIAVE ---
# Opzione A (Più sicura): Usa i Secrets di Streamlit Cloud
# Opzione B (Veloce): Inserisci la stringa direttamente qui
api_key = "INSERISCI_QUI_LA_TUA_CHIAVE_SK_..." 

# Inizializzazione Client
client = OpenAI(api_key=api_key)

st.set_page_config(page_title="AI Podcast Factory", page_icon="🎙️")
st.title("🎙️ PDF to Podcast Generator")

# Selezione lingua e voce
col1, col2 = st.columns(2)
with col1:
    language = st.selectbox("Lingua", ["Italiano", "English", "Español", "Français"])
with col2:
    voice = st.selectbox("Voce", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])

# Funzione per dividere il testo in modo intelligente (evita di tagliare frasi)
def get_text_chunks(text, chunk_size=3000):
    chunks = []
    while len(text) > 0:
        if len(text) <= chunk_size:
            chunks.append(text)
            break
        # Cerca l'ultimo punto per non interrompere una frase
        stop_index = text.rfind('.', 0, chunk_size)
        if stop_index == -1: stop_index = chunk_size
        chunks.append(text[:stop_index + 1])
        text = text[stop_index + 1:].strip()
    return chunks

uploaded_file = st.file_uploader("Carica il PDF", type="pdf")

if uploaded_file and st.button("Avvia Generazione"):
    try:
        # 1. Estrazione Testo
        reader = PdfReader(uploaded_file)
        full_text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
        
        if not full_text.strip():
            st.error("Il PDF sembra vuoto o non leggibile.")
            st.stop()

        # 2. Divisione in capitoli
        chunks = get_text_chunks(full_text)
        st.info(f"Testo diviso in {len(chunks)} parti.")
        
        full_audio = b""
        progress_bar = st.progress(0)

        for i, chunk in enumerate(chunks):
            st.write(f"Elaborazione parte {i+1}...")
            
            # 3. Trasformazione in Podcast (GPT-4o)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"Sei un podcaster professionista. Riassumi e adatta il testo in {language} in modo colloquiale."},
                    {"role": "user", "content": chunk}
                ]
            )
            script = response.choices[0].message.content

            # 4. Sintesi Vocale (TTS)
            audio_part = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=script
            )
            full_audio += audio_part.content
            progress_bar.progress((i + 1) / len(chunks))

        # 5. Output Finale
        st.success("Podcast pronto!")
        st.audio(full_audio, format="audio/mp3")
        st.download_button("Scarica Podcast MP3", full_audio, "podcast.mp3", "audio/mp3")

    except Exception as e:
        st.error(f"Errore critico: {e}")
        st.info("Verifica che la tua API Key sia corretta e che il tuo account OpenAI abbia credito.")
