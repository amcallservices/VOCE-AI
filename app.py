import streamlit as st  
import openai
import replicate
import os

# Configurazione della pagina Streamlit (Deve essere il PRIMO comando Streamlit della pagina)
st.set_page_config(page_title="Comic AI Creator - Book Edition", page_icon="🎨", layout="wide")

# --- GESTIONE CHIAVI API ---
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    openai.api_key = os.getenv("OPENAI_API_KEY")

if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")


st.title("🎨 Comic AI Creator - Book Edition")
st.markdown("### Crea il tuo libro a fumetti completo mantenendo la coerenza dei personaggi")

# --- SIDEBAR (INPUT UTENTE) ---
st.sidebar.header("📚 Configura il tuo Libro")

# Tipo di fumetto (Stile)
stile_fumetto = st.sidebar.selectbox(
    "Che tipo/stile di fumetto vuoi?",
    ["Graphic Novel Americana", "Manga Giapponese", "Fumetto Bonelli (Dylan Dog/Tex)", "Comic Book Classico", "Cartoon / Disney Style", "Cyberpunk / Sci-Fi Dark"]
)

# Numero di vignette esteso per creare un libro/capitolo
num_vignette = st.sidebar.slider("Numero di vignette (pannelli del libro)", min_value=3, max_value=30, value=10, step=1)

# Trama principale
trama = st.sidebar.text_area(
    "Inserisci la trama completa del tuo libro:",
    placeholder="Un detective privato scopre che la sua ombra ha iniziato a vivere di vita propria...",
    height=150
)

# Pulsante di avvio
generate_button = st.sidebar.button("✨ Genera Libro a Fumetti")

# --- LOGICA DI GENERAZIONE ---
if generate_button:
    if not openai.api_key or not os.environ.get("REPLICATE_API_TOKEN"):
        st.error("⚠️ Errore: Assicurati di aver configurato correttamente le API Key di OpenAI e Replicate nei Secrets di Streamlit!")
    elif not trama.strip():
        st.warning("✍️ Per favore, inserisci una trama prima di iniziare.")
    else:
        client = openai.OpenAI()
        
        # FASE 1: Creazione dei fogli modello dei personaggi per mantenere la coerenza visiva
        with st.spinner("🧠 Fase 1: GPT-4o-Mini sta estraendo i personaggi e creando le linee guida per la coerenza visiva..."):
            try:
                character_prompt = (
                    "Analizza la seguente trama e identifica i personaggi principali. "
                    "Crea una descrizione fisica dettagliata in INGLESE per ognuno di essi (es. genere, età apparente, vestiti fissi, capelli, espressione tipica). "
                    "Queste descrizioni verranno usate como prompt per un'IA generativa di immagini, quindi sii visivo, chiaro e conciso. "
                    "Rispondi SOLTANTO con le descrizioni dei personaggi accumulate in un unico paragrafo compatto."
                )
                
                char_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": character_prompt},
                        {"role": "user", "content": f"Trama: {trama}"}
                    ],
                    temperature=0.5
                )
                personaggi_coerenza = char_response.choices[0].message.content
                st.sidebar.success("✅ Coerenza Personaggi Attivata!")
                with st.sidebar.expander("Visualizza Modello Personaggi (AI)"):
                    st.write(personaggi_coerenza)
                    
            except Exception as e:
                st.error(f"Errore nella generazione dei personaggi: {e}")
                personaggi_coerenza = ""

        # FASE 2: Generazione dello storyboard completo
        with st.spinner(f"📖 Fase 2: Generazione della sceneggiatura estesa in {num_vignette} vignette..."):
            try:
                system_prompt = (
                    "Sei un esperto sceneggiatore e regista di fumetti. Il tuo compito è suddividere la trama dell'utente "
                    f"in esattamente {num_vignette} vignette sequenziali per comporre un libro/capitolo completo. "
                    "La progressione deve coprire l'intera storia dall'inizio alla fine in modo fluido.\n\n"
                    "Per ogni vignetta devi fornire tassativamente:\n"
                    "1. Il testo del dialogo o la didascalia narrativa (in italiano).\n"
                    "2. Un prompt d'immagine d'azione dettagliato in INGLESE focalizzato sull'ambiente e sui movimenti.\n\n"
                    "Rispondi formattando l'output esattamente in questo modo per ogni singola riga, separando i campi con il carattere '|':\n"
                    "Vignetta X | Testo del dialogo o didascalia | Prompt d'azione per l'immagine\n"
                    "Non aggiungere introduzioni o altre parole, scrivi solo le righe formattate con '|'."
                )

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Trama: {trama}"}
                    ],
                    temperature=0.7
                )
                
                sceneggiatura = response.choices[0].message.content
                righe = [line.strip() for line in sceneggiatura.split("\n") if "|" in line]
                
            except Exception as e:
                st.error(f"Errore durante la generazione della sceneggiatura: {e}")
                righe = []

        # FASE 3: Generazione delle immagini e rendering del libro
        if righe:
            st.success(f"📝 Sceneggiatura di {len(righe)} vignette pronta! Inizio il disegno del libro...")
            
            for riga in righe:
                try:
                    parti = riga.split("|")
                    if len(parti) < 3:
                        continue
                        
                    titolo_vignetta = parti[0].strip()
                    dialogo = parti[1].strip()
                    action_prompt = parti[2].strip()
                    
                    st.write(f"### 📖 {titolo_vignetta}")
                    st.info(f"💬 **Testo/Didascalia:** {dialogo}")
                    
                    with st.spinner(f"🎨 Disegno in corso per {titolo_vignetta.lower()}..."):
                        # Uniamo le caratteristiche fisse dei personaggi con l'azione specifica della vignetta e lo stile scelto
                        prompt_finale = (
                            f"{action_prompt}. Character appearance guidelines: {personaggi_coerenza}. "
                            f"Comic book panel, style: {stile_fumetto}, highly detailed, sequential art, crisp lines."
                        )
                        
                        output = replicate.run(
                            "black-forest-labs/flux-schnell",
                            input={
                                "prompt": prompt_finale,
                                "aspect_ratio": "4:3",
                                "num_outputs": 1
                            }
                        )
                        
                        # FIX: Gestione del nuovo formato FileOutput / Liste di Replicate
                        # Se è una lista di oggetti FileOutput, prendiamo il primo e lo convertiamo in stringa (URL)
                        if isinstance(output, list):
                            image_url = str(output[0])
                        else:
                            image_url = str(output)
                        
                        st.image(image_url, caption=f"{titolo_vignetta} - {dialogo}", use_container_width=True)
                        st.markdown("---")
                        
                except Exception as e:
                    st.error(f"Errore nella generazione dell'immagine per questa vignetta: {e}")
                    st.markdown("---")
            
            st.balloons()
            st.success("🎉 Il tuo libro a fumetti è stato completato con successo!")
