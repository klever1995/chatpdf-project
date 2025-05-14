import React, { useState } from 'react';
import './App.css';
import logo from './logo.png';

function App() {
  // Estados para carga de PDF
  const [file, setFile] = useState(null);
  const [pdfText, setPdfText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Estados para generación de caso de uso y solución
  const [useCase, setUseCase] = useState('');
  const [userSolution, setUserSolution] = useState('');
  const [activeStep, setActiveStep] = useState('upload');

  // Estados para mostrar las tres soluciones 
  const [azureResponse, setAzureResponse] = useState('');
  const [geminiResponse, setGeminiResponse] = useState('');
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
  const [combinedResponse, setCombinedResponse] = useState('');
  const [showDownloadButton, setShowDownloadButton] = useState(false);
  const BASE_URL = "https://f653-201-183-101-131.ngrok-free.app";

  //Estados de las comparaciones
  const [similarityScores, setSimilarityScores] = useState({
    azure: null,
    gemini: null,
    qualitative: null
  });

  // Agrega esto con las demás funciones del componente
  const interpretSimilarity = (score) => {
    if (score >= 0.9) return "Coincidencia casi exacta";
    if (score >= 0.7) return "Alta coincidencia"; 
    if (score >= 0.5) return "Coincidencia moderada";
    if (score >= 0.3) return "Baja coincidencia";
    return "Muy poca coincidencia";
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    if (!file) {
      setError("Por favor selecciona un archivo PDF.");
      setIsLoading(false);
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${BASE_URL}/upload_pdf/`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || "Error al procesar el PDF");
      }

      setPdfText(data.text);
      setActiveStep('useCase');
    } catch (error) {
      setError(error.message);
      console.error("Error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateUseCase = async (autoGenerate = true) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${BASE_URL}/generate_use_case/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          pdf_text: pdfText,
          generate_automatically: autoGenerate
        })
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || "Error al generar caso de uso");
      }

      setUseCase(data.use_case || '');
    } catch (error) {
      setError(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleContinueToAnalysis = () => {
    if (!useCase.trim()) {
      setError("Por favor genera o escribe un caso de uso");
      return;
    }
    setActiveStep('analysis');
  };

  const handleSolutionSubmit = async () => {
    if (!userSolution.trim()) {
      setError("Por favor ingresa tu solución");
      return;
    }
  
    setComparisonLoading(true);
    setError(null);
    setShowComparison(false); // Asegurar que no se muestre comparación inicialmente
  
    try {
      // Solo obtener respuestas (parte rápida)
      const [azureRes, geminiRes] = await Promise.all([
        fetch(`${BASE_URL}/solve_case/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            pdf_text: pdfText,
            scenario: useCase
          })
        }),
        fetch(`${BASE_URL}/solve_case_gemini/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            pdf_text: pdfText,
            escenario: useCase
          })
        })
      ]);
  
      const azureData = await azureRes.json();
      const geminiData = await geminiRes.json();
  
      if (!azureRes.ok || !geminiRes.ok) {
        throw new Error(azureData.detail || geminiData.detail || "Error al generar respuestas");
      }
  
      setAzureResponse(azureData.ai_response);
      setGeminiResponse(geminiData.gemini_response);
      setActiveStep('comparison');
  
    } catch (error) {
      setError(error.message);
    } finally {
      setComparisonLoading(false);
    }
  };
  
  // Añade esta NUEVA función justo después:
  const handleCompareSolutions = async () => {
    setComparisonLoading(true);
    try {
      const [azureCompare, geminiCompare, qualitativeEval] = await Promise.all([
        fetch(`${BASE_URL}/compare_responses/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            ai_response: azureResponse,
            user_response: userSolution
          })
        }),
        fetch(`${BASE_URL}/compare_gemini_response/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            gemini_response: geminiResponse,
            user_response: userSolution
          })
        }),
        fetch(`${BASE_URL}/evaluate_three_responses/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            pdf_text: pdfText,
            question: useCase,
            azure_response: azureResponse,
            gemini_response: geminiResponse,
            user_response: userSolution
          })
        })
      ]);
  
      const azureCompareData = await azureCompare.json();
      const geminiCompareData = await geminiCompare.json();
      const qualitativeData = await qualitativeEval.json();
  
      setSimilarityScores({
        azure: azureCompareData.similarity,
        gemini: geminiCompareData.similarity,
        qualitative: qualitativeData
      });
  
      setShowComparison(true);
    } catch (error) {
      setError(error.message);
    } finally {
      setComparisonLoading(false);
    }
  };

  const handleCombineResponses = async () => {
    try {
      const response = await fetch(`${BASE_URL}/combine_responses/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          pdf_text: pdfText,
          azure_response: azureResponse,
          gemini_response: geminiResponse,
          user_response: userSolution
        })
      });
      const data = await response.json();
      setCombinedResponse(data.combined_solution);
      setShowDownloadButton(true); // <- Activa el botón de descarga
    } catch (error) {
      setError("Error al combinar respuestas");
    }
  };

  const generarPDF = async () => {
    try {
      const formData = new FormData();
      formData.append('caso_uso', useCase);
      formData.append('respuesta_usuario', userSolution);
      formData.append('respuesta_azure', azureResponse);
      formData.append('respuesta_gemini', geminiResponse);
      formData.append('respuesta_combinada', combinedResponse);
  
      const response = await fetch(`${BASE_URL}/descargar-reporte/`, {
        method: 'POST',
        body: formData  // ¡Importante! No incluir headers 'Content-Type'
      });
  
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "reporte_final.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      } else {
        throw new Error('Error al descargar PDF');
      }
    } catch (error) {
      console.error("Error:", error);
      setError("No se pudo descargar el PDF");
    }
  };
  

  return (
    <div className="App">
      <header className="app-header">
        <div className="university-info">
          <div className="logo-and-name">
            <img src={logo} alt="Logo Universidad" className="university-logo"/>
            <div className="university-text">
              <h2 className="university-name">Universidad Central del Ecuador</h2>
              <p className="course-info">Grupo 4 - Legislación</p>
            </div>
          </div>
        </div>
        <h1>📄 ChatPDF Comparador de Respuestas</h1>
        <p>Sube un documento PDF para comenzar el análisis.</p>
      </header>
  
      <main className="content">
        {/* Paso 1: Subir PDF */}
        {activeStep === 'upload' && (
          <section className="upload-section">
            <h2>Sube tu archivo PDF</h2>
            {error && <div className="error-message">{error}</div>}
            <form onSubmit={handleSubmit} className="upload-form">
              <input
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                className="file-input"
                required
              />
              <button 
                type="submit" 
                className="submit-button" 
                disabled={isLoading}
              >
                {isLoading ? 'Procesando...' : 'Subir PDF'}
              </button>
            </form>
          </section>
        )}
  
        {/* Paso 2: Generar caso de uso */}
        {activeStep === 'useCase' && (
          <section className="use-case-section">
            <h2>Generar caso de uso</h2>
            {error && <div className="error-message">{error}</div>}
            
            <div className="use-case-options">
              <button 
                onClick={() => handleGenerateUseCase(true)}
                className="generate-button"
                disabled={isLoading}
              >
                {isLoading ? 'Generando...' : '🪄 Generar automáticamente con IA'}
              </button>
              
              <p className="or-divider">─ o ─</p>
              
              <textarea
                value={useCase}
                onChange={(e) => setUseCase(e.target.value)}
                placeholder="Escribe manualmente tu caso de uso aquí..."
                className="use-case-input"
              />
            </div>
            
            <div className="action-buttons">
              <button 
                onClick={() => setActiveStep('upload')}
                className="back-button"
              >
                Volver
              </button>
              
              <button 
                onClick={handleContinueToAnalysis}
                className="submit-button"
                disabled={isLoading || !useCase.trim()}
              >
                Continuar al análisis
              </button>
            </div>
          </section>
        )}
  
        {/* Paso 3: Ingresar solución */}
        {activeStep === 'analysis' && (
          <section className="analysis-section">
            <h2>Análisis de solución</h2>
            {error && <div className="error-message">{error}</div>}
  
            <div className="case-review">
              <h3>Tu caso de uso:</h3>
              <div className="case-content">
                {useCase.split('\n').map((paragraph, i) => (
                  <p key={i}>{paragraph}</p>
                ))}
              </div>
            </div>
  
            <div className="solution-input">
              <h3>Ingresa tu solución:</h3>
              <textarea
                value={userSolution}
                onChange={(e) => setUserSolution(e.target.value)}
                placeholder="Escribe tu respuesta detallada aquí..."
                className="solution-textarea"
              />
            </div>
  
            <div className="action-buttons">
              <button 
                onClick={() => setActiveStep('useCase')}
                className="back-button"
              >
                Volver
              </button>
              
              <button 
                onClick={handleSolutionSubmit}
                className="submit-button"
                disabled={!userSolution.trim() || comparisonLoading}
              >
                {comparisonLoading ? 'Comparando...' : 'Continuar'}
              </button>
            </div>
          </section>
        )}
  
        {/* Paso 4: Comparación de soluciones */}
        {activeStep === 'comparison' && (
          <section className="comparison-section">
            <h2>Comparación de soluciones</h2>
            {error && <div className="error-message">{error}</div>}

            {/* Mostrar siempre las soluciones */}
            <div className="solutions-grid">
              <div className="solution-card">
                <h3>✍️ Tu solución</h3>
                <div className="solution-content">
                  {userSolution.split('\n').map((p, i) => <p key={i}>{p}</p>)}
                </div>
              </div>
              <div className="solution-card">
                <h3>🤖 Azure AI</h3>
                <div className="solution-content">
                  {azureResponse.split('\n').map((p, i) => <p key={i}>{p}</p>)}
                </div>
              </div>
              <div className="solution-card">
                <h3>🔮 Gemini</h3>
                <div className="solution-content">
                  {geminiResponse.split('\n').map((p, i) => <p key={i}>{p}</p>)}
                </div>
              </div>
            </div>

            {/* Contenedor de acciones con ambos botones */}
            <div className="comparison-actions">
              <button 
                onClick={() => {
                  setActiveStep('analysis');
                  setShowComparison(false);
                }}
                className="back-button"
              >
                Volver
              </button>
              
              {/* Botón de comparar solo si no se ha mostrado la comparación */}
              {/* Botón de comparar (solo visible ANTES de mostrar resultados) */}
              {!showComparison && (
                <button 
                  onClick={handleCompareSolutions}
                  className="compare-button"
                  disabled={comparisonLoading}
                >
                  {comparisonLoading ? 'Comparando...' : 'Comparar Soluciones'}
                </button>
              )}

              {/* Botón de combinar (solo visible DESPUÉS de mostrar resultados) */}
              {showComparison && (
                <button 
                  onClick={handleCombineResponses}
                  className="submit-button"
                >
                  Combinar Mejores Puntos
                </button>
              )}
            </div>

            {/* Mostrar gráficos solo si showComparison es true */}
            {showComparison && (
              <>
              <h3 className="textual-title">Análisis Textual</h3> {/* Título agregado */}
              <div className="textual-comparison">
                <div className="similarity-chart">
                  <h4>Similitud con Azure AI</h4>
                  <div className="circle-chart" style={{ 
                    background: `conic-gradient(#4299e1 ${similarityScores.azure * 100}%, #e2e8f0 0)` 
                  }}>
                    <span>{Math.round(similarityScores.azure * 100)}%</span>
                  </div>
                  <p>{interpretSimilarity(similarityScores.azure)}</p>
                </div>
                <div className="similarity-chart">
                  <h4>Similitud con Gemini</h4>
                  <div className="circle-chart" style={{ 
                    background: `conic-gradient(#ed8936 ${similarityScores.gemini * 100}%, #e2e8f0 0)` 
                  }}>
                    <span>{Math.round(similarityScores.gemini * 100)}%</span>
                  </div>
                  <p>{interpretSimilarity(similarityScores.gemini)}</p>
                </div>
              </div>
            </>
          )}

            {showComparison && similarityScores.qualitative && (
              <div className="qualitative-analysis">
                <h3>Análisis Cualitativo</h3>
                
                <div className="qualitative-metrics">
                  <div className="metric">
                    <h4>Coherencia Normativa</h4>
                    <div className="bars-container">
                      <div className="bar-wrapper">
                        <span className="label">Azure</span>
                        <div className="bar-background">
                          <div 
                            className="bar azure-bar" 
                            style={{ width: `${similarityScores.qualitative.puntuaciones.azure.coherencia}%` }}
                          >
                            <span className="percentage">{similarityScores.qualitative.puntuaciones.azure.coherencia}%</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="bar-wrapper">
                        <span className="label">Gemini</span>
                        <div className="bar-background">
                          <div 
                            className="bar gemini-bar" 
                            style={{ width: `${similarityScores.qualitative.puntuaciones.gemini.coherencia}%` }}
                          >
                            <span className="percentage">{similarityScores.qualitative.puntuaciones.gemini.coherencia}%</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="bar-wrapper">
                        <span className="label">Tu Respuesta</span>
                        <div className="bar-background">
                          <div 
                            className="bar user-bar" 
                            style={{ width: `${similarityScores.qualitative.puntuaciones.usuario.coherencia}%` }}
                          >
                            <span className="percentage">{similarityScores.qualitative.puntuaciones.usuario.coherencia}%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Repetir para Precisión y Aplicabilidad */}
                </div>
                
                <div className="qualitative-feedback">
                  <h4>Evaluación Comparativa</h4>
                  <p>{similarityScores.qualitative.analisis}</p>
                  
                  <div className="best-response">
                    <strong>Mejor respuesta:</strong> 
                    <span className={`tag ${
                      similarityScores.qualitative.mejor_respuesta === 'azure' ? 'azure-tag' :
                      similarityScores.qualitative.mejor_respuesta === 'gemini' ? 'gemini-tag' :
                      'user-tag'
                    }`}>
                      {similarityScores.qualitative.mejor_respuesta === 'azure' ? 'Azure AI' :
                      similarityScores.qualitative.mejor_respuesta === 'gemini' ? 'Gemini' : 'Tu respuesta'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {combinedResponse && (
              <div className="combined-solution">
                <h3><span style={{ color: "#6b46c1" }}>✨</span> Solución Combinada</h3>
                <div className="solution-content">
                  {combinedResponse.split('\n').map((p, i) => <p key={i}>{p}</p>)}
                </div>

                {/* Botón de descarga (solo visible después de combinar) */}
                {showDownloadButton && (
                  <button 
                    onClick={() => generarPDF()} 
                    className="download-button"
                    style={{ marginTop: '20px', backgroundColor: '#4CAF50' }}
                  >
                    📥 Descargar PDF con Reporte
                  </button>
                )}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
    
  );
}

export default App;