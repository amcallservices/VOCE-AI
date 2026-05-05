import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import io

# --- CONFIGURAZIONE ---
# Inserisci qui la tua API Key
OPENAI_API_KEY = "IL_TUO_CODICE_API_QUI_OPENAI" 

client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="AI Podcast Pro", page_icon="🎙️")
st.title("🎙️ PDF to Podcast Generator (Long Version)")

# Selezione Lingua e Voce
col1, col2 = st.columns(2)
with col1:
    language = st.selectbox("Lingua Podcast", ["Italiano", "English", "Español", "Français", "Deutsch"])
with col2:
    voice = st.selectbox("Voce IA", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])

# Funzione per dividere il testo in blocchi
def split_text(text, max_chars=3000):
    chunks = []
    while len(text) > max_chars:
        # Trova l'ultimo spazio utile per non tagliare una parola a metà
        split_index = text.rfind(' ', 0, max_chars)
        if split_index == -1: split_index = max_chars
        chunks.append(text[:split_index])
        text = text[split_index:].strip()
    chunks.append(text)
    return chunks

uploaded_file = st.file_uploader("Carica il PDF", type="pdf")

if uploaded_file is not None:
    if st.button("Genera Podcast Completo"):
        # 1. Lettura PDF
        reader = PdfReader(uploaded_file)
        full_text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                full_text += content + " "
        
        # 2. Divisione in capitoli/blocchi
        text_chunks = split_text(full_text)
        st.info(f"Il documento è stato diviso in {len(text_chunks)} parti per l'elaborazione.")
        
        combined_audio_bytes = b"" # Buffer per unire l'audio
        
        progress_bar = st.progress(0)
        
        for i, chunk in enumerate(text_chunks):
            st.write(f"Elaborazione parte {i+1} di {len(text_chunks)}...")
            
            # 3. Traduzione e Adattamento Podcast via GPT
            prompt = f"""
            Sei un autore di podcast. Traduci e rielabora questo testo in {language}. 
            Rendilo parlato, elimina riferimenti a tabelle o numeri di pagina. 
            Deve sembrare un discorso fluido.
            Testo: {chunk}
            """
            
            chat_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Sei un esperto podcaster."},
                          {"role": "user", "content": prompt}]
            )
            script_chunk = chat_response.choices[0].message.content
            
            # 4. Generazione Audio (TTS)
            # Nota: OpenAI TTS ha un limite di 4096 caratteri per richiesta
            audio_response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=script_chunk
            )
            
            # Aggiungiamo i bytes di questa parte al file finale
            combined_audio_bytes += audio_response.content
            
            # Aggiorna progresso
            progress_bar.progress((i + 1) / len(text_chunks))

        # Risultato Finale
        st.success("Tutte le parti sono state elaborate e unite!")
        
        # Player unico
        st.audio(combined_audio_bytes, format="audio/mp3")
        
        # Download unico
        st.download_button(
            label="Scarica Podcast Completo (MP3)",
            data=combined_audio_bytes,
            file_name="podcast_completo.mp3",
            mime="audio/mp3"
        )
