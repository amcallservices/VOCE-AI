import streamlit as st  
import openai
import replicate
import os
import requests
from io import BytesIO
from PIL import Image
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Comic AI Creator - KDP Word Publisher", page_icon="🎨", layout="wide", initial_sidebar_state="expanded")

# --- CSS AVANZATO: BLOCCO SIDEBAR E RIMOZIONE MENU IN ALTO A DESTRA ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    [data-testid="sidebar-toggle"] {
        display: none !important;
    }
    
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
    .comic-story-text {
        background-color: #161920;
        border-left: 4px solid #45f3ff;
        padding: 15px;
        margin-bottom: 20px;
        font-style: italic;
        border-radius: 0 4px 4px 0;
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

# --- INIZIALIZZAZIONE DELLO STATO DI MEMORIA ---
if "vignette_generate" not in st.session_state:
    st.session_state["vignette_generate"] = []
if "word_data" not in st.session_state:
    st.session_state["word_data"] = None

# --- GESTIONE CHIAVI API ---
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    openai.api_key = os.getenv("OPENAI_API_KEY")

if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN")

st.title("影🎨 Comic AI Creator & KDP Word Publisher")
st.markdown("### Genera fino a 200 vignette con testo e immagini uniti nella stessa pagina KDP 6\"x9\"")

# --- SIDEBAR (INPUT UTENTE) ---
st.sidebar.header("📚 Configura il tuo Libro")

# Nuova opzione per inserire il titolo del libro personalizzato
titolo_libro = st.sidebar.text_input("Inserisci il Titolo del Libro:", placeholder="Es. L'Ombra del Destino")

stile_fumetto = st.sidebar.selectbox(
    "Scegli lo stile grafico:",
    [
        "Dark Manga, ink sketch, high contrast black and white", 
        "Cyberpunk Graphic Novel, neon noir shadows, gritty realism", 
        "Classic American Comic Book, retro inks, dramatic shading",
        "Modern Cinematic Comic Art, detailed digital painting"
    ]
)

num_vignette = st.sidebar.slider("Numero di vignette/capitoli", min_value=2, max_value=200, value=4, step=1)

layout_scelta = st.sidebar.selectbox(
    "Struttura anteprima web (Layout):",
    ["Lista Singola Verticale (Grande)", "Griglia a 2 Colonne (Consigliata)", "Griglia a 3 Colonne (Compatta)"]
)

trama = st.sidebar.text_area(
    "Inserisci la trama completa del tuo libro:",
    placeholder="Scrivi qui la storia del tuo libro a fumetti...",
    height=150
)

generate_button = st.sidebar.button("⚡ CREA LIBRO ILLUSTRATO WORD")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Svuota Memoria / Reset"):
    st.session_state["vignette_generate"] = []
    st.session_state["word_data"] = None
    st.rerun()

# --- LOGICA DI GENERAZIONE ---
if generate_button:
    if not openai.api_key or not os.environ.get("REPLICATE_API_TOKEN"):
        st.error("⚠️ API Key mancanti nei Secrets di Streamlit!")
    elif not trama.strip():
        st.warning("✍️ *Per favore, inserisci una trama prima di iniziare.*")
    else:
        st.session_state["vignette_generate"] = []
        st.session_state["word_data"] = None
        
        # Validazione del titolo inserito
        titolo_finale_libro = titolo_libro.strip().upper() if titolo_libro.strip() else "IL MIO ROMANZO ILLUSTRATO"
        
        client = openai.OpenAI()
        
        # FASE 1: Coerenza Personaggi
        with st.spinner("🧠 Analisi della trama e strutturazione dei personaggi..."):
            try:
                character_prompt = (
                    "Analizza la trama e identifica i personaggi principali. "
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
            except Exception as e:
                st.sidebar.error(f"Errore coerenza: {e}")
                personaggi_coerenza = ""

        # FASE 2: Storyboard a blocchi (Chunking)
        righe = []
        vignette_per_blocco = 5 
        tot_blocchi = (num_vignette + vignette_per_blocco - 1) // vignette_per_blocco
        
        progress_bar = st.progress(0)
        
        for blocco in range(tot_blocchi):
            start_vig = (blocco * vignette_per_blocco) + 1
            end_vig = min((blocco + 1) * vignette_per_blocco, num_vignette)
            
            with st.spinner(f"📝 Generazione narrativa e prompt: Scene {start_vig} a {end_vig}..."):
                try:
                    system_prompt = (
                        f"Sei un autore di romanzi illustrati. Stai scrivendo un libro di {num_vignette} scene totali. "
                        f"Adesso devi scrivere ESATTAMENTE la porzione che va dalla scena {start_vig} alla scena {end_vig}.\n\n"
                        "Per OGNI scena devi generare tassativamente 4 elementi separati dal carattere '|':\n"
                        "1. Il Titolo (es. VIGNETTA X)\n"
                        "2. La STORIA TESTUALE (Un paragrafo narrativo concentrato ed avvincente in prosa letteraria italiana, di circa 4-5 righe, da stampare sopra l'immagine).\n"
                        "3. La DIDASCALIA BREVE (In Italiano, tutto in maiuscolo, solenne, per il box nero sotto l'immagine).\n"
                        "4. Il PROMPT D'AZIONE (In Inglese, dettagliato, focalizzato su un singolo riquadro visivo senza scritte).\n\n"
                        "Rispondi formattando l'output rigidamente in questo modo per ogni riga (una riga per scena):\n"
                        "Titolo | Storia Testuale Romanzata | Didascalia Fumetto | Prompt per l'immagine\n"
                        "Non includere introduzioni, note o markdown extra. Usa solo il divisore '|'."
                    )
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Trama generale del libro: {trama}. Record storico righe precedenti: {str(righe[-2:]) if len(righe)>0 else 'Inizio'}"}
                        ],
                        temperature=0.7
                    )
                    
                    for line in response.choices[0].message.content.split("\n"):
                        line = line.strip()
                        if "|" in line and "titolo" not in line.lower() and len(line.split("|")) >= 4:
                            righe.append(line)
                            
                except Exception as e:
                    st.error(f"Errore blocco sceneggiatura {blocco+1}: {e}")
            
            progress_bar.progress((blocco + 1) / tot_blocchi)

        # FASE 3: Generazione immagini interamente in RAM
        if righe:
            st.success(f"📝 Sceneggiatura ed elementi testuali di {len(righe)} scene pronti! Avvio pittura digitale...")
            
            for i, riga in enumerate(righe):
                if i >= num_vignette:
                    break
                try:
                    parti = riga.split("|")
                    titolo_vignetta = parti[0].strip()
                    storia_testo = parti[1].strip()
                    dialogo = parti[2].strip()
                    action_prompt = parti[3].strip()
                    
                    with st.spinner(f"🎨 Disegno ed impaginazione di {titolo_vignetta}..."):
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
                        
                        img_response = requests.get(image_url)
                        if img_response.status_code == 200:
                            ram_buffer_png = BytesIO(img_response.content)
                            image_webp = Image.open(ram_buffer_png)
                            
                            out_png_buffer = BytesIO()
                            image_webp.save(out_png_buffer, "PNG")
                            out_png_buffer.seek(0)
                            png_bytes = out_png_buffer.getvalue()
                        else:
                            png_bytes = None
                        
                        st.session_state["vignette_generate"].append({
                            "titolo": titolo_vignetta,
                            "storia": storia_testo,
                            "dialogo": dialogo,
                            "url": image_url,
                            "png_bytes": png_bytes
                        })
                except Exception as e:
                    st.error(f"Errore nella generazione della scena {i+1}: {e}")

            # --- COMPILAZIONE FILE WORD (.DOCX) 6x9 POLLICI PER KDP ---
            if st.session_state["vignette_generate"]:
                with st.spinner("📝 Generazione del manoscritto Word KDP Unificato..."):
                    doc = Document()
                    
                    # Configurazione Layout 6x9 Amazon KDP
                    sections = doc.sections
                    for section in sections:
                        section.page_width = Inches(6.0)
                        section.page_height = Inches(9.0)
                        section.top_margin = Inches(0.76)
                        section.bottom_margin = Inches(0.76)
                        section.left_margin = Inches(0.76)
                        section.right_margin = Inches(0.76)
                    
                    # Frontespizio / Copertina Interna Pulita: Solo il Titolo Utente
                    doc.add_paragraph("\n\n\n\n\n")
                    title_p = doc.add_paragraph()
                    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    title_run = title_p.add_run(f"{titolo_finale_libro}\n")
                    title_run.font.name = 'Courier New'
                    title_run.font.size = Pt(26)
                    title_run.font.bold = True
                    
                    doc.add_page_break()
                    
                    # Costruzione delle pagine unificate (Testo + Immagine)
                    for idx, vig in enumerate(st.session_state["vignette_generate"]):
                        # 1. PARTE SUPERIORE DELLA PAGINA: Storia Testuale Romanzata
                        storia_pulita = vig.get('storia', '')
                        p_story = doc.add_paragraph()
                        p_story.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                        p_story.paragraph_format.line_spacing = 1.15
                        p_story.paragraph_format.space_after = Pt(8)
                        
                        # Titolo della singola scena
                        run_chap = p_story.add_run(f"--- {vig['titolo'].upper()} ---\n")
                        run_chap.font.name = 'Georgia'
                        run_chap.font.size = Pt(11)
                        run_chap.font.bold = True
                        
                        # Testo narrativo
                        run_story = p_story.add_run(storia_pulita)
                        run_story.font.name = 'Georgia'
                        run_story.font.size = Pt(9.5)
                        
                        # Spazio vuoto prima del disegno
                        p_space = doc.add_paragraph()
                        p_space.paragraph_format.space_after = Pt(6)
                        
                        # 2. PARTE INFERIORE DELLA PAGINA: La Tavola Grafica (Immagine Compatta + Box Nero)
                        if vig.get('png_bytes'):
                            try:
                                table = doc.add_table(rows=2, cols=1)
                                table.autofit = False
                                table.columns[0].width = Inches(4.48)
                                
                                # Inserimento Immagine (ridimensionata per la pagina unificata)
                                cell_img = table.cell(0, 0)
                                p_img = cell_img.paragraphs[0]
                                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                p_img.add_run().add_picture(BytesIO(vig['png_bytes']), width=Inches(3.3))
                                
                                # Inserimento Box Nero con Didascalia sotto l'immagine
                                cell_cap = table.cell(1, 0)
                                shading_xml = parse_xml(r'<w:shd {} w:fill="000000"/>'.format(nsdecls('w')))
                                cell_cap._tc.get_or_add_tcPr().append(shading_xml)
                                
                                p_cap = cell_cap.paragraphs[0]
                                p_cap.paragraph_format.left_indent = Inches(0.1)
                                p_cap.paragraph_format.right_indent = Inches(0.1)
                                
                                run_t = p_cap.add_run(f"{vig['titolo'].upper()} - ")
                                run_t.font.name = 'Courier New'
                                run_t.font.size = Pt(9)
                                run_t.font.bold = True
                                run_t.font.color.rgb = RGBColor(69, 243, 255) # Ciano
                                
                                run_d = p_cap.add_run(vig['dialogo'].upper())
                                run_d.font.name = 'Courier New'
                                run_d.font.size = Pt(9)
                                run_d.font.bold = True
                                run_d.font.color.rgb = RGBColor(255, 255, 255) # Bianco
                                
                            except Exception as e:
                                print(e)
                        
                        # FIX DEFINITIVO PAGINA VUOTA: Inserisce l'interruzione SOLO se NON siamo all'ultima pagina
                        if idx < len(st.session_state["vignette_generate"]) - 1:
                            doc.add_page_break()
                
                word_buffer = BytesIO()
                doc.save(word_buffer)
                word_buffer.seek(0)
                st.session_state["word_data"] = word_buffer.getvalue()

