import google.generativeai as genai
import logging
import os
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

load_dotenv()

class ConsultaIA_Gemini:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")  # Clave desde .env (¡nunca hardcodeada!)
        self.model_name = "gemini-1.5-flash"  # Modelo a usar
        
        if not self.api_key:
            logging.error("❌ Falta la API Key de Gemini en variables de entorno.")
            raise ValueError("GEMINI_API_KEY no configurada.")

        # Configuración inicial
        genai.configure(api_key=self.api_key)

    def generar_respuesta(self, texto_pdf: str, escenario: str) -> str:
        
        try:
            prompt = f"""
            Eres un experto en análisis normativo. Basa tu respuesta EXCLUSIVAMENTE en este documento:
            
            --- TEXTO NORMATIVO ---
            {texto_pdf}
            --- FIN DEL DOCUMENTO ---
            
            Escenario a resolver:
            {escenario}
            
            Instrucciones:
            1. Analiza el documento completo
            2. Identifica artículos/secciones aplicables
            3. Fundamenta tu respuesta citando los fragmentos relevantes
            4. Si el escenario no está regulado, indícalo claramente
            5. Estructura tu respuesta en:
            - Base legal (artículos aplicables)
            - Interpretación técnica
            - Recomendación práctica
            
            Respuesta:
            """
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            else:
                logging.warning("⚠️ Gemini no devolvió contenido válido.")
                return "No se pudo generar respuesta basada en la normativa."
                
        except Exception as e:
            logging.error(f"Error en Gemini: {e}")
            return "❌ Error al consultar la normativa con Gemini."
        
    def comparar_respuestas(self, respuesta_gemini: str, respuesta_usuario: str) -> float:

        try:
            vectorizer = TfidfVectorizer().fit_transform([respuesta_gemini, respuesta_usuario])
            similarity = cosine_similarity(vectorizer[0:1], vectorizer[1:2])
            return round(float(similarity[0][0]), 2)
        except Exception as e:
            logging.error(f"Error al comparar respuestas: {e}")
            return 0.0  # Devuelve 0 si hay error