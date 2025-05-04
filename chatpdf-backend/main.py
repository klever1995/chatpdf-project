from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pdf_utils import extract_text_from_pdf
from ai_utils import Consulta_ia_openai
import os
import logging
from typing import Optional

app = FastAPI()
ai = Consulta_ia_openai()

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
    
@app.post("/evaluate_responses/")
async def evaluate_responses(
    pdf_text: str = Form(...),
    question: str = Form(...),
    ai_response: str = Form(...),
    user_response: str = Form(...)
):
    try:
        if not all([pdf_text.strip(), question.strip(), ai_response.strip(), user_response.strip()]):
            raise HTTPException(
                status_code=400,
                detail="Todos los campos deben contener texto"
            )

        evaluation = ai.evaluar_calidad_respuestas(
            texto_pdf=pdf_text,
            pregunta=question,
            respuesta_ia=ai_response,
            respuesta_usuario=user_response
        )

        return {
            "ai_score": evaluation["precision_ia"],
            "user_score": evaluation["precision_usuario"],
            "feedback": evaluation["feedback"],
            "both_correct": evaluation["ambas_correctas"],
            "detailed_evaluation": evaluation  
        }

    except Exception as e:
        logging.error(f"Error al evaluar respuestas cualitativamente: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error al evaluar las respuestas cualitativamente"
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