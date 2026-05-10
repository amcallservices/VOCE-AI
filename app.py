import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import io
from concurrent.futures import ThreadPoolExecutor # Per la velocità

# --- 1. CONFIGURAZIONE SICUREZZA ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ Chiave API non trovata nei Secrets!")
    st.stop()

client = OpenAI(api_key=api_key)

# --- 2. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI Podcast Turbo", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button { width: 100%; border-radius: 5px; background-color: #00CC66; color: white; font-weight: bold; }
    .cost-box { padding: 20px; border-radius: 10px; border: 1px solid #ddd; background-color: #fff; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ AI Podcast Factory: Versione Turbo")
st.write("Questa versione processa i capitoli in parallelo per risparmiare tempo.")

# Sidebar
language = st.sidebar.selectbox("Lingua", ["Italiano", "English", "Español", "Français"])
voice = st.sidebar.selectbox("Voce", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])

# --- 3. FUNZIONE DI ELABORAZIONE SINGOLA PARTE ---
def process_chunk(i, chunk, lang, v):
    """Questa funzione gestisce una singola parte del podcast"""
    prompt = f"Sei un podcaster. Adatta questo testo in {lang} in modo colloquiale: {chunk}"
    
    chat_response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": prompt}]
    )
    script = chat_response.choices[0].message.content

    audio_response = client.audio.speech.create(
        model="tts-1",
        voice=v,
        input=script
    )
    return i, audio_response.content

# --- 4. LOGICA PRINCIPALE ---
uploaded_file = st.file_uploader("Carica il PDF", type="pdf")

if uploaded_file is not None:
    # --- NUOVA SEZIONE: CALCOLO COSTI PREVENTIVO ---
    reader = PdfReader(uploaded_file)
    text = " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
    char_count = len(text)
    
    # Stima dei costi (TTS incide per il 95% del costo totale)
    # TTS-1 costa $0.015 ogni 1000 caratteri
    # GPT-4o-mini è quasi trascurabile, aggiungiamo un piccolo margine
    estimated_cost = (char_count / 1000) * 0.016 

    st.markdown(f"""
        <div class="cost-box">
            <h3>📊 Analisi del Documento</h3>
            <p>Caratteri rilevati: <b>{char_count:,}</b></p>
            <p>Costo stimato totale (GPT + Voce): <b>${estimated_cost:.4f} USD</b></p>
            <small><i>*La stima può variare leggermente in base alla lunghezza della traduzione generata.</i></small>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 CONFERMA E GENERA PODCAST"):
        try:
            # B. Divisione in blocchi
            words = text.split()
            chunk_size = 600 
            chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
            
            st.info(f"Avvio elaborazione parallela di {len(chunks)} parti...")
            progress_bar = st.progress(0)
            
            # C. ELABORAZIONE IN PARALLELO
            results = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_chunk, i, chunk, language, voice) for i, chunk in enumerate(chunks)]
                
                for i, future in enumerate(futures):
                    results.append(future.result())
                    progress_bar.progress((i + 1) / len(chunks))

            # D. Riordino
            results.sort(key=lambda x: x[0])
            final_audio = b"".join([r[1] for r in results])

            st.success("🎉 Podcast completato in tempo record!")
            st.audio(final_audio, format="audio/mp3")
            
            # Funzione di download (già presente, resa più evidente)
            st.download_button(
                label="📥 SCARICA IL PODCAST MP3", 
                data=final_audio, 
                file_name="mio_podcast_ai.mp3", 
                mime="audio/mp3"
            )

        except Exception as e:
            st.error(f"Errore: {e}")
