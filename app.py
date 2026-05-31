import streamlit as st  
import openai
import replicate
import os
import requests
from fpdf import FPDF
from io import BytesIO

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

# --- CLASSE CUSTOM FPDF PER IL LOOK DARK BONELLI / MANGA ---
class ComicPDF(FPDF):
    def header(self):
        pass
    def footer(self):
        # Numero di pagina in basso a destra
        self.set_y(-15)
        self.set_font("courier", "B", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"{self.page_no()}", align="R")

# --- LOGICA DI GENERAZIONE ---
if generate_button:
    if not openai.api_key or not os.environ.get("REPLICATE_API_TOKEN"):
        st.error("⚠️ API Key mancanti nei Secrets di Streamlit!")
    elif not trama.strip():
        st.warning("✍️ *Per favore, inserisci una trama prima di iniziare.*")
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
                    model="gpt-4o-mini",
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
                    "Sei un expert sceneggiatore di fumetti e manga dark. Suddividi la trama dell'utente "
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

        # FASE 3: Generazione immagini e raccolta dati
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
                        
                        # Scarichiamo l'immagine in memoria per passarla a FPDF senza salvarla su disco
                        img_response = requests.get(image_url)
                        img_bytes = BytesIO(img_response.content) if img_response.status_code == 200 else None
                        
                        vignette_renderizzate.append({
                            "titolo": titolo_vignetta,
                            "dialogo": dialogo,
                            "url": image_url,
                            "bytes": img_bytes
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

                # --- COMPILAZIONE PDF NATIVA (FPDF2) ---
                st.markdown("---")
                st.markdown("## 📦 ESPORTA IL TUO LIBRO COMPLETO")
                
                with st.spinner("📚 Generazione del file PDF in corso..."):
                    pdf = ComicPDF(orientation="P", unit="mm", format="A4")
                    pdf.set_auto_page_break(auto=True, margin=15)
                    
                    # 1. PAGINA DI COPERTINA SCOLO COERENTE (SFONDO NERO)
                    pdf.add_page()
                    pdf.set_fill_color(13, 15, 18) # Sfondo scuro dell'app
                    pdf.rect(0, 0, 210, 297, "F")
                    
                    pdf.set_y(100)
                    pdf.set_font("courier", "B", 32)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 15, "SHADOW REQUIEM", align="C", ln=True)
                    
                    pdf.set_font("courier", "I", 14)
                    pdf.set_text_color(150, 150, 150)
                    pdf.cell(0, 10, "A Comic AI Generated Book", align="C", ln=True)
                    
                    # 2. INSERIMENTO DELLE VIGNETTE (Massimo 2 per pagina per la massima resa grafica)
                    for idx, vig in enumerate(vignette_renderizzate):
                        # Aggiungiamo una nuova pagina ogni 2 vignette per non affollare la stampa
                        if idx % 2 == 0:
                            pdf.add_page()
                            pdf.set_fill_color(13, 15, 18)
                            pdf.rect(0, 0, 210, 297, "F")
                            pdf.set_y(15)
                        
                        if vig['bytes']:
                            try:
                                # Reset del buffer di memoria dell'immagine
                                vig['bytes'].seek(0)
                                
                                # Disegno dell'immagine (Larghezza standard 170mm, centrata su A4)
                                current_y = pdf.get_y()
                                pdf.image(vig['bytes'], x=20, y=current_y, w=170)
                                
                                # Calcolo altezza proporzionale dell'immagine (aspetto 4:3) -> h = (170 * 3) / 4 = 127.5mm
                                pdf.set_y(current_y + 127.5)
                                
                                # Riquadro di testo Didascalia (Sfondo Nero)
                                pdf.set_fill_color(0, 0, 0)
                                pdf.set_draw_color(31, 40, 51)
                                pdf.set_line_width(0.8)
                                
                                # Calcoliamo quante righe occupa il testo per fare il box corretto
                                pdf.set_font("courier", "B", 10)
                                pdf.set_text_color(69, 243, 255) # Colore ciano per il titolo della vignetta
                                text_title = f"{vig['titolo']} - "
                                
                                pdf.set_text_color(255, 255, 255) # Testo bianco
                                full_text = text_title + vig['dialogo'].upper()
                                
                                # Stampiamo il blocco con lo sfondo nero attivato (ln=True ci sposta sotto per la vignetta successiva)
                                pdf.multi_cell(170, 6, full_text, border=1, align="L", fill=True)
                                pdf.set_y(pdf.get_y() + 12) # Spazio di distanziamento per la seconda vignetta della pagina
                                
                            except Exception as pdf_img_err:
                                print(f"Errore inserimento immagine PDF: {pdf_img_err}")
                    
                    # Generazione dei byte del PDF direttamente in memoria
                    pdf_output = pdf.output()
                
                # Rilascio del pulsante di download
                st.balloons()
                st.success("🎉 Il tuo libro a fumetti è stato impaginato ed è pronto al download!")
                st.download_button(
                    label="📥 SCARICA IL LIBRO IN PDF (PRONTO STAMPA)",
                    data=bytes(pdf_output),
                    file_name="mio_libro_a_fumetti.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
