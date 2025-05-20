import { useEffect, useRef, useState } from 'react'
import { FaCheckCircle, FaCode, FaDownload, FaExclamationTriangle, FaGithub, FaMoon, FaRocket, FaServer, FaSpinner, FaSun } from 'react-icons/fa'
import './App.css'

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [endpoints, setEndpoints] = useState([])
  const [projectData, setProjectData] = useState(null)
  const [processingSteps, setProcessingSteps] = useState([
    { id: 'clone', label: 'Cloning repository', completed: false, active: false },
    { id: 'extract', label: 'Extracting API endpoints', completed: false, active: false },
    { id: 'schema', label: 'Generating database schema', completed: false, active: false },
    { id: 'priority', label: 'Prioritizing endpoints', completed: false, active: false },
    { id: 'generate', label: 'Generating backend code (AI)', completed: false, active: false },
    { id: 'postman', label: 'Creating Postman collection', completed: false, active: false },
    { id: 'construct', label: 'Constructing Final codebase', completed: false, active: false }
  ])
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark'
  })
  const eventSourceRef = useRef(null)
  const API_BASE_URL = 'http://localhost:8000'
  const [error, setError] = useState(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  const updateProcessingStep = (status) => {
    if (!status) return
    setProcessingSteps(prevSteps => {
      const updatedSteps = [...prevSteps]
      // Match status to steps and update accordingly
      if (status.includes('Starting code generation')) {
        updateStep(updatedSteps, 'clone', 'active')
      } else if (status.includes('Cloning repository')) {
        updateStep(updatedSteps, 'clone', 'active')
      } else if (status.includes('cloned successfully')) {
        updateStep(updatedSteps, 'clone', 'completed')
        updateStep(updatedSteps, 'extract', 'active')
      } else if (status.includes('Extracting API endpoints')) {
        updateStep(updatedSteps, 'extract', 'active')
      } else if (status.includes('endpoints extracted successfully')) {
        updateStep(updatedSteps, 'extract', 'completed')
        // Activate both schema and priority steps simultaneously
        updateStep(updatedSteps, 'schema', 'active')
        updateStep(updatedSteps, 'priority', 'active')
      } else if (status.includes('Generating database schema')) {
        // When schema generation starts, also start showing priority as active
        updateStep(updatedSteps, 'schema', 'active')
        updateStep(updatedSteps, 'priority', 'active')
      } else if (status.includes('Database schema generated successfully')) {
        // Mark schema as complete but keep priority active
        updateStep(updatedSteps, 'schema', 'completed')
        // Keep priority spinner going
        updateStep(updatedSteps, 'priority', 'active')
      } else if (status.includes('Setting API endpoint priorities')) {
        // Priority step is already active, but ensure it stays that way
        updateStep(updatedSteps, 'priority', 'active')
      } else if (status.includes('endpoints prioritized successfully')) {
        updateStep(updatedSteps, 'priority', 'completed')
        updateStep(updatedSteps, 'generate', 'active')
      } else if (status.includes('Generating backend code')) {
        updateStep(updatedSteps, 'generate', 'active')
      } else if (status.includes('Backend code generated successfully')) {
        updateStep(updatedSteps, 'generate', 'completed')
        updateStep(updatedSteps, 'postman', 'active')
      } else if (status.includes('Postman collection generated successfully')) {
        updateStep(updatedSteps, 'postman', 'completed')
        updateStep(updatedSteps, 'construct', 'active')
      } else if (status.includes('API codebase constructed and zipped successfully')) {
        updateStep(updatedSteps, 'construct', 'completed')
      }
      return updatedSteps
    })
  }

  // Helper function to update a step
  function updateStep(steps, id, state) {
    const index = steps.findIndex(step => step.id === id)
    if (index !== -1) {
      if (state === 'active') {
        steps[index].active = true
        steps[index].completed = false
      } else if (state === 'completed') {
        steps[index].active = false
        steps[index].completed = true
      }
    }
  }

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  const handleClone = async () => {
    if (!repoUrl || loading) return

    // Clear any previous errors
    setError(null);

    setLoading(true)
    setEndpoints([])
    setProjectData(null)

    // Reset all processing steps
    setProcessingSteps(processingSteps.map(step => ({
      ...step,
      completed: false,
      active: false
    })))

    // Close any existing EventSource
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    try {
      const response = await fetch(`${API_BASE_URL}/stream-code-gen`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: repoUrl }),
      })

      if (!response.ok) {
        throw new Error('Failed to start code generation')
      }

      // Get a reader from the response body stream
      const reader = response.body.getReader()
      let decoder = new TextDecoder()
      let buffer = ''

      // Create a custom event handler to process the SSE stream manually
      const processStream = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read()

            if (done) {
              console.log('Stream complete')
              setLoading(false)
              break
            }

            // Convert the chunk to text and add to buffer
            const chunk = decoder.decode(value, { stream: true })
            buffer += chunk

            // Process any complete events in the buffer
            const events = buffer.split('\n\n')
            buffer = events.pop() || '' 

            for (const eventData of events) {
              if (!eventData.trim()) continue

              // Parse the event type and data
              const eventLines = eventData.split('\n')
              let eventType = ''
              let eventContent = ''

              for (const line of eventLines) {
                if (line.startsWith('event: ')) {
                  eventType = line.substring(7)
                } else if (line.startsWith('data: ')) {
                  eventContent = line.substring(6)
                }
              }

              if (!eventType || !eventContent) continue

              // Process the event based on its type
              try {
                const data = JSON.parse(eventContent)

                switch (eventType) {
                  case 'status':
                    // Update the progress steps based on status
                    updateProcessingStep(data.status)
                    break

                  case 'endpoints':
                    if (Array.isArray(data.endpoints)) {
                      const formattedEndpoints = data.endpoints.map(endpoint => ({
                        method: endpoint.method || 'GET',
                        path: endpoint.endpointName || endpoint.path || '',
                        description: endpoint.description || endpoint.summary || ''
                      }))
                      console.log('Received endpoints:', formattedEndpoints)
                      setEndpoints(formattedEndpoints)
                    }
                    break

                  case 'completed':
                    if (data.result) {
                      setProjectData(data.result)
                    }
                    setLoading(false)
                    break

                  case 'error':
                    setError(data.error || 'An unknown error occurred during code generation')
                    setLoading(false)
                    break

                  case 'message_stop':
                    setLoading(false)
                    break
                }

              } catch (error) {
                console.error(`Error parsing ${eventType} event:`, error)
                setError(`Error parsing event data: ${error.message}`)
              }
            }
          }
        } catch (error) {
          console.error('Stream processing error:', error)
          setError(`Stream processing error: ${error.message}`)
          setLoading(false)
        }
      }

      // Start processing the stream
      processStream()

    } catch (error) {
      console.error('Error:', error)
      setError(`Failed to start code generation: ${error.message}`)
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    if (!projectData) return

    try {
      const zipFilePath = projectData.zip_path
      const repoName = projectData.repo_name || 'backend-code'

      if (!zipFilePath) {
        throw new Error('Zip file path not found in project data')
      }

      // Show loading state for download
      setLoading(true)

      // Send POST request to fetch the zip file
      const response = await fetch(`${API_BASE_URL}/fetch-zip`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ zip_path: zipFilePath }),
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`)
      }

      // Get the blob from the response
      const blob = await response.blob()
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob)
      
      // Create a temporary link element to trigger the download
      const a = document.createElement('a')
      a.href = url
      a.download = `${repoName}.zip`
      document.body.appendChild(a)
      a.click()
      
      // Clean up
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      setLoading(false)

    } catch (error) {
      console.error('Download error:', error)
      alert(`Download error: ${error.message}`)
      setLoading(false)
    }
  }

  // Get percentage of completed steps
  const completionPercentage = processingSteps.filter(step => step.completed).length / processingSteps.length * 100

  // Find current active step name
  const currentStep = processingSteps.find(step => step.active)
  const currentStepName = currentStep ? currentStep.label : 'Initializing...'

  return (
    <div className="app-container">
      <div className="theme-toggle" onClick={toggleTheme}>
        {theme === 'dark' ? <FaSun /> : <FaMoon />}
      </div>

      <header>
        <div className="logo-section">
          <div className="logo">
            <div className="icon-container">
              <FaRocket className="rocket-icon" />
            </div>
            <div className="text-container">
              <h1>Engine</h1>
              <p className="tagline">powering rocket</p>
            </div>
          </div>
        </div>
      </header>

      <main>
        <div className="hero-section">
          <h2>Generate backend code from your GitHub repository</h2>
          <p>Instantly transform your frontend project into a fully functional backend</p>
        </div>

        <div className="input-container">
          <div className="input-wrapper">
            <FaGithub className="input-icon" />
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="Enter GitHub repo URL"
              disabled={loading}
            />
          </div>
          <button
            className="clone-button"
            onClick={handleClone}
            disabled={loading || !repoUrl}
          >
            {loading ? (
              <>
                <div className="spinner"></div>
                <span>Processing...</span>
              </>
            ) : (
              <>
                <FaCode className="button-icon" />
                <span>Generate Backend</span>
              </>
            )}
          </button>
        </div>

        <div className="side-by-side-container">
          {loading ? (
            <>
              <div className="left-column">
                <div className="generation-progress">
                  <div className="progress-header">
                    <h2>Generation Progress</h2>
                  </div>

                  <div className="progress-steps">
                    {processingSteps.map(step => (
                      // Only show steps that are active or completed
                      (step.active || step.completed) && (
                        <div key={step.id} className={`progress-step ${step.active ? 'active' : ''} ${step.completed ? 'completed' : ''}`}>
                          {step.completed ? (
                            <FaCheckCircle className="step-icon completed" />
                          ) : step.active ? (
                            <FaSpinner className="step-icon spinning" />
                          ) : (
                            <div className="step-icon empty" />
                          )}
                          <span className="step-label">{step.label}</span>
                        </div>
                      )
                    ))}
                  </div>
                </div>
              </div>
              
              {endpoints.length > 0 && (
                <div className="right-column">
                  <div className="endpoints-container">
                    <div className="endpoints-header">
                      <FaServer className="endpoints-icon" />
                      <h2>API Endpoints Generated</h2>
                      <div className="endpoints-count">{endpoints.length}</div>
                    </div>

                    <div className="endpoints-table-container">
                      <div className="endpoints-table-header">
                        <div className="method-column">METHOD</div>
                        <div className="path-column">ENDPOINT</div>
                        <div className="description-column">DESCRIPTION</div>
                      </div>
                      <div className="endpoints-list">
                        {endpoints.map((endpoint, index) => (
                          <div key={index} className="endpoint-item">
                            <div className="method-column">
                              <span className={`method ${(endpoint.method || 'get').toLowerCase()}`}>
                                {endpoint.method || 'GET'}
                              </span>
                            </div>
                            <div className="path-column">
                              <code className="path">{endpoint.path || 'Unknown path'}</code>
                            </div>
                            <div className="description-column">
                              <p>{endpoint.description || 'No description available'}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            endpoints.length > 0 && (
              <div className="full-width-column">
                <div className="endpoints-container">
                  <div className="endpoints-header">
                    <FaServer className="endpoints-icon" />
                    <h2>API Endpoints Generated</h2>
                    <div className="endpoints-count">{endpoints.length}</div>
                  </div>

                  <div className="endpoints-table-container">
                    <div className="endpoints-table-header">
                      <div className="method-column">METHOD</div>
                      <div className="path-column">ENDPOINT</div>
                      <div className="description-column">DESCRIPTION</div>
                    </div>
                    <div className="endpoints-list">
                      {endpoints.map((endpoint, index) => (
                        <div key={index} className="endpoint-item">
                          <div className="method-column">
                            <span className={`method ${(endpoint.method || 'get').toLowerCase()}`}>
                              {endpoint.method || 'GET'}
                            </span>
                          </div>
                          <div className="path-column">
                            <code className="path">{endpoint.path || 'Unknown path'}</code>
                          </div>
                          <div className="description-column">
                            <p>{endpoint.description || 'No description available'}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )
          )}
        </div>

        {error && (
          <div className="error-container">
            <div className="error-header">
              <FaExclamationTriangle className="error-icon" />
              <h2>Error Occurred</h2>
            </div>
            <div className="error-message">
              <p>{error}</p>
            </div>
          </div>
        )}

        {projectData && (
          <div className="download-container">
            <div className="result-info">
              <div className="success-header">
                <FaCheckCircle className="success-icon" />
                <h2>Backend Code Generated!</h2>
              </div>
              <div className="result-details">
                <p><strong>Project:</strong> {projectData.repo_name}</p>
                <p><strong>Location:</strong> <code>{projectData.zip_path}</code></p>
              </div>
            </div>
            <button
              className="download-button"
              onClick={handleDownload}
              title="Download the generated code as a ZIP file"
            >
              <FaDownload className="button-icon" />
              <span>Download Code</span>
            </button>
          </div>
        )}
      </main>

      <footer>
        <div className="footer-content">
          <div className="footer-logo">
            <div className="icon-container icon-container-small">
              <FaRocket className="rocket-icon" />
            </div>
            <div className="text-container">
              <h3 className="footer-title">Engine</h3>
              <p className="tagline">powering rocket</p>
            </div>
          </div>
          <p>© 2025 Engine - All rights reserved</p>
        </div>
      </footer>
    </div>
  )
}

export default App