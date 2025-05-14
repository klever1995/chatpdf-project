from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pdf_utils import extract_text_from_pdf
from ai_utils import Consulta_ia_openai
from gemini_utils import ConsultaIA_Gemini
import os
import logging
from fpdf import FPDF
from datetime import datetime
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()
ai = Consulta_ia_openai()
ai_gemini = ConsultaIA_Gemini()

# Configuración CORS (ajusta esto en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de directorios
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE_MB = 10  # Límite de 10MB para los PDFs

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Validación del tipo de archivo
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos PDF"
            )

        # Validación del tamaño del archivo
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"El archivo excede el tamaño máximo de {MAX_FILE_SIZE_MB}MB"
            )

        # Guardado temporal del archivo
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(contents)

        # Extracción de texto
        text = extract_text_from_pdf(file_path)
        
        # Eliminación del archivo temporal
        os.remove(file_path)

        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail="No se pudo extraer texto del PDF (puede ser un PDF escaneado o protegido)"
            )

        return {"text": text}

    except Exception as e:
        logging.error(f"Error al procesar PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo: {str(e)}"
        )

@app.post("/solve_case/")
async def solve_case(pdf_text: str = Form(...), scenario: str = Form(...)):
    try:
        if not pdf_text.strip() or not scenario.strip():
            raise HTTPException(
                status_code=400,
                detail="El texto del PDF y el escenario no pueden estar vacíos"
            )

        response = ai.generar_respuesta(pdf_text, scenario)
        return {"ai_response": response}

    except Exception as e:
        logging.error(f"Error al generar respuesta: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error al procesar tu solicitud"
        )

@app.post("/compare_responses/")
async def compare(
    ai_response: str = Form(...),
    user_response: str = Form(...)
):
    try:
        if not ai_response.strip() or not user_response.strip():
            raise HTTPException(
                status_code=400,
                detail="Ambas respuestas deben contener texto"
            )

        similarity_score = ai.comparar_respuestas(ai_response, user_response)
        return {
            "similarity": similarity_score,
            "interpretation": interpret_similarity(similarity_score)
        }

    except Exception as e:
        logging.error(f"Error al comparar respuestas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error al comparar las respuestas"
        )
    
@app.post("/generate_use_case/")
async def generate_use_case(
    pdf_text: str = Form(...),
    generate_automatically: bool = Form(True)  
):
    try:
        if not pdf_text.strip():
            raise HTTPException(status_code=400, detail="El texto del PDF no puede estar vacío")

        if generate_automatically:
            use_case = ai.generar_caso_de_uso(pdf_text)
            if not use_case:
                raise HTTPException(status_code=500, detail="Error al generar caso de uso con IA")
            return {"use_case": use_case, "source": "azure_ai"}
        else:
            return {"use_case": "", "source": "manual"}  

    except Exception as e:
        logging.error(f"Error en /generate_use_case: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al generar caso de uso")
    
@app.post("/compare_gemini_response/")
async def compare_gemini_response(
    gemini_response: str = Form(...),
    user_response: str = Form(...)
):
    """Compara textualmente la respuesta de Gemini con la del usuario"""
    try:
        if not gemini_response.strip() or not user_response.strip():
            raise HTTPException(
                status_code=400,
                detail="Ambas respuestas deben contener texto"
            )

        similarity_score = ai_gemini.comparar_respuestas(gemini_response, user_response)
        return {
            "similarity": similarity_score,
            "interpretation": interpret_similarity(similarity_score)
        }

    except Exception as e:
        logging.error(f"Error al comparar respuestas Gemini: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al comparar respuestas con Gemini"
        )

@app.post("/evaluate_three_responses/")
async def evaluate_three_responses(
    pdf_text: str = Form(...),
    question: str = Form(...),
    azure_response: str = Form(...),
    gemini_response: str = Form(...),
    user_response: str = Form(...)
):
    """Evalúa cualitativamente las 3 respuestas (Azure, Gemini y usuario)"""
    try:
        if not all([pdf_text.strip(), question.strip(), azure_response.strip(), 
                   gemini_response.strip(), user_response.strip()]):
            raise HTTPException(
                status_code=400,
                detail="Todos los campos deben contener texto"
            )

        evaluation = ai.evaluar_calidad_respuestas(
            texto_pdf=pdf_text,
            pregunta=question,
            respuesta_azure=azure_response,
            respuesta_gemini=gemini_response,
            respuesta_usuario=user_response
        )

        return evaluation

    except Exception as e:
        logging.error(f"Error al evaluar tres respuestas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al evaluar las tres respuestas"
        )

