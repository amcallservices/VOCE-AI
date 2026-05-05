import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import io

# Configurazione Pagina
st.set_page_config(page_title="AI Podcast Generator", page_icon="🎙️")
st.title("🎙️ PDF to Podcast Generator")
st.subheader("Trasforma i tuoi documenti in audio multilingua")

# Inserimento API Key (Sicurezza)
api_key = st.sidebar.text_input("Inserisci la tua OpenAI API Key", type="password")

if api_key:
    client = OpenAI(api_key=api_key)
else:
    st.warning("Per favore, inserisci la tua OpenAI API Key nella barra laterale.")
    st.stop()

# Selezione Lingua
language = st.selectbox("In quale lingua vuoi il podcast?", 
                        ["Italiano", "English", "Español", "Français", "Deutsch"])

# Selezione Voce
voice = st.selectbox("Scegli la voce dell'IA", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])

# Caricamento PDF
uploaded_file = st.file_uploader("Carica il tuo file PDF", type="pdf")

if uploaded_file is not None:
    if st.button("Genera Podcast"):
        with st.spinner("Estrazione testo e generazione audio in corso..."):
            
            # 1. Estrazione Testo
            reader = PdfReader(uploaded_file)
            raw_text = ""
            for page in reader.pages:
                raw_text += page.extract_text()
            
            # Limitiamo il testo per non consumare troppi token in un colpo solo (opzionale)
            input_text = raw_text[:4000] 

            # 2. Traduzione e Adattamento (Prompt)
            prompt = f"""
            Agisci come un podcaster professionista. Traduci e rielabora il seguente testo in {language}.
            Rendilo scorrevole, colloquiale e adatto ad essere ascoltato. 
            Testo: {input_text}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            podcast_script = response.choices[0].message.content

            # 3. Generazione Audio (TTS)
            audio_response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=podcast_script
            )
            
            # Salvataggio in un buffer per lo streaming
            audio_data = io.BytesIO(audio_response.content)

            st.success("Podcast generato con successo!")
            
            # Player Audio
            st.audio(audio_data, format="audio/mp3")
            
            # Download button
            st.download_button(
                label="Scarica Podcast (MP3)",
                data=audio_response.content,
                file_name="podcast.mp3",
                mime="audio/mp3"
            )
