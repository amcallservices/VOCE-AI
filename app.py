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
st.markdown("### Genera fino a 200 vignette e scarica il tuo libro Word pronto nel formato KDP 6\"x9\"")

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

num_vignette = st.sidebar.slider("Numero di vignette totali", min_value=2, max_value=200, value=6, step=1)

layout_scelta = st.sidebar.selectbox(
    "Struttura anteprima web (Layout):",
    ["Griglia a 2 Colonne (Consigliata)", "Lista Singola Verticale (Grande)", "Griglia a 3 Colonne (Compatta)"]
)

trama = st.sidebar.text_area(
    "Inserisci la trama completa del tuo libro:",
    placeholder="Scrivi qui la storia del tuo libro a fumetti...",
    height=150
)

generate_button = st.sidebar.button("⚡ CREA E FORMATTA LIBRO WORD")

# --- LOGICA DI GENERAZIONE ---
if generate_button:
    if not openai.api_key or not os.environ.get("REPLICATE_API_TOKEN"):
        st.error("⚠️ API Key mancanti nei Secrets di Streamlit!")
    elif not trama.strip():
        st.warning("✍️ *Per favore, inserisci una trama prima di iniziare.*")
    else:
        # Resettiamo la memoria precedente per una nuova generazione
        st.session_state["vignette_generate"] = []
        st.session_state["word_data"] = None
        
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

        # FASE 2: Storyboard a blocchi (Chunking) fino a 200 vignette
        righe = []
        vignette_per_blocco = 10
        tot_blocchi = (num_vignette + vignette_per_blocco - 1) // vignette_per_blocco
        
        progress_bar = st.progress(0)
        
        for blocco in range(tot_blocchi):
            start_vig = (blocco * vignette_per_blocco) + 1
            end_vig = min((blocco + 1) * vignette_per_blocco, num_vignette)
            
            with st.spinner(f"📝 Generazione sceneggiatura: Vignette da {start_vig} a {end_vig}..."):
                try:
                    system_prompt = (
                        f"Sei un esperto sceneggiatore di fumetti. Stai scrivendo un libro di {num_vignette} vignette totali. "
                        f"Adesso devi scrivere ESATTAMENTE la porzione che va dalla vignetta {start_vig} alla vignetta {end_vig}. "
                        "Mantieni la massima continuità logica con i blocchi precedenti.\n\n"
                        "Rispondi formattando l'output rigidamente in questo modo per ogni riga, separando i campi unicamente con '|':\n"
                        "VIGNETTA X | Testo Didascalia Fumetto (In Italiano, maiuscolo, solenne) | Prompt d'azione per l'immagine (In Inglese)\n"
                        "Non includere introduzioni, note o markdown extra."
                    )
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Trama generale del libro: {trama}. Contesto righe precedenti: {str(righe[-3:]) if len(righe)>0 else 'Inizio'}"}
                        ],
                        temperature=0.7
                    )
                    
                    for line in response.choices[0].message.content.split("\n"):
                        line = line.strip()
                        if "|" in line and "titolo" not in line.lower() and len(line.split("|")) >= 3:
                            righe.append(line)
                            
                except Exception as e:
                    st.error(f"Errore blocco sceneggiatura {blocco+1}: {e}")
            
            progress_bar.progress((blocco + 1) / tot_blocchi)

        # FASE 3: Generazione immagini interamente in RAM
        if righe:
            st.success(f"📝 Sceneggiatura di {len(righe)} vignette pronta! Avvio disegno dei pannelli...")
            
            for i, riga in enumerate(righe):
                if i >= num_vignette:
                    break
                try:
                    parti = riga.split("|")
                    titolo_vignetta = parti[0].strip()
                    dialogo = parti[1].strip()
                    action_prompt = parti[2].strip()
                    
                    with st.spinner(f"🎨 Generazione {titolo_vignetta} di {num_vignette}..."):
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
                            
                            # Convertiamo e salviamo in RAM come byte PNG
                            out_png_buffer = BytesIO()
                            image_webp.save(out_png_buffer, "PNG")
                            out_png_buffer.seek(0)
                            png_bytes = out_png_buffer.getvalue()
                        else:
                            png_bytes = None
                        
                        st.session_state["vignette_generate"].append({
                            "titolo": titolo_vignetta,
                            "dialogo": dialogo,
                            "url": image_url,
                            "png_bytes": png_bytes
                        })
                except Exception as e:
                    st.error(f"Errore nella generazione della vignetta {i+1}: {e}")

            # --- COMPILAZIONE FILE WORD (.DOCX) IN RAM CONFIGURATO IN 6x9 POLLICI PER AMAZON KDP ---
            if st.session_state["vignette_generate"]:
                with st.spinner("📝 Compilazione e formattazione del file Word 6\"x9\" per KDP..."):
                    doc = Document()
                    
                    # 1. Configurazione Dimensioni Pagina 6x9 pollici ed impostazione margini di taglio (Bleed)
                    sections = doc.sections
                    for section in sections:
                        section.page_width = Inches(6.0)     # Larghezza KDP Standard
                        section.page_height = Inches(9.0)    # Altezza KDP Standard
                        section.top_margin = Inches(0.76)    # Margine di sicurezza superiore
                        section.bottom_margin = Inches(0.76) # Margine di sicurezza inferiore
                        section.left_margin = Inches(0.76)   # Margine interno (Gutter/Rilegatura sicuro)
                        section.right_margin = Inches(0.76)  # Margine esterno
                    
                    # 2. Pagina di Copertina Interna del Libro Word
                    title_p = doc.add_paragraph()
                    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    doc.add_paragraph("\n\n\n") # Spaziatura verticale per centrare il titolo
                    
                    title_run = title_p.add_run("SHADOW REQUIEM\n\n")
                    title_run.font.name = 'Courier New'
                    title_run.font.size = Pt(28)
                    title_run.font.bold = True
                    
                    sub_run = title_p.add_run("Volume a Fumetti\nEdito con AI Creator")
                    sub_run.font.name = 'Courier New'
                    sub_run.font.size = Pt(12)
                    sub_run.italic = True
                    
                    doc.add_page_break()
                    
                    # 3. Inserimento Tavole (1 Vignetta per pagina in formato 6x9)
                    for vig in st.session_state["vignette_generate"]:
                        if vig['png_bytes']:
                            try:
                                # Creiamo la griglia-tabella a cella singola per mantenere l'estetica fumetto
                                table = doc.add_table(rows=2, cols=1)
                                table.autofit = False
                                # La larghezza utile della cella calcolata sui margini (6.0 - 0.76 - 0.76 = 4.48 pollici)
                                table.columns[0].width = Inches(4.48)
                                
                                # Cella 1: Immagine Vignetta adattata proporzionalmente al formato 6x9
                                cell_img = table.cell(0, 0)
                                p_img = cell_img.paragraphs[0]
                                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                p_img.add_run().add_picture(BytesIO(vig['png_bytes']), width=Inches(4.3))
                                
                                # Cella 2: Didascalia Fumetto (Sfondo Nero, Testo Bianco Monospace)
                                cell_cap = table.cell(1, 0)
                                shading_xml = parse_xml(r'<w:shd {} w:fill="000000"/>'.format(nsdecls('w')))
                                cell_cap._tc.get_or_add_tcPr().append(shading_xml)
                                
                                p_cap = cell_cap.paragraphs[0]
                                p_cap.paragraph_format.left_indent = Inches(0.1)
                                p_cap.paragraph_format.right_indent = Inches(0.1)
                                
                                run_title = p_cap.add_run(f"{vig['titolo'].upper()} - ")
                                run_title.font.name = 'Courier New'
                                run_title.font.size = Pt(9.5)
                                run_title.font.bold = True
                                run_title.font.color.rgb = RGBColor(69, 243, 255) # Colore Ciano
                                
                                run_text = p_cap.add_run(vig['dialogo'].upper())
                                run_text.font.name = 'Courier New'
                                run_text.font.size = Pt(9.5)
                                run_text.font.bold = True
                                run_text.font.color.rgb = RGBColor(255, 255, 255) # Testo Bianco
                                
                                # Forza l'interruzione di pagina: ogni vignetta occupa una pagina KDP pulita ed indipendente
                                doc.add_page_break()
                            except Exception as e:
                                print(f"Errore KDP Word: {e}")
                
                word_buffer = BytesIO()
                doc.save(word_buffer)
                word_buffer.seek(0)
                st.session_state["word_data"] = word_buffer.getvalue()

# --- RENDERING ANTEPRIMA (FUORI DALL'IF GENERATE_BUTTON PER MANTENERE I DATI ATTIVI) ---
if st.session_state["vignette_generate"]:
    st.markdown("## 📖 ANTEPRIMA DEL LIBRO A FUMETTI")
    st.markdown("---")
    
    col_count = 3 if layout_scelta == "Griglia a 3 Colonne (Compatta)" else (2 if layout_scelta == "Griglia a 2 Colonne (Consigliata)" else 1)
    cols = st.columns(col_count)
    
    for idx, vig in enumerate(st.session_state["vignette_generate"]):
        with cols[idx % col_count]:
            st.markdown(f"""
            <div class="comic-panel-container">
                <div class="comic-overlay-caption">{vig['titolo']}</div>
                <img class="comic-panel-img" src="{vig['url']}">
                <div class="comic-caption-box">{vig['dialogo']}</div>
            </div>
            """, unsafe_allow_html=True)

    # --- AREA EXPORT UNICA E BLOCCATA IN BASSO ---
    st.markdown("---")
    st.markdown("## 📦 AREA EXPORT KDP AMAZON")
    
    if st.session_state["word_data"]:
        st.success(f"🎉 Elaborazione completata con successo! Il tuo file Microsoft Word è pronto.")
        st.download_button(
            label="📥 DOWNLOAD LIBRO FUMETTI IN WORD (.DOCX FORMATTATO 6x9 PER KDP)",
            data=st.session_state["word_data"],
            file_name="mio_libro_kdp_6x9.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
