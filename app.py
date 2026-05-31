import streamlit as st  
import openai
import replicate
import os

# Configurazione della pagina Streamlit (Deve essere il PRIMO comando Streamlit della pagina)
st.set_page_config(page_title="Comic AI Creator - Manga Edition", page_icon="🎨", layout="wide")

# --- STILE CSS PERSONALIZZATO (Per ricreare il look dell'esempio) ---
st.markdown("""
    <style>
    /* Sfondo scuro per l'intera applicazione per richiamare il mood del manga */
    .stApp {
        background-color: #0d0f12;
        color: #e0e0e0;
    }
    
    /* Box della Vignetta del Fumetto */
    .comic-panel-container {
        position: relative;
        margin-bottom: 25px;
        border: 3px solid #1a1d24;
        background-color: #000000;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.7);
        border-radius: 4px;
        overflow: hidden;
    }
    
    /* Immagine adattiva della vignetta */
    .comic-panel-img {
        width: 100%;
        display: block;
        height: auto;
    }
    
    /* Didascalia stile "Shadow Requiem" (Riquadro nero, testo bianco, bordo sottile) */
    .comic-caption-box {
        background-color: rgba(0, 0, 0, 0.85);
        color: #ffffff;
        border: 1px solid #3a3f4d;
        padding: 10px 14px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 11pt;
        line-height: 1.4;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: -4px; /* Unisce visivamente il box all'immagine */
    }
    
    /* Didascalia interna opzionale (Angolo in alto) */
    .comic-overlay-caption {
        position: absolute;
        top: 10px;
        left: 10px;
        background-color: #000000;
        color: #ffffff;
        border: 1px solid #ffffff;
        padding: 6px 10px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 10pt;
        max-width: 80%;
        z-index: 10;
        text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)


# --- GESTIONE CHIAVI API ---
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    openai.api_key = os.getenv("OPENAI_API_KEY")

if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")


st.title("影🎨 Comic AI Creator - Shadow Edition")
st.markdown("### Genera il tuo libro a fumetti con layout e didascalie in stile Manga/Dark Novel")

# --- SIDEBAR (INPUT UTENTE) ---
st.sidebar.header("📚 Configura la tua Opera")

# Tipo di fumetto (Stile ottimizzato)
stile_fumetto = st.sidebar.selectbox(
    "Scegli lo stile grafico:",
    [
        "Dark Manga, ink sketch, high contrast black and white", 
        "Cyberpunk Graphic Novel, neon noir shadows, gritty realism", 
        "Classic American Comic Book, retro inks, dramatic shading",
        "Modern Cinematic Comic Art, detailed digital painting"
    ]
)

# Numero di vignette esteso per creare un libro/capitolo
num_vignette = st.sidebar.slider("Numero di vignette totali", min_value=2, max_value=20, value=4, step=1)

# Scelta del Layout della pagina
layout_scelta = st.sidebar.selectbox(
    "Struttura della pagina (Layout):",
    ["Griglia a 2 Colonne (Consigliata)", "Lista Singola Verticale (Grande)", "Griglia a 3 Colonne (Compatta)"]
)

# Trama principale
trama = st.sidebar.text_area(
    "Inserisci la trama completa:",
    placeholder="Anno 2128. La città di Noctis è controllata dalla Corp. Un ragazzo di nome Kai scopre che la sua ombra ha un potere proibito...",
    height=150
)

# Pulsante di avvio
generate_button = st.sidebar.button("⚡ CREA TAVOLA A FUMETTI")

# --- LOGICA DI GENERAZIONE ---
if generate_button:
    if not openai.api_key or not os.environ.get("REPLICATE_API_TOKEN"):
        st.error("⚠️ API Key mancanti nei Secrets di Streamlit!")
    elif not trama.strip():
        st.warning("✍️ Inserisci una trama prima di iniziare.")
    else:
        client = openai.OpenAI()
        
        # FASE 1: Creazione dei fogli modello dei personaggi per mantenere la coerenza visiva
        with st.spinner("🧠 Analisi della trama e fissaggio dei tratti dei personaggi..."):
            try:
                character_prompt = (
                    "Analizza la seguente trama e identifica i personaggi principali. "
                    "Crea una descrizione fisica molto dettagliata in INGLESE per ognuno di essi (es. genere, età apparente, vestiti fissi, capelli, espressione tipica). "
                    "Sii molto visivo ed evita concetti astratti. "
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
                with st.sidebar.expander("Visualizza Modello Personaggi"):
                    st.write(personaggi_coerenza)
                    
            except Exception as e:
                st.sidebar.error(f"Errore coerenza: {e}")
                personaggi_coerenza = ""

        # FASE 2: Generazione dello storyboard completo
        with st.spinner(f"📖 Scrittura della sceneggiatura in {num_vignette} vignette..."):
            try:
                system_prompt = (
                    "Sei un esperto sceneggiatore di fumetti e manga dark. Il tuo compito è suddividere la trama dell'utente "
                    f"in esattamente {num_vignette} vignette sequenziali per comporre una tavola o un capitolo completo. "
                    "La progressione deve coprire l'intera storia dall'inizio alla fine in modo fluido.\n\n"
                    "Per ogni vignetta devi fornire tassativamente:\n"
                    "1. Il titolo identificativo (es: VIGNETTA 1).\n"
                    "2. Una didascalia narrativa o un dialogo (IN ITALIANO), che sia d'impatto, epico e drammatico (es: 'ANNO 2128. LA CITTÀ È CONTROLLATA DALLA CORP...'). Non usare virgolette interne.\n"
                    "3. Un prompt d'immagine d'azione dettagliato in INGLESE focalizzato su un singolo riquadro, descrivendo l'inquadratura (es. dramatic close-up, wide overview angle), l'azione del personaggio e l'atmosfera circostante.\n\n"
                    "Rispondi formattando l'output esattamente in questo modo per ogni singola riga, separando i campi unicamente con il carattere '|':\n"
                    "Titolo Vignetta | Testo Didascalia Fumetto | Prompt d'azione per l'immagine\n"
                    "Non aggiungere introduzioni, note o markdown extra, scrivi solo le righe separate da '|'."
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

        # FASE 3: Generazione delle immagini e rendering grafico stile Manga
        if righe:
            st.success(f"📝 Sceneggiatura pronta! Disegno dei pannelli in corso...")
            
            # Prepariamo la struttura a colonne di Streamlit in base alla scelta dell'utente
            vignette_renderizzate = []
            
            # Ciclo di generazione (raccolta dati e chiamata a Replicate)
            for riga in righe:
                try:
                    parti = riga.split("|")
                    if len(parti) < 3:
                        continue
                        
                    titolo_vignetta = parti[0].strip()
                    dialogo = parti[1].strip()
                    action_prompt = parti[2].strip()
                    
                    with st.spinner(f"🎨 Disegno: {titolo_vignetta}..."):
                        # Costruiamo il prompt definitivo inserendo comandi per forzare il pannello singolo pulito
                        prompt_finale = (
                            f"A single, isolated comic book panel, {stile_fumetto}, masterwork. "
                            f"Scene: {action_prompt}. "
                            f"Character visual guidelines: {personaggi_coerenza}. "
                            f"Gothic atmosphere, deep shadows, high contrast, sharp ink lineart, distinct outer panel border. "
                            f"Clean frame, absolute no text, no speech bubbles, no words, single image view."
                        )
                        
                        output = replicate.run(
                            "black-forest-labs/flux-schnell",
                            input={
                                "prompt": prompt_finale,
                                "aspect_ratio": "4:3",
                                "num_outputs": 1
                            }
                        )
                        
                        image_url = str(output[0]) if isinstance(output, list) else str(output)
                        
                        # Salviamo i dati per il rendering successivo
                        vignette_renderizzate.append({
                            "titolo": titolo_vignetta,
                            "dialogo": dialogo,
                            "url": image_url
                        })
                        
                except Exception as e:
                    st.error(f"Errore nella vignetta: {e}")

            # --- RENDERING FINALE DELLA TAVOLA A FUMETTI (Struttura della pagina) ---
            st.markdown("## 📖 LA TAVOLA FINALE")
            st.markdown("---")
            
            if vignette_renderizzate:
                # Definiamo quante colonne usare nel layout di Streamlit
                if layout_scelta == "Griglia a 2 Colonne (Consigliata)":
                    col_count = 2
                elif layout_scelta == "Griglia a 3 Colonne (Compatta)":
                    col_count = 3
                else:
                    col_count = 1
                
                # Dividiamo le vignette nei contenitori grafici
                cols = st.columns(col_count)
                
                for idx, vig in enumerate(vignette_renderizzate):
                    # Sceglie la colonna corretta in modo ciclico
                    target_col = cols[idx % col_count]
                    
                    with target_col:
                        # Iniettiamo l'HTML customizzato per creare il blocco fumetto perfetto
                        html_pannello = f"""
                        <div class="comic-panel-container">
                            <div class="comic-overlay-caption">{vig['titolo']}</div>
                            <img class="comic-panel-img" src="{vig['url']}" alt="Comic Panel">
                            <div class="comic-caption-box">
                                {vig['dialogo']}
                            </div>
                        </div>
                        """
                        st.markdown(html_pannello, unsafe_allow_html=True)
                
                st.balloons()
                st.success("🎉 La tua opera in stile Shadow Requiem è pronta!")
