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
    # 1. Traduzione/Script (Uso gpt-4o-mini per velocità e risparmio)
    prompt = f"Sei un podcaster. Adatta questo testo in {lang} in modo colloquiale: {chunk}"
    
    chat_response = client.chat.completions.create(
        model="gpt-4o-mini", # Più veloce!
        messages=[{"role": "user", "content": prompt}]
    )
    script = chat_response.choices[0].message.content

    # 2. Sintesi Vocale
    audio_response = client.audio.speech.create(
        model="tts-1",
        voice=v,
        input=script
    )
    return i, audio_response.content

# --- 4. LOGICA PRINCIPALE ---
uploaded_file = st.file_uploader("Carica il PDF", type="pdf")

if uploaded_file is not None:
    if st.button("🚀 GENERA PODCAST TURBO"):
        try:
            # A. Estrazione Testo
            reader = PdfReader(uploaded_file)
            text = " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
            
            # B. Divisione in blocchi (aumentiamo un po' la dimensione per meno chiamate)
            words = text.split()
            chunk_size = 600 # Circa 600 parole per blocco
            chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
            
            st.info(f"Avvio elaborazione parallela di {len(chunks)} parti...")
            progress_bar = st.progress(0)
            
            # C. ELABORAZIONE IN PARALLELO (Il segreto della velocità)
            results = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Lanciamo tutte le richieste insieme
                futures = [executor.submit(process_chunk, i, chunk, language, voice) for i, chunk in enumerate(chunks)]
                
                for i, future in enumerate(futures):
                    results.append(future.result())
                    progress_bar.progress((i + 1) / len(chunks))

            # D. Riordino (fondamentale perché il parallelo potrebbe finire in ordine sparso)
            results.sort(key=lambda x: x[0])
            final_audio = b"".join([r[1] for r in results])

            st.success("🎉 Podcast completato in tempo record!")
            st.audio(final_audio, format="audio/mp3")
            st.download_button("📥 SCARICA MP3", final_audio, "podcast_turbo.mp3", "audio/mp3")

        except Exception as e:
            st.error(f"Errore: {e}")