# --- RENDERING INTERFACCIA WEB ANTEPRIMA ---
if st.session_state["vignette_generate"]:
    st.markdown("## 📖 ANTEPRIMA DEL LIBRO ILLUSTRATO")
    st.markdown("---")
    
    col_count = 3 if layout_scelta == "Griglia a 3 Colonne (Compatta)" else (2 if layout_scelta == "Griglia a 2 Colonne (Consigliata)" else 1)
    cols = st.columns(col_count)
    
    for idx, vig in enumerate(st.session_state["vignette_generate"]):
        with cols[idx % col_count]:
            st.markdown(f"### 📄 {vig['titolo']}")
            
            storia_web = vig.get('storia', 'Nessun testo narrativo generato per questa scena.')
            st.markdown(f"<div class='comic-story-text'><b>Il Racconto:</b> {storia_web}</div>", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="comic-panel-container">
                <img class="comic-panel-img" src="{vig['url']}">
                <div class="comic-caption-box">{vig['dialogo']}</div>
            </div>
            """, unsafe_allow_html=True)

    # --- AREA EXPORT KDP ---
    st.markdown("---")
    st.markdown("## 📦 AREA EXPORT KDP AMAZON")
    
    if st.session_state["word_data"]:
        st.success("🎉 Libro generato! Ogni pagina del file Word contiene la storia testuale e la tavola illustrata unite in formato 6\"x9\" (senza pagine vuote finali).")
        st.download_button(
            label="📥 DOWNLOAD LIBRO UNIFICATO (STORIA + ILLUSTRAZIONI UNITE IN WORD 6x9)",
            data=st.session_state["word_data"],
            file_name="romanzo_illustrato_unificato_6x9.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
