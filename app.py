import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import io
from concurrent.futures import ThreadPoolExecutor

# --- 1. CONFIGURAZIONE SICUREZZA ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ Chiave API non trovata nei Secrets!")
    st.stop()

client = OpenAI(api_key=api_key)

# --- 2. CONFIGURAZIONE PAGINA E CSS ---
st.set_page_config(page_title="AI Podcast Turbo", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    /* Nasconde menu e footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sidebar fissa e pulita */
    [data-testid="stSidebar"] {
        min-width: 350px;
        max-width: 350px;
    }
    
    .stButton>button { 
        width: 100%; 
        border-radius: 5px; 
        background-color: #00CC66; 
        color: white; 
        font-weight: bold; 
        height: 3em;
    }
    
    .cost-box { 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #00CC66; 
        background-color: #f0fff4; 
        margin-bottom: 20px; 
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ AI Podcast Factory: Versione Turbo")
st.write("Processa il testo in parallelo e traduci in varie lingue in tempo record.")

# --- 3. SIDEBAR CON ANTEPRIME VOCI ---
st.sidebar.header("🎙️ Configurazione Podcast")

language = st.sidebar.selectbox("1. Lingua del Podcast", ["Italiano", "English", "Español", "Français", "Deutsch"])

voice = st.sidebar.selectbox("2. Scegli la Voce IA", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])

# Esempi audio ufficiali OpenAI per far scegliere l'utente
st.sidebar.write("🎵 Ascolta l'anteprima della voce:")
voice_samples = {
    "alloy": "https://cdn.openai.com/API/docs/audio/alloy.wav",
    "echo": "https://cdn.openai.com/API/docs/audio/echo.wav",
    "fable": "https://cdn.openai.com/API/docs/audio/fable.wav",
    "onyx": "https://cdn.openai.com/API/docs/audio/onyx.wav",
    "nova": "https://cdn.openai.com/API/docs/audio/nova.wav",
    "shimmer": "https://cdn.openai.com/API/docs/audio/shimmer.wav"
}
st.sidebar.audio(voice_samples[voice], format="audio/wav")

st.sidebar.divider()
st.sidebar.info("Il programma analizzerà il PDF e calcolerà il costo prima di procedere.")

# --- 4. FUNZIONE DI ELABORAZIONE ---
def process_chunk(i, chunk, lang, v):
    """Gestisce una singola parte del podcast"""
    prompt = f"Sei un podcaster professionista. Traduci e adatta questo testo in {lang} in modo molto colloquiale e fluido: {chunk}"
    
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

# --- 5. LOGICA PRINCIPALE ---
uploaded_file = st.file_uploader("Carica il tuo PDF qui", type="pdf")

if uploaded_file is not None:
    # Lettura e analisi immediata
    reader = PdfReader(uploaded_file)
    text = " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
    char_count = len(text)
    
    # Calcolo preventivo costi
    # TTS-1 = $0.015/1k char | GPT-4o-mini = trascurabile. Usiamo 0.016 per sicurezza.
    estimated_cost = (char_count / 1000) * 0.016 

    st.markdown(f"""
        <div class="cost-box">
            <h3>📊 Analisi Preventiva</h3>
            <p>Caratteri totali nel PDF: <b>{char_count:,}</b></p>
            <p>Costo stimato dell'operazione: <b>${estimated_cost:.4f} USD</b></p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 CONFERMA E GENERA PODCAST"):
        try:
            # Divisione in blocchi
            words = text.split()
            chunk_size = 600 
            chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
            
            st.info(f"⚡ Turbo Mode attiva: Elaborazione di {len(chunks)} parti in parallelo...")
            progress_bar = st.progress(0)
            
            results = []
            # Utilizzo di 5 thread paralleli per massima velocità
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_chunk, i, chunk, language, voice) for i, chunk in enumerate(chunks)]
                
                for i, future in enumerate(futures):
                    results.append(future.result())
                    progress_bar.progress((i + 1) / len(chunks))

            # Riordino dei pezzi e unione
            results.sort(key=lambda x: x[0])
            final_audio = b"".join([r[1] for r in results])

            st.success("🎉 Podcast generato con successo!")
            
            # Anteprima e Download
            st.audio(final_audio, format="audio/mp3")
            
            st.download_button(
                label="📥 SCARICA IL PODCAST COMPLETO (MP3)", 
                data=final_audio, 
                file_name="podcast_antonino.mp3", 
                mime="audio/mp3"
            )

        except Exception as e:
            st.error(f"Errore durante la generazione: {e}")
