import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import io
from concurrent.futures import ThreadPoolExecutor

# --- 1. CONFIGURAZIONE SICUREZZA ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ Chiave API non trovata! Vai in Settings > Secrets su Streamlit Cloud.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- 2. CONFIGURAZIONE LAYOUT ---
st.set_page_config(page_title="AI Podcast Turbo", page_icon="⚡", layout="wide")

# CSS per nascondere menu e rendere la sidebar più solida + STILE DARK PER COST-BOX
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebar"] { min-width: 350px; }
    .stButton>button { 
        width: 100%; 
        border-radius: 8px; 
        background-color: #00CC66; 
        color: white; 
        font-weight: bold; 
        height: 3.5em;
        border: none;
    }
    .cost-box { 
        padding: 20px; 
        border-radius: 10px; 
        border: 2px solid #00CC66; 
        background-color: #1e1e1e; /* SFONDO DARK */
        color: #ffffff; /* TESTO BIANCO */
    }
    .cost-box h4 {
        color: #00CC66; /* Titolo in verde */
        margin-top: 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR FISSA CON ESEMPI VOCI ---
with st.sidebar:
    st.title("🎙️ Configurazione")
    st.divider()
    
    language = st.selectbox("🌍 Scegli la Lingua", 
                            ["Italiano", "English", "Español", "Français", "Deutsch"])
    
    st.write("---")
    
    voice = st.selectbox("🗣️ Scegli la Voce", 
                         ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
    
    # Anteprime Audio ufficiali OpenAI
    st.write("🎵 Ascolta l'anteprima:")
    voice_urls = {
        "alloy": "https://cdn.openai.com/API/docs/audio/alloy.wav",
        "echo": "https://cdn.openai.com/API/docs/audio/echo.wav",
        "fable": "https://cdn.openai.com/API/docs/audio/fable.wav",
        "onyx": "https://cdn.openai.com/API/docs/audio/onyx.wav",
        "nova": "https://cdn.openai.com/API/docs/audio/nova.wav",
        "shimmer": "https://cdn.openai.com/API/docs/audio/shimmer.wav"
    }
    st.audio(voice_urls[voice], format="audio/wav")
    
    st.divider()
    st.info("Carica un PDF a destra per calcolare i costi.")

# --- 4. FUNZIONE CORE (TURBO) ---
def process_chunk(i, chunk, lang, v):
    # Prompt per traduzione e adattamento
    prompt = f"Sei un podcaster professionista. Traduci e adatta questo testo in {lang} in modo colloquiale: {chunk}"
    
    # 1. GPT-4o-mini (Economico e Veloce)
    chat_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Sei un autore di podcast."},
                  {"role": "user", "content": prompt}]
    )
    script = chat_response.choices[0].message.content

    # 2. TTS (Sintesi Vocale)
    audio_response = client.audio.speech.create(
        model="tts-1",
        voice=v,
        input=script
    )
    return i, audio_response.content

# --- 5. INTERFACCIA PRINCIPALE ---
st.title("⚡ AI di Antonino: Podcast Creator Turbo")
st.write("Trasforma PDF lunghi in audio MP3 in pochi secondi.")

uploaded_file = st.file_uploader("Trascina qui il tuo file PDF", type="pdf")

if uploaded_file:
    # Estrazione testo immediata per preventivo
    reader = PdfReader(uploaded_file)
    full_text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t: full_text += t + " "
    
    char_count = len(full_text)
    
    if char_count > 0:
        # Calcolo costo approssimativo ($0.016 per 1000 char per coprire GPT+TTS)
        costo_stimato = (char_count / 1000) * 0.016
        
        st.markdown(f"""
            <div class="cost-box">
                <h4>📊 Analisi Preventiva</h4>
                <p>Testo rilevato: <b>{char_count:,} caratteri</b></p>
                <p>Costo totale stimato: <b>${costo_stimato:.4f} USD</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 GENERA IL PODCAST ORA"):
            try:
                # Divisione in blocchi da circa 3000 caratteri
                words = full_text.split()
                chunk_size = 500 # parole
                chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
                
                st.info(f"Elaborazione parallela di {len(chunks)} parti in corso...")
                progress_bar = st.progress(0)
                
                results = []
                # Multithreading per velocità Turbo
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(process_chunk, i, chunk, language, voice) for i, chunk in enumerate(chunks)]
                    
                    for i, future in enumerate(futures):
                        results.append(future.result())
                        progress_bar.progress((i + 1) / len(chunks))

                # Riordino e unione dei file audio
                results.sort(key=lambda x: x[0])
                final_audio = b"".join([r[1] for r in results])

                st.success("🎉 Podcast generato con successo!")
                
                # Player e Download
                st.audio(final_audio, format="audio/mp3")
                st.download_button(
                    label="📥 SCARICA IL PODCAST (MP3)",
                    data=final_audio,
                    file_name="podcast_finale.mp3",
                    mime="audio/mp3"
                )

            except Exception as e:
                st.error(f"Si è verificato un errore: {e}")
    else:
        st.warning("Il PDF caricato non contiene testo leggibile.")