@app.post("/combine_responses/")
async def combine_responses(
    pdf_text: str = Form(...),
    azure_response: str = Form(...),
    gemini_response: str = Form(...),
    user_response: str = Form(...)
):
    """Combina las 3 respuestas en una solución integrada"""
    try:
        if not all([pdf_text.strip(), azure_response.strip(), 
                   gemini_response.strip(), user_response.strip()]):
            raise HTTPException(
                status_code=400,
                detail="Todos los campos deben contener texto"
            )

        combined = ai.combinar_respuestas(
            texto_pdf=pdf_text,
            respuesta_azure=azure_response,
            respuesta_gemini=gemini_response,
            respuesta_usuario=user_response
        )

        return {"combined_solution": combined}

    except Exception as e:
        logging.error(f"Error al combinar respuestas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al combinar las soluciones"
        )
    
@app.post("/solve_case_gemini/")
async def solve_case_gemini(pdf_text: str = Form(...), escenario: str = Form(...)):
    try:
        if not pdf_text.strip():
            raise HTTPException(
                status_code=400,
                detail="El texto del PDF no puede estar vacío"
            )
        if not escenario.strip():
            raise HTTPException(
                status_code=400,
                detail="El escenario no puede estar vacío"
            )

        response = ai_gemini.generar_respuesta(pdf_text, escenario)
        return {"gemini_response": response}

    except Exception as e:
        logging.error(f"Error al generar respuesta normativa con Gemini: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error al interpretar la normativa con Gemini"
        )
    
def interpret_similarity(score: float) -> str:
    """Ayuda a interpretar el puntaje de similitud"""
    if score >= 0.9:
        return "Coincidencia casi exacta"
    elif score >= 0.7:
        return "Alta coincidencia"
    elif score >= 0.5:
        return "Coincidencia moderada"
    elif score >= 0.3:
        return "Baja coincidencia"
    else:
        return "Muy poca coincidencia"
    
@app.post("/descargar-reporte/")
async def descargar_reporte(
    caso_uso: str = Form(...),
    respuesta_usuario: str = Form(...),
    respuesta_azure: str = Form(...),
    respuesta_gemini: str = Form(...),
    respuesta_combinada: str = Form(...),
    guardar_local: bool = Form(False)
):
    try:
        # 1. Validación de campos
        if not all([caso_uso, respuesta_usuario, respuesta_azure, respuesta_gemini, respuesta_combinada]):
            raise HTTPException(status_code=400, detail="Todos los campos deben contener texto")

        # 2. Cargar prompts con valores por defecto
        prompt_caso_uso = "Genera un caso de uso basado en el documento normativo"
        prompt_combinar = "Combina las mejores partes de las respuestas proporcionadas"
        
        prompts_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
        if os.path.exists(prompts_path):
            try:
                with open(prompts_path, "r", encoding="utf-8") as f:
                    prompts = f.read().split("#")
                    if len(prompts) > 1:
                        prompt_caso_uso = prompts[1].strip()
                    if len(prompts) > 3:
                        prompt_combinar = prompts[3].strip()
            except Exception as e:
                logging.warning(f"No se pudo leer prompts.txt: {str(e)}")

        # 3. Configuración inicial del PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(left=15, top=15, right=15)
        pdf.set_font("Arial", size=10)

        # Función para manejar texto largo
        def write_long_text(text, font_size=10):
            pdf.set_font("Arial", size=font_size)
            try:
                text = str(text).encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(w=180, h=6, txt=text, border=0, align='L')
            except Exception as e:
                pdf.multi_cell(w=180, h=6, txt="Error al procesar este texto", border=0, align='L')
            pdf.ln(4)

        # Encabezado
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="Reporte de Análisis Normativo", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt=f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        pdf.ln(15)

        # Secciones del PDF
        sections = [
            ("1. Caso de Uso Generado", [
                ("Prompt utilizado:", prompt_caso_uso),
                ("Caso de uso generado:", caso_uso)
            ]),
            ("2. Comparación de Respuestas", [
                ("✍️ Tu respuesta:", respuesta_usuario),
                ("🤖 Azure OpenAI:", respuesta_azure),
                ("🔮 Gemini:", respuesta_gemini)
            ]),
            ("3. Solución Combinada", [
                ("Prompt utilizado:", prompt_combinar),
                ("💡 Respuesta combinada:", respuesta_combinada)
            ])
        ]

        for section_title, items in sections:
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt=section_title, ln=True)
            pdf.ln(5)
            
            for item_title, item_text in items:
                pdf.set_font("Arial", 'B', 10)
                write_long_text(item_title)
                pdf.set_font("Arial", size=10)
                write_long_text(item_text)
                pdf.ln(5)
            pdf.ln(10)

        # Guardado del PDF
        filename = f"reporte_analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        temp_path = os.path.join(os.path.dirname(__file__), filename)
        
        if guardar_local:
            downloads_path = str(Path.home() / "Downloads")
            local_path = os.path.join(downloads_path, filename)
            pdf.output(local_path)
            logging.info(f"PDF guardado localmente en: {local_path}")

        pdf.output(temp_path)
        return FileResponse(temp_path, filename=filename, media_type="application/pdf")

    except Exception as e:
        logging.error(f"Error al generar PDF: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el reporte en PDF: {str(e)}"
        )