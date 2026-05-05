import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import io

# --- 1. CONFIGURAZIONE SICUREZZA ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("⚠️ Chiave API non trovata! Vai nelle impostazioni di Streamlit Cloud (Settings > Secrets) e aggiungi OPENAI_API_KEY.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- 2. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI Podcast Factory", page_icon="🎙️", layout="wide")

# CSS personalizzato per nascondere il menu, il footer e stilizzare l'app
st.markdown("""
    <style>
    /* Nasconde il menu in alto a destra e il footer 'Made with Streamlit' */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .main { background-color: #f5f7f9; }
    .stButton>button { 
        width: 100%; 
        border-radius: 5px; 
        height: 3em; 
        background-color: #FF4B4B; 
        color: white; 
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ AI di Antonino: Podcast Creator")
st.write("Trasforma i tuoi PDF in podcast professionali multilingua.")

# Sidebar per opzioni
st.sidebar.header("Impostazioni Podcast")
language = st.sidebar.selectbox("Lingua del Podcast", ["Italiano", "English", "Español", "Français", "Deutsch", "Português"])
voice = st.sidebar.selectbox("Scegli la Voce IA", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
st.sidebar.info("Nota: Le voci 'onyx' e 'echo' sono più maschili, 'nova' e 'shimmer' più femminili.")

# --- 3. FUNZIONI TECNICHE ---

def get_text_chunks(text, chunk_size=3500):
    """Divide il testo in blocchi per non superare i limiti di OpenAI TTS e GPT."""
    chunks = []
    while len(text) > 0:
        if len(text) <= chunk_size:
            chunks.append(text)
            break
        stop_index = text.rfind('.', 0, chunk_size)
        if stop_index == -1: stop_index = chunk_size
        chunks.append(text[:stop_index + 1])
        text = text[stop_index + 1:].strip()
    return chunks

# --- 4. INTERFACCIA DI CARICAMENTO ---
uploaded_file = st.file_uploader("Carica il tuo file PDF", type="pdf")

if uploaded_file is not None:
    if st.button("🚀 GENERA PODCAST COMPLETO"):
        try:
            with st.status("Elaborazione in corso...", expanded=True) as status:
                # A. Estrazione Testo
                st.write("📖 Lettura del PDF...")
                reader = PdfReader(uploaded_file)
                full_text = ""
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        full_text += content + " "
                
                if not full_text.strip():
                    st.error("Il PDF non contiene testo leggibile.")
                    st.stop()

                # B. Divisione in blocchi
                chunks = get_text_chunks(full_text)
                st.write(f"📦 Il testo è stato diviso in {len(chunks)} capitoli.")
                
                final_audio = b""
                progress_bar = st.progress(0)

                # C. Loop di elaborazione
                for i, chunk in enumerate(chunks):
                    st.write(f"⏳ Elaborazione parte {i+1} di {len(chunks)}...")
                    
                    # 1. Traduzione e Adattamento Podcast (GPT-4o)
                    prompt = f"""
                    Sei un conduttore di podcast esperto. Traduci e rielabora il seguente testo in {language}. 
                    Rendilo colloquiale, coinvolgente e facile da ascoltare. 
                    Elimina numeri di pagina, citazioni bibliografiche noiose o tabelle. 
                    Parla direttamente all'ascoltatore.
                    Testo da elaborare: {chunk}
                    """
                    
                    chat_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Sei un autore di podcast di successo."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    podcast_script = chat_response.choices[0].message.content

                    # 2. Generazione Audio (TTS)
                    audio_response = client.audio.speech.create(
                        model="tts-1",
                        voice=voice,
                        input=podcast_script
                    )
                    
                    # Accumulo dei pezzi audio
                    final_audio += audio_response.content
                    progress_bar.progress((i + 1) / len(chunks))

                status.update(label="✅ Podcast Generato!", state="complete", expanded=False)

            # --- 5. RISULTATO FINALE ---
            st.success("🎉 Il tuo podcast è pronto per l'ascolto!")
            
            # Player Audio
            st.audio(final_audio, format="audio/mp3")
            
            # Bottone di Download (Sempre visibile dopo la generazione)
            st.download_button(
                label="📥 SCARICA IL PODCAST (MP3)",
                data=final_audio,
                file_name="mio_podcast_ai.mp3",
                mime="audio/mp3"
            )

        except Exception as e:
            st.error(f"Si è verificato un errore: {e}")
            st.info("Consiglio: Controlla che la tua API Key abbia credito sufficiente su OpenAI.")
