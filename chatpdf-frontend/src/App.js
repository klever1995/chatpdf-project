import React, { useState } from 'react';
import './App.css';
import logo from './logo.png';

function App() {
  const [file, setFile] = useState(null);
  const [pdfText, setPdfText] = useState('');
  const [scenario, setScenario] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [userResponse, setUserResponse] = useState('');
  const [similarity, setSimilarity] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('upload');

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    if (!file) {
      alert("Por favor selecciona un archivo PDF.");
      setIsLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch("http://127.0.0.1:8000/upload_pdf/", {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      
      if (response.ok) {
        setPdfText(data.text);
        setActiveTab('scenario');
      } else {
        alert("Hubo un problema al subir el archivo.");
      }
    } catch (error) {
      console.error("Error al subir el archivo:", error);
      alert("Error al subir el archivo.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleScenarioSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    if (!scenario.trim()) {
      alert("Por favor ingresa un escenario válido.");
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/solve_case/", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          pdf_text: pdfText,
          scenario: scenario
        })
      });

      const data = await response.json();
      
      if (response.ok) {
        setAiResponse(data.ai_response);
        setActiveTab('response');
      } else {
        alert("Hubo un problema al procesar el escenario.");
      }
    } catch (error) {
      console.error("Error al procesar el escenario:", error);
      alert("Error al procesar el escenario.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompareSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    if (!userResponse.trim()) {
      alert("Por favor ingresa tu respuesta.");
      setIsLoading(false);
      return;
    }

    try {
      // Primero comparación textual
      const compareResponse = await fetch("http://127.0.0.1:8000/compare_responses/", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          ai_response: aiResponse,
          user_response: userResponse
        })
      });

      const compareData = await compareResponse.json();
      
      if (compareResponse.ok) {
        setSimilarity(compareData.similarity);
        
        // Luego evaluación cualitativa
        const evalResponse = await fetch("http://127.0.0.1:8000/evaluate_responses/", {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: new URLSearchParams({
            pdf_text: pdfText,
            question: scenario,
            ai_response: aiResponse,
            user_response: userResponse
          })
        });

        const evalData = await evalResponse.json();
        
        if (evalResponse.ok) {
          setEvaluation(evalData);
          setActiveTab('comparison');
        } else {
          throw new Error("Error en evaluación cualitativa");
        }
      } else {
        throw new Error("Error en comparación textual");
      }
    } catch (error) {
      console.error("Error al comparar respuestas:", error);
      alert("Error al comparar respuestas.");
    } finally {
      setIsLoading(false);
    }
  };

  const interpretSimilarity = (score) => {
    if (score >= 0.9) return "Coincidencia casi exacta";
    if (score >= 0.7) return "Alta coincidencia";
    if (score >= 0.5) return "Coincidencia moderada";
    if (score >= 0.3) return "Baja coincidencia";
    return "Muy poca coincidencia";
  };

  const renderComparisonResults = () => {
    return (
      <div className="comparison-results">
        <div className="similarity-section">
          <h3>Análisis Textual</h3>
          <div className="score-circle" style={{ 
            backgroundColor: `hsl(${similarity * 120}, 70%, 50%)`
          }}>
            {Math.round(similarity * 100)}%
          </div>
          <p className="interpretation">
            {interpretSimilarity(similarity)}
          </p>
        </div>

        <div className="evaluation-section">
          <h3>Análisis Cualitativo</h3>
          <div className="scores-container">
            <div className="score-box">
              <h4>Precisión IA</h4>
              <div className="score-bar">
                <div 
                  className="score-fill" 
                  style={{ width: `${evaluation.ai_score * 100}%` }}
                >
                  {Math.round(evaluation.ai_score * 100)}%
                </div>
              </div>
            </div>
            
            <div className="score-box">
              <h4>Tu precisión</h4>
              <div className="score-bar">
                <div 
                  className="score-fill" 
                  style={{ width: `${evaluation.user_score * 100}%` }}
                >
                  {Math.round(evaluation.user_score * 100)}%
                </div>
              </div>
            </div>
          </div>

          <div className="feedback-box">
            <h4>Feedback detallado:</h4>
            <p>{evaluation.feedback}</p>
            {evaluation.both_correct && (
              <div className="correct-badge">✅ Ambas respuestas son correctas</div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <header className="app-header">

        {/* Nueva sección institucional */}
  <div className="university-info">
    <div className="logo-and-name">
      <img 
        src={logo}  
        alt="Logo Universidad" 
        className="university-logo"
      />
      <div className="university-text">
        <h2 className="university-name">Universidad Central del Ecuador</h2>
        <p className="course-info">Grupo 4 - Legislación</p>
      </div>
    </div>
  </div>
        <h1>📄 ChatPDF Comparador de Respuestas</h1>
        <p>Sube un documento PDF, plantea un escenario y compara tu solución con la de la IA de Openai.</p>
      </header>

      <main className="content">
        {activeTab === 'upload' && (
          <section className="upload-section">
            <h2>Sube tu archivo PDF</h2>
            <form onSubmit={handleSubmit} className="upload-form">
              <input
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                className="file-input"
                required
              />
              <button type="submit" className="submit-button" disabled={isLoading}>
                {isLoading ? 'Subiendo...' : 'Subir PDF'}
              </button>
            </form>
          </section>
        )}

        {activeTab === 'scenario' && (
          <section className="scenario-section">
            <h2>Plantea tu caso de uso</h2>
            <form onSubmit={handleScenarioSubmit} className="scenario-form">
              <textarea
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                placeholder="Describe el escenario o caso que quieres analizar..."
                className="scenario-input"
                required
              />
              <button type="submit" className="submit-button" disabled={isLoading}>
                {isLoading ? 'Procesando...' : 'Obtener respuesta de la IA'}
              </button>
            </form>
          </section>
        )}

        {activeTab === 'response' && (
          <section className="response-section">
            <h2>Respuesta del ChatPDF</h2>
            <div className="response-box">
              <h3>Tu escenario:</h3>
              <p>{scenario}</p>
              
              <h3>Respuesta de la IA:</h3>
              <div className="ai-response">
                {aiResponse.split('\n').map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
              
              <h3>Tu respuesta:</h3>
              <form onSubmit={handleCompareSubmit}>
                <textarea
                  value={userResponse}
                  onChange={(e) => setUserResponse(e.target.value)}
                  placeholder="Escribe tu respuesta para comparar con la IA..."
                  className="user-input"
                  required
                />
                <div className="button-group">
                  <button 
                    type="button"
                    className="back-button"
                    onClick={() => setActiveTab('scenario')}
                  >
                    Volver
                  </button>
                  <button 
                    type="submit" 
                    className="submit-button "
                    disabled={isLoading}
                  >
                    {isLoading ? 'Comparando...' : 'Comparar respuestas'}
                  </button>
                </div>
              </form>
            </div>
          </section>
        )}

        {activeTab === 'comparison' && (
          <section className="comparison-section">
            <h2>Resultado de la comparación</h2>
            <div className="comparison-box">
              {evaluation && renderComparisonResults()}
              
              <div className="responses-comparison">
                <div className="response-column">
                  <h3>Respuesta de la IA:</h3>
                  <div className="ai-response">
                    {aiResponse.split('\n').map((paragraph, index) => (
                      <p key={index}>{paragraph}</p>
                    ))}
                  </div>
                </div>
                
                <div className="response-column">
                  <h3>Tu respuesta:</h3>
                  <div className="user-response">
                    {userResponse.split('\n').map((paragraph, index) => (
                      <p key={index}>{paragraph}</p>
                    ))}
                  </div>
                </div>
              </div>
              
              <button 
                className="back-button"
                onClick={() => setActiveTab('response')}
              >
                Volver a comparar
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;