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
                temperature=0.3,
                max_tokens=1500
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error al generar respuesta: {e}", exc_info=True)
            return "❌ Ocurrió un error al generar la respuesta."

    def comparar_respuestas(self, respuesta_ia, respuesta_usuario):
        vectorizer = TfidfVectorizer().fit_transform([respuesta_ia, respuesta_usuario])
        similarity = cosine_similarity(vectorizer[0:1], vectorizer[1:2])
        return round(float(similarity[0][0]), 2)

    
    def generar_caso_de_uso(self, texto_pdf):

        prompt = f"""
        Como consultor experto en normativas técnicas, genera UN CASO DE USO REALISTA basado en este documento.
        El formato debe ser:

        [CONTEXTO EMPRESARIAL]
        - Tipo de organización (ej: empresa de software médio, consultora TI multinacional)
        - Sector industrial (ej: financiero, salud, gobierno)
        - Situación actual (1-2 oraciones)

        [PROBLEMA CONCRETO]
        - Descripción detallada del problema que requiere aplicar esta normativa
        - Consecuencias de no resolverlo (ej: multas, pérdida de contratos)
        - Necesidad específica que justifica usar este estándar

        Reglas:
        1. Máximo 2 párrafos (6-8 oraciones total)
        2. Basado estrictamente en el ámbito de aplicación del documento
        3. Usar ejemplos realistas (no hipotéticos)
        4. Sin lenguaje técnico complejo
        5. Incluir datos contextuales específicos (tamaño empresa, ubicación, etc.)

        Ejemplo:
        "Una consultora de TI en Quito con 50 empleados necesita evaluar sus procesos de desarrollo para participar en una licitación del Ministerio de Salud que exige certificación SPICE Nivel 3. Actualmente tienen evaluaciones inconsistentes entre proyectos, lo que ha causado rechazo en 3 licitaciones internacionales el último año."

        Documento normativo:
        {texto_pdf[:8000]}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,  # Balance realismo/creatividad
                max_tokens=400,
                top_p=0.9
            )
            caso = response.choices[0].message.content
            
            # Post-procesamiento para asegurar formato
            return caso.replace("**", "").replace("- ", "").strip()
            
        except Exception as e:
            logging.error(f"Error al generar caso real: {e}")
            return "No se pudo generar el caso. Por favor ingrésalo manualmente."
        
    def evaluar_calidad_respuestas(self, texto_pdf: str, pregunta: str, respuesta_azure: str, respuesta_gemini: str, respuesta_usuario: str) -> dict:

        # 1. Comparación textual local
        sim_azure = self.comparar_respuestas(respuesta_azure, respuesta_usuario)
        sim_gemini = self.comparar_respuestas(respuesta_gemini, respuesta_usuario)
        
        # 2. Evaluación cualitativa mejorada
        prompt = f"""
        Evalúa estas respuestas según 3 criterios (0-100%):
        - Coherencia normativa: Alineación con estándares
        - Precisión técnica: Exactitud técnica
        - Aplicabilidad práctica: Utilidad real

        [CONTEXTO]
        Documento: {texto_pdf[:3000]}...
        Pregunta: {pregunta}

        [RESPUESTAS]
        - Azure: {respuesta_azure[:500]}...
        - Gemini: {respuesta_gemini[:500]}...
        - Usuario: {respuesta_usuario[:500]}...

        Devuelve SOLO JSON con:
        {{
            "puntuaciones": {{
                "azure": {{"coherencia": 0-100, "precision": 0-100, "aplicabilidad": 0-100}},
                "gemini": {{"coherencia": 0-100, "precision": 0-100, "aplicabilidad": 0-100}},
                "usuario": {{"coherencia": 0-100, "precision": 0-100, "aplicabilidad": 0-100}}
            }},
            "analisis": "Comparación concisa (2-3 oraciones)",
            "mejor_respuesta": "azure|gemini|usuario"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            evaluacion = json.loads(response.choices[0].message.content)

            return {
                "similarity_azure": sim_azure,
                "similarity_gemini": sim_gemini,
                "puntuaciones": evaluacion.get("puntuaciones", {}),
                "analisis": evaluacion.get("analisis", ""),
                "mejor_respuesta": evaluacion.get("mejor_respuesta", "")
            }

        except Exception as e:
            logging.error(f"Error en evaluación cualitativa: {str(e)}")
            return {
                "similarity_azure": sim_azure,
                "similarity_gemini": sim_gemini,
                "error": "Error en evaluación cualitativa"
            }

    def combinar_respuestas(self, texto_pdf: str, respuesta_azure: str, respuesta_gemini: str, respuesta_usuario: str) -> str:
        """
        Combina las respuestas en un análisis integrado y bien redactado.
        """
        resumen_azure = respuesta_azure[:200] + "..." if len(respuesta_azure) > 200 else respuesta_azure
        resumen_gemini = respuesta_gemini[:200] + "..." if len(respuesta_gemini) > 200 else respuesta_gemini
        resumen_usuario = respuesta_usuario[:200] + "..." if len(respuesta_usuario) > 200 else respuesta_usuario

        prompt = f"""
        **Objetivo**: Genera un análisis integrado que combine las perspectivas clave de las 3 respuestas, 
        priorizando claridad y coherencia normativa. Sigue estas instrucciones:

        1. **Contexto**: Usa el documento base como referencia principal.
        2. **Síntesis**: Integra los aportes únicos de cada fuente:
        - Azure: Fortalezas técnicas
        - Gemini: Perspectiva contextual
        - Usuario: Enfoque práctico/normativo
        3. **Formato**:
        - Párrafo introductorio (2-3 líneas).
        - 3-5 ideas principales (cada una con 1-2 oraciones).
        - Conclusión breve (opcional).
        4. **Estilo**: Lenguaje formal pero fluido, como un informe técnico-jurídico.

        [DOCUMENTO BASE]: {texto_pdf[:1000]}...
        [RESUMEN AZURE]: {resumen_azure}
        [RESUMEN GEMINI]: {resumen_gemini}
        [RESUMEN USUARIO]: {resumen_usuario}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Un poco más creativo
                max_tokens=400    # Permite mayor desarrollo
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error al combinar respuestas: {str(e)}")
            return "❌ Error al generar la solución combinada"
