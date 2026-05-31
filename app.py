import streamlit as st  
import openai
import replicate
import os
import requests
import base64
from weasyprint import HTML

# Configurazione della pagina Streamlit (Deve essere il PRIMO comando Streamlit della pagina)
st.set_page_config(page_title="Comic AI Creator - Book Publisher", page_icon="🎨", layout="wide")

# --- STILE CSS PERSONALIZZATO PER INTERFACCIA WEB ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0d0f12;
        color: #e0e0e0;
    }
    .comic-panel-container {
        position: relative;
        margin-bottom: 25px;
        border: 3px solid #1a1d24;
        background-color: #000000;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.7);
        border-radius: 4px;
        overflow: hidden;
    }
    .comic-panel-img {
        width: 100%;
        display: block;
        height: auto;
    }
    .comic-caption-box {
        background-color: rgba(0, 0, 0, 0.9);
        color: #ffffff;
        border-top: 2px solid #1a1d24;
        padding: 12px 16px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 11pt;
        line-height: 1.4;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
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

st.title("影🎨 Comic AI Creator & Book Publisher")
st.markdown("### Genera le tue tavole e scarica l'intero libro formattato in PDF")

# --- SIDEBAR (INPUT UTENTE) ---
st.sidebar.header("📚 Configura il tuo Libro")

stile_fumetto = st.sidebar.selectbox(
    "Scegli lo stile grafico:",
    [
        "Dark Manga, ink sketch, high contrast black and white", 
        "Cyberpunk Graphic Novel, neon noir shadows, gritty realism", 
        "Classic American Comic Book, retro inks, dramatic shading",
        "Modern Cinematic Comic Art, detailed digital painting"
    ]
)

num_vignette = st.sidebar.slider("Numero di vignette totali", min_value=2, max_value=20, value=4, step=1)

layout_scelta = st.sidebar.selectbox(
    "Struttura anteprima web (Layout):",
    ["Griglia a 2 Colonne (Consigliata)", "Lista Singola Verticale (Grande)", "Griglia a 3 Colonne (Compatta)"]
)

trama = st.sidebar.text_area(
    "Inserisci la trama completa del tuo libro:",
    placeholder="Anno 2128. La città di Noctis è controllata dalla Corp...",
    height=150
)

generate_button = st.sidebar.button("⚡ CREA E FORMATTA LIBRO")

# --- FUNZIONE UTILE PER CONVERTIRE IMMAGINI IN BASE64 PER IL PDF ---
def get_image_base64(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        print(f"Errore download immagine per Base64: {e}")
    return ""

# --- LOGICA DI GENERAZIONE ---
if generate_button:
    if not openai.api_key or not os.environ.get("REPLICATE_API_TOKEN"):
        st.error("⚠️ API Key mancanti nei Secrets di Streamlit!")
    elif not trama.strip():
        st.warning("✍ *Per favore, inserisci una trama prima di iniziare.*")
    else:
        client = openai.OpenAI()
        
        # FASE 1: Coerenza Personaggi
        with st.spinner("🧠 Analisi della trama e strutturazione dei personaggi..."):
            try:
                character_prompt = (
                    "Analizza la seguente trama e identifica i personaggi principali. "
                    "Crea una descrizione fisica molto dettagliata in INGLESE per ognuno di essi. "
                    "Rispondi SOLTANTO con le descrizioni dei personaggi accumulate in un unico paragrafo compatto."
                )
                char_response = client.chat.completions.create(
                    model="gpt-4o-mini", model_list=None,
                    messages=[
                        {"role": "system", "content": character_prompt},
                        {"role": "user", "content": f"Trama: {trama}"}
                    ],
                    temperature=0.5
                )
                personaggi_coerenza = char_response.choices[0].message.content
                st.sidebar.success("✅ Coerenza Personaggi Attivata!")
            except Exception as e:
                st.sidebar.error(f"Errore coerenza: {e}")
                personaggi_coerenza = ""

        # FASE 2: Storyboard
        with st.spinner(f"📖 Scrittura della sceneggiatura cinematografica ({num_vignette} vignette)..."):
            try:
                system_prompt = (
                    "Sei un esperto sceneggiatore di fumetti e manga dark. Suddividi la trama dell'utente "
                    f"in esattamente {num_vignette} vignette sequenziali per comporre un capitolo/libro completo.\n\n"
                    "Rispondi formattando l'output esattamente in questo modo per ogni riga, separando i campi con '|':\n"
                    "Titolo Vignetta | Testo Didascalia Fumetto (In Italiano, stile solenne e maiuscolo) | Prompt d'azione per l'immagine (In Inglese)\n"
                    "Non aggiungere introduzioni o altre parole."
                )
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Trama: {trama}"}
                    ],
                    temperature=0.7
                )
                righe = [line.strip() for line in response.choices[0].message.content.split("\n") if "|" in line]
            except Exception as e:
                st.error(f"Errore sceneggiatura: {e}")
                righe = []

        # FASE 3: Generazione immagini e raccolta dati per il PDF
        if righe:
            st.success(f"📝 Sceneggiatura pronta! Disegno dei pannelli in corso...")
            vignette_renderizzate = []
            
            for riga in righe:
                try:
                    parti = riga.split("|")
                    if len(parti) < 3:
                        continue
                    titolo_vignetta = parti[0].strip()
                    dialogo = parti[1].strip()
                    action_prompt = parti[2].strip()
                    
                    with st.spinner(f"🎨 Disegno in corso: {titolo_vignetta}..."):
                        prompt_finale = (
                            f"A single, isolated comic book panel, {stile_fumetto}, masterwork. "
                            f"Scene: {action_prompt}. Character visual guidelines: {personaggi_coerenza}. "
                            f"Gothic atmosphere, deep shadows, high contrast, sharp ink lineart, distinct outer panel border. "
                            f"Clean frame, absolute no text, no speech bubbles, no words, single image view."
                        )
                        output = replicate.run(
                            "black-forest-labs/flux-schnell",
                            input={"prompt": prompt_finale, "aspect_ratio": "4:3", "num_outputs": 1}
                        )
                        image_url = str(output[0]) if isinstance(output, list) else str(output)
                        
                        # Scarica e converti l'immagine in Base64 per incorporarla nel PDF senza dipendere da URL esterni stabili
                        img_b64 = get_image_base64(image_url)
                        
                        vignette_renderizzate.append({
                            "titolo": titolo_vignetta,
                            "dialogo": dialogo,
                            "url": image_url,
                            "b64": img_b64
                        })
                except Exception as e:
                    st.error(f"Errore nella generazione di una vignetta: {e}")

            # --- VISUALIZZAZIONE WEB ANTEPRIMA ---
            st.markdown("## 📖 ANTEPRIMA TAVOLA")
            st.markdown("---")
            if vignette_renderizzate:
                col_count = 3 if layout_scelta == "Griglia a 3 Colonne (Compatta)" else (2 if layout_scelta == "Griglia a 2 Colonne (Consigliata)" else 1)
                cols = st.columns(col_count)
                for idx, vig in enumerate(vignette_renderizzate):
                    with cols[idx % col_count]:
                        st.markdown(f"""
                        <div class="comic-panel-container">
                            <div class="comic-overlay-caption">{vig['titolo']}</div>
                            <img class="comic-panel-img" src="{vig['url']}">
                            <div class="comic-caption-box">{vig['dialogo']}</div>
                        </div>
                        """, unsafe_allow_html=True)

                # --- COMPILAZIONE ED ESPORTAZIONE PDF REALE ---
                st.markdown("---")
                st.markdown("## 📦 ESPORTA IL TUO LIBRO COMPLETO")
                
                with st.spinner("📚 Formattazione del libro e compilazione del PDF in corso..."):
                    # Generazione del codice HTML pulito per WeasyPrint (impaginazione da libro reale)
                    html_content = """
                    <html>
                    <head>
                    <style>
                        @page {
                            size: A4;
                            margin: 15mm 15mm;
                            background-color: #0b0c10;
                        }
                        body {
                            margin: 0;
                            padding: 0;
                            font-family: 'Courier New', Courier, monospace;
                            background-color: #0b0c10;
                            color: #ffffff;
                        }
                        .page-title-section {
                            text-align: center;
                            padding-top: 60mm;
                            page-break-after: always;
                        }
                        .page-title-section h1 {
                            font-size: 32pt;
                            letter-spacing: 2px;
                            margin-bottom: 10px;
                            color: #ffffff;
                            text-transform: uppercase;
                        }
                        .page-title-section p {
                            font-size: 14pt;
                            color: #888888;
                        }
                        .pdf-panel-wrapper {
                            page-break-inside: avoid;
                            margin-bottom: 30mm;
                            border: 4px solid #1f2833;
                            background-color: #000000;
                        }
                        .pdf-img {
                            width: 100%;
                            display: block;
                        }
                        .pdf-caption {
                            background-color: #000000;
                            color: #ffffff;
                            padding: 15px;
                            font-size: 13pt;
                            line-height: 1.5;
                            border-top: 3px solid #1f2833;
                            text-transform: uppercase;
                            letter-spacing: 0.5px;
                        }
                        .pdf-meta {
                            font-size: 10pt;
                            color: #45f3ff;
                            margin-bottom: 5px;
                            font-weight: bold;
                        }
                    </style>
                    </head>
                    <body>
                        <div class="page-title-section">
                            <h1>SHADOW REQUIEM</h1>
                            <p>Generato da Comic AI Creator</p>
                        </div>
                    """
                    
                    # Aggiungiamo i blocchi delle vignette nel file HTML
                    for vig in vignette_renderizzate:
                        if vig['b64']:
                            html_content += f"""
                            <div class="pdf-panel-wrapper">
                                <img class="pdf-img" src="data:image/png;base64,{vig['b64']}">
                                <div class="pdf-caption">
                                    <div class="pdf-meta">{vig['titolo']}</div>
                                    {vig['dialogo']}
                                </div>
                            </div>
                            """
                    
                    html_content += "</body></html>"
                    
                    # Salvataggio temporaneo del file HTML ed esecuzione di WeasyPrint per produrre il PDF
                    html_path = "temp_comic.html"
                    pdf_path = "libro_fumetti.pdf"
                    
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    
                    # Trasforma l'HTML compilato in un PDF pronto all'uso
                    HTML(html_path).write_pdf(pdf_path)
                    
                    # Lettura dei dati binari del PDF per permettere il download su Streamlit
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                
                # Rilascio del pulsante di download per l'utente
                st.balloons()
                st.success("🎉 Il tuo libro a fumetti è formattato e pronto!")
                st.download_button(
                    label="📥 SCARICA IL LIBRO IN PDF (PRONTO STAMPA)",
                    data=pdf_bytes,
                    file_name="mio_libro_a_fumetti.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
