import streamlit as tf
import openai
import replicate
import os

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Comic AI Creator", page_icon="🎨", layout="wide")

# --- GESTIONE CHIAVI API ---
# Streamlit Secrets legge le chiavi quando l'app è online. 
# In locale, puoi usare un file .env o impostarle nell'ambiente.
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    openai.api_key = os.getenv("OPENAI_API_KEY")

if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")


st.title("🎨 Comic AI Creator")
st.subtitle("Crea la tua tavola a fumetti usando GPT-4o-Mini e Replicate")

# --- SIDEBAR (INPUT UTENTE) ---
st.sidebar.header("Configura il tuo Fumetto")

# Tipo di fumetto (Stile)
stile_fumetto = st.sidebar.selectbox(
    "Che tipo/stile di fumetto vuoi?",
    ["Graphic Novel Americana", "Manga Giapponese", "Fumetto Bonelli (Dylan Dog/Tex)", "Comic Book Classico", "Cartoon / Disney Style", "Cyberpunk / Sci-Fi Dark"]
)

# Numero di vignette
num_vignette = st.sidebar.slider("Numero di vignette (pannelli)", min_value=2, max_value=5, value=3)

# Trama principale
trama = st.sidebar.text_area(
    "Inserisci la trama o l'idea principale:",
    placeholder="Un detective privato scopre che la sua ombra ha iniziato a vivere di vita propria..."
)

# Pulsante di avvio
generate_button = st.sidebar.button("✨ Genera Fumetto")

# --- LOGICA DI GENERAZIONE ---
if generate_button:
    if not openai.api_key or not os.environ.get("REPLICATE_API_TOKEN"):
        st.error("⚠️ Errore: Assicurati di aver configurato correttamente le API Key di OpenAI e Replicate nei Secrets di Streamlit!")
    elif not trama.strip():
        st.warning("✍️ Per favore, inserisci una trama prima di iniziare.")
    else:
        with st.spinner("🧠 GPT-4o-Mini sta scrivendo la sceneggiatura e i prompt delle vignette..."):
            try:
                # Creiamo il prompt per GPT-4o-Mini per ottenere i prompt visivi delle vignette
                system_prompt = (
                    "Sei un esperto sceneggiatore di fumetti. Il tuo compito è suddividere la trama dell'utente "
                    f"in esattamente {num_vignette} vignette sequenziali. Per ogni vignetta devi fornire: \n"
                    "1. Il testo del dialogo o la didascalia.\n"
                    f"2. Un prompt d'immagine dettagliato in INGLESE ottimizzato per la generazione AI, mantenendo lo stile richiesto: {stile_fumetto}. "
                    "Assicurati che ci sia coerenza visiva dei personaggi tra le vignette.\n"
                    "Rispondi formattando l'output esattamente in questo modo per ogni vignetta, separando i dati con '|':\n"
                    "Vignetta X | Testo del dialogo | Prompt per l'immagine"
                )

                # Chiamata a GPT-4o-Mini (Nome del modello ufficiale: gpt-4o-mini)
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Trama: {trama}"}
                    ],
                    temperature=0.7
                )
                
                sceneggiatura = response.choices[0].message.content
                
                # Parsing della risposta (dividiamo per righe)
                righe = [line.strip() for line in sceneggiatura.split("\n") if "|" in line]
                
            except Exception as e:
                st.error(f"Errore durante la generazione del testo con OpenAI: {e}")
                righe = []

        if righe:
            st.success("📝 Sceneggiatura pronta! Ora inizio a disegnare le vignette...")
            
            # Iteriamo sulle vignette generate per mandarle a Replicate
            for riga in righe:
                try:
                    # Dividiamo i dati estratti da GPT
                    parti = riga.split("|")
                    titolo_vignetta = parti[0].strip()
                    dialogo = parti[1].strip()
                    image_prompt = parti[2].strip()
                    
                    st.write(f"### {titolo_vignetta}")
                    st.info(f"💬 **Dialogo/Didascalia:** {dialogo}")
                    
                    with st.spinner(f"🎨 Replicate sta disegnando la {titolo_vignetta.lower()}..."):
                        # Usiamo Flux-Schnell (o SDXL) su Replicate. È velocissimo e di altissima qualità.
                        # Modello: stability-ai/sdxl o black-forest-labs/flux-schnell
                        output = replicate.run(
                            "black-forest-labs/flux-schnell",
                            input={
                                "prompt": f"{image_prompt}, comic book style, {stile_fumetto}, high quality, detailed",
                                "aspect_ratio": "4:3",
                                "num_outputs": 1
                            }
                        )
                        
                        # Replicate restituisce una lista di URL
                        image_url = output[0]
                        
                        # Mostriamo l'immagine risultante
                        st.image(image_url, caption=f"Scena: {dialogo}", use_container_width=True)
                        st.markdown("---")
                        
                except Exception as e:
                    st.error(f"Errore nella generazione dell'immagine per questa vignetta: {e}")
                    st.markdown("---")
            
            st.balloons()
            st.success("🎉 Il tuo fumetto è pronto!")
