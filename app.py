import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 1. CONFIGURAZIONE SICUREZZA ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ Chiave API non trovata! Vai in Settings > Secrets su Streamlit Cloud.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- 2. CONFIGURAZIONE LAYOUT ---
st.set_page_config(page_title="AI Podcast Turbo", page_icon="⚡", layout="wide")

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
        color: #00CC66; 
        margin-top: 0;
    }
    .part-container {
        padding: 10px;
        border-bottom: 1px solid #444;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🎙️ Configurazione")
    st.divider()
    language = st.selectbox("🌍 Scegli la Lingua", ["Italiano", "English", "Español", "Français", "Deutsch"])
    st.write("---")
    voice = st.selectbox("🗣️ Scegli la Voce", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
    
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

# --- 4. FUNZIONE CORE ---
def process_chunk(i, chunk, lang, v):
    prompt = f"Sei un podcaster professionista. Traduci e adatta questo testo in {lang} in modo colloquiale: {chunk}"
    chat_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Sei un autore di podcast."},
                  {"role": "user", "content": prompt}]
    )
    script = chat_response.choices[0].message.content
    audio_response = client.audio.speech.create(
        model="tts-1",
        voice=v,
        input=script
    )
    return i, audio_response.content

# --- 5. INTERFACCIA PRINCIPALE ---
st.title("⚡ AI di Antonino: Podcast Creator Turbo")
st.write("Scarica le singole parti in tempo reale o l'intero file alla fine.")

uploaded_file = st.file_uploader("Trascina qui il tuo file PDF", type="pdf")

if uploaded_file:
    reader = PdfReader(uploaded_file)
    full_text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t: full_text += t + " "
    
    char_count = len(full_text)
    
    if char_count > 0:
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
                words = full_text.split()
                chunk_size = 500
                chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
                
                st.info(f"Elaborazione di {len(chunks)} parti in corso...")
                progress_bar = st.progress(0)
                
                # Container per le singole parti scaricabili
                st.subheader("📦 Parti elaborate in tempo reale")
                parts_container = st.container()
                
                results_map = {}
                processed_count = 0
                
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = {executor.submit(process_chunk, i, chunk, language, voice): i for i, chunk in enumerate(chunks)}
                    
                    for future in as_completed(futures):
                        idx, audio_content = future.result()
                        results_map[idx] = audio_content
                        processed_count += 1
                        
                        # Aggiorna UI per la singola parte
                        with parts_container:
                            with st.expander(f"✅ Parte {idx + 1} Pronta", expanded=False):
                                st.audio(audio_content, format="audio/mp3")
                                st.download_button(
                                    label=f"📥 Scarica Parte {idx + 1}",
                                    data=audio_content,
                                    file_name=f"parte_{idx + 1}.mp3",
                                    mime="audio/mp3",
                                    key=f"btn_{idx}"
                                )
                        
                        progress_bar.progress(processed_count / len(chunks))

                # Riordino per il file finale
                sorted_indices = sorted(results_map.keys())
                final_audio = b"".join([results_map[i] for i in sorted_indices])

                st.divider()
                st.success("🎉 PODCAST COMPLETO GENERATO!")
                st.audio(final_audio, format="audio/mp3")
                st.download_button(
                    label="🔥 SCARICA PODCAST COMPLETO (UNICO FILE)",
                    data=final_audio,
                    file_name="podcast_completo.mp3",
                    mime="audio/mp3",
                    key="final_full_btn"
                )

            except Exception as e:
                st.error(f"Si è verificato un errore: {e}")
    else:
        st.warning("Il PDF caricato non contiene testo leggibile.")
