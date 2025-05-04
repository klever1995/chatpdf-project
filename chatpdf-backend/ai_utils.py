import os
import logging
from openai import AzureOpenAI
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import json


load_dotenv()

class Consulta_ia_openai:
    def __init__(self):        
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://recursoazureopenaimupi.openai.azure.com/")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_version = "2024-08-01-preview"
        self.model_name = "gpt-4o"

        if not self.api_key:
            logging.error("❌ No se encontró la clave de API de OpenAI en variables de entorno.")
            raise EnvironmentError("Falta la clave de API de OpenAI.")

        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.azure_endpoint
        )

    def generar_respuesta(self, texto_pdf, escenario):
        prompt = (
            f"Según el siguiente contenido del documento:\n\n"
            f"{texto_pdf}\n\n"
            f"Responde al siguiente escenario aplicado a este contenido:\n\n"
            f"{escenario}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error al generar respuesta: {e}", exc_info=True)
            return "❌ Ocurrió un error al generar la respuesta."

    def comparar_respuestas(self, respuesta_ia, respuesta_usuario):
        vectorizer = TfidfVectorizer().fit_transform([respuesta_ia, respuesta_usuario])
        similarity = cosine_similarity(vectorizer[0:1], vectorizer[1:2])
        return round(float(similarity[0][0]), 2)

    def evaluar_calidad_respuestas(self, texto_pdf, pregunta, respuesta_ia, respuesta_usuario):
        """
        Evalúa cualitativamente ambas respuestas comparándolas con el contenido del PDF.
        
        Args:
            texto_pdf (str): Texto extraído del PDF
            pregunta (str): Pregunta original que se hizo
            respuesta_ia (str): Respuesta generada por la IA
            respuesta_usuario (str): Respuesta proporcionada por el usuario
            
        Returns:
            dict: {
                "precision_ia": float (0-1),
                "precision_usuario": float (0-1),
                "feedback": str,
                "ambas_correctas": bool
            }
        """
        prompt = f"""
        Eres un experto evaluador técnico. Analiza las siguientes respuestas en base al documento de referencia.
        
        Documento:
        {texto_pdf}
        
        Pregunta:
        {pregunta}
        
        Respuesta del Asistente:
        {respuesta_ia}
        
        Respuesta del Usuario:
        {respuesta_usuario}
        
        Evalúa:
        1. ¿La respuesta del asistente es técnica y factualmente correcta según el documento? (0-1)
        2. ¿La respuesta del usuario es técnica y factualmente correcta según el documento? (0-1)
        3. Proporciona feedback detallado comparando ambas respuestas.
        
        Devuelve SOLO un objeto JSON con las claves:
        - "precision_ia"
        - "precision_usuario"
        - "feedback"
        - "ambas_correctas" (booleano)
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Eres un evaluador técnico objetivo. Devuelve solo JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Más determinista para evaluaciones
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # Parsear la respuesta JSON
            evaluacion = json.loads(response.choices[0].message.content)
            return evaluacion
            
        except Exception as e:
            logging.error(f"Error al evaluar respuestas: {e}", exc_info=True)
            return {
                "precision_ia": 0,
                "precision_usuario": 0,
                "feedback": "❌ Error al evaluar las respuestas",
                "ambas_correctas": False
            }