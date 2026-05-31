import streamlit as st  
import openai
import replicate
import os
import requests
from io import BytesIO
from PIL import Image
from fpdf import FPDF
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

# Configurazione della pagina Streamlit (Deve essere il PRIMO comando Streamlit della pagina)
st.set_page_config(page_title="Comic AI Creator - Ultimate Publisher", page_icon="🎨", layout="wide", initial_sidebar_state="expanded")

# --- CSS AVANZATO: BLOCCO SIDEBAR E RIMOZIONE MENU IN ALTO A DESTRA ---
st.markdown("""
    <style>
    /* Nasconde il menu in alto a destra (tre puntini/linee) e il footer standard */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Nasconde la freccetta per chiudere la sidebar, bloccandola sempre aperta */
    [data-testid="sidebar-toggle"] {
        display: none !important;
    }
    
    /* Stile scuro per l'interfaccia Web (Stile Shadow Requiem) */
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

# --- FUNZIONE DI PULIZIA TESTO PER EVITARE UNICODEENCODEERROR IN FPDF ---
def clean_text_for_latin1(text):
    if not text:
        return ""
    replacements = {
        '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2026': '...',
        'à': "a'", 'è': "e'", 'é': "e'", 'ì': "i'", 'ò': "o'", 'ù': "u'"
    }
    for unicode_char, latin1_char in replacements.items():
        text = text.replace(unicode_char, latin1_char)
    return text.encode('latin-1', 'ignore').decode('latin-1')

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
st.markdown("### Genera fino a 200 vignette e scarica l'opera formattata in PDF o WORD")

# --- SIDEBAR (INPUT UTENTE) ---
st.sidebar.header("📚 Configura la tua Opera")

stile_fumetto = st.sidebar.selectbox(
    "Scegli lo stile grafico:",
    [
        "Dark Manga, ink sketch, high contrast black and white", 
        "Cyberpunk Graphic Novel, neon noir shadows, gritty realism", 
        "Classic American Comic Book, retro inks, dramatic shading",
        "Modern Cinematic Comic Art, detailed digital painting"
    ]
)

# Esteso fino a 200 vignette come richiesto
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

generate_button = st.sidebar.button("⚡ CREA OPERA COMPLETA")

# --- CLASSE CUSTOM FPDF ---
class ComicPDF(FPDF):
    def __init__(self, orientation="P", unit="mm", format="A4"):
        super().__init__(orientation, unit, format)
    def header(self):
        pass
    def footer(self):
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
                st.sidebar.success("✅ Coerenza Personaggi Attivata!")
            except Exception as e:
                st.sidebar.error(f"Errore coerenza: {e}")
                personaggi_coerenza = ""

        # FASE 2: Storyboard strutturato a blocchi (Chunking) per supportare fino a 200 vignette
        righe = []
        vignette_per_blocco = 10
        tot_blocchi = (num_vignette + vignette_per_blocco - 1) // vignette_per_blocco
        
        progress_bar = st.progress(0)
        st.info("📖 Pianificazione della sceneggiatura a blocchi in corso...")
        
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
            vignette_renderizzate = []
            
            for i, riga in enumerate(righe):
                if i >= num_vignette: # Taglio di sicurezza se GPT genera righe in più
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
                        
                        # SCARICAMENTO E CONVERSIONE IN RAM (Questo risolve il PDF vuoto)
                        img_response = requests.get(image_url)
                        if img_response.status_code == 200:
                            # Apriamo l'immagine WebP e la salviamo come PNG dentro un buffer di memoria RAM
                            ram_buffer_png = BytesIO()
                            image_webp = Image.open(BytesIO(img_response.content))
                            image_webp.save(ram_buffer_png, "PNG")
                            ram_buffer_png.seek(0)
                        else:
                            ram_buffer_png = None
                        
                        vignette_renderizzate.append({
                            "titolo": titolo_vignetta,
                            "dialogo": dialogo,
                            "url": image_url,
                            "ram_png": ram_buffer_png
                        })
                except Exception as e:
                    st.error(f"Errore nella generazione della vignetta {i+1}: {e}")

            # --- VISUALIZZAZIONE WEB ANTEPRIMA ---
            st.markdown("## 📖 ANTEPRIMA DEL LIBRO A FUMETTI")
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

                # --- GENERAZIONE COMPILAZIONE FILE PDF IN RAM ---
                st.markdown("---")
                st.markdown("## 📦 AREA EXPORT & DOWNLOAD")
                
                with st.spinner("📚 Impaginazione del file PDF in corso..."):
                    pdf = ComicPDF(orientation="P", unit="mm", format="A4")
                    pdf.set_auto_page_break(auto=True, margin=15)
                    
                    # Copertina PDF
                    pdf.add_page()
                    pdf.set_fill_color(13, 15, 18) 
                    pdf.rect(0, 0, 210, 297, "F")
                    pdf.set_y(100)
                    pdf.set_font("courier", "B", 32)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 15, clean_text_for_latin1("SHADOW REQUIEM"), align="C", ln=True)
                    pdf.set_font("courier", "I", 14)
                    pdf.set_text_color(150, 150, 150)
                    pdf.cell(0, 10, clean_text_for_latin1("Volume a Fumetti Completo"), align="C", ln=True)
                    
                    # Pagine Interne PDF (2 vignette per pagina)
                    for idx, vig in enumerate(vignette_renderizzate):
                        if idx % 2 == 0:
                            pdf.add_page()
                            pdf.set_fill_color(13, 15, 18)
                            pdf.rect(0, 0, 210, 297, "F")
                            pdf.set_y(15)
                        
                        if vig['ram_png']:
                            try:
                                vig['ram_png'].seek(0)
                                current_y = pdf.get_y()
                                
                                # Carichiamo il PDF passando l'oggetto BytesIO direttamente. FPDF lo supporta stabilmente.
                                pdf.image(vig['ram_png'], x=20, y=current_y, w=170)
                                pdf.set_y(current_y + 127.5)
                                
                                # Box didascalia
                                pdf.set_fill_color(0, 0, 0)
                                pdf.set_draw_color(31, 40, 51)
                                pdf.set_line_width(0.8)
                                
                                pdf.set_font("courier", "B", 10)
                                pdf.set_text_color(69, 243, 255) 
                                text_title = f"{vig['titolo']} - "
                                pdf.set_text_color(255, 255, 255) 
                                full_text = text_title + vig['dialogo'].upper()
                                
                                pdf.multi_cell(170, 6, clean_text_for_latin1(full_text), border=1, align="L", fill=True)
                                pdf.set_y(pdf.get_y() + 12) 
                            except Exception as pdf_err:
                                print(f"Errore PDF: {pdf_err}")
                                
                    pdf_bytes = pdf.output(dest='S')

                # --- GENERAZIONE COMPILAZIONE FILE WORD (.DOCX) IN RAM ---
                with st.spinner("📝 Compilazione del file Microsoft Word (.docx) in corso..."):
                    doc = Document()
                    
                    # Configurazione margini pagina Word
                    sections = doc.sections
                    for section in sections:
                        section.top_margin = Inches(0.6)
                        section.bottom_margin = Inches(0.6)
                        section.left_margin = Inches(0.6)
                        section.right_margin = Inches(0.6)
                    
                    # Titolo Copertina Word
                    title_p = doc.add_paragraph()
                    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    title_run = title_p.add_run("SHADOW REQUIEM\n")
                    title_run.font.name = 'Courier New'
                    title_run.font.size = Pt(36)
                    title_run.font.bold = True
                    
                    sub_run = title_p.add_run("Volume a Fumetti edito con AI Creator")
                    sub_run.font.name = 'Courier New'
                    sub_run.font.size = Pt(14)
                    sub_run.italic = True
                    
                    doc.add_page_break()
                    
                    # Inserimento Tavole nel file Word
                    for vig in vignette_renderizzate:
                        if vig['ram_png']:
                            try:
                                vig['ram_png'].seek(0)
                                
                                # Creiamo una tabella a cella singola per simulare il box contenitore scuro
                                table = doc.add_table(rows=2, cols=1)
                                table.autofit = False
                                table.columns[0].width = Inches(6.5)
                                
                                # Cella 1: L'Immagine del fumetto
                                cell_img = table.cell(0, 0)
                                p_img = cell_img.paragraphs[0]
                                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                p_img.add_run().add_picture(vig['ram_png'], width=Inches(6.2))
                                
                                # Cella 2: La didascalia (Sfondo Nero, Testo Bianco Monospace)
                                cell_cap = table.cell(1, 0)
                                
                                # Coloriamo lo sfondo della cella di nero tramite XML interno di Word
                                shading_xml = parse_xml(r'<w:shd {} w:fill="000000"/>'.format(nsdecls('w')))
                                cell_cap._tc.get_or_add_tcPr().append(shading_xml)
                                
                                p_cap = cell_cap.paragraphs[0]
                                p_cap.paragraph_format.left_indent = Inches(0.2)
                                p_cap.paragraph_format.right_indent = Inches(0.2)
                                
                                run_title = p_cap.add_run(f"{vig['titolo'].upper()} - ")
                                run_title.font.name = 'Courier New'
                                run_title.font.size = Pt(11)
                                run_title.font.bold = True
                                run_title.font.color.rgb = RGBColor(69, 243, 255) # Colore Ciano
                                
                                run_text = p_cap.add_run(vig['dialogo'].upper())
                                run_text.font.name = 'Courier New'
                                run_text.font.size = Pt(11)
                                run_text.font.bold = True
                                run_text.font.color.rgb = RGBColor(255, 255, 255) # Testo Bianco
                                
                                doc.add_paragraph("\n") # Spaziatore tra le tavole
                            except Exception as word_err:
                                print(f"Errore inserimento Word: {word_err}")
                    
                    # Salviamo il documento Word dentro un flusso di byte in RAM
                    word_buffer = BytesIO()
                    doc.save(word_buffer)
                    word_buffer.seek(0)
                    word_bytes = word_buffer.getvalue()

                # --- PULSANTI DI DOWNLOAD FORMATTATI SULL'INTERFACCIA ---
                st.balloons()
                st.success(f"🎉 Il tuo libro a fumetti esteso ({len(vignette_renderizzate)} vignette) è pronto!")
                
                # Visualizziamo i due bottoni affiancati
                dl_col1, dl_col2 = st.columns(2)
                
                with dl_col1:
                    st.download_button(
                        label="📥 SCARICA IL LIBRO IN PDF (PAGINE PRONTE STAMPA)",
                        data=pdf_bytes,
                        file_name="mio_libro_a_fumetti.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                with dl_col2:
                    st.download_button(
                        label="📝 SCARICA IL LIBRO IN WORD (.DOCX EDITABILE)",
                        data=word_bytes,
                        file_name="mio_libro_a_fumetti.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
