import { useEffect, useRef, useState } from 'react'
import { FaCode, FaDownload, FaGithub, FaMoon, FaRocket, FaSun } from 'react-icons/fa'
import './App.css'

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [endpoints, setEndpoints] = useState([])
  const [projectData, setProjectData] = useState(null)
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark'
  })
  const eventSourceRef = useRef(null)
  const API_BASE_URL = 'http://localhost:8000'

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  const handleClone = async () => {
    if (!repoUrl || loading) return

    setLoading(true)
    setStatus('Starting backend generation...')
    setEndpoints([])
    setProjectData(null)

    // Close any existing EventSource
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    try {
      // First make the initial POST request to start the process
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

      // Now connect to SSE stream
      const eventSource = new EventSource(`${API_BASE_URL}/stream-code-gen`)
      eventSourceRef.current = eventSource

      // Listen for different event types
      eventSource.addEventListener('status', (event) => {
        try {
          const data = JSON.parse(event.data)
          setStatus(data.status)
        } catch (error) {
          console.error('Error parsing status event:', error)
        }
      })

      eventSource.addEventListener('endpoints', (event) => {
        try {
          const data = JSON.parse(event.data)
          if (Array.isArray(data.endpoints)) {
            const formattedEndpoints = data.endpoints.map(endpoint => ({
              method: endpoint.method || 'GET',
              path: endpoint.path || '',
              description: endpoint.description || endpoint.summary || ''
            }))
            setEndpoints(formattedEndpoints)
          }
        } catch (error) {
          console.error('Error parsing endpoints event:', error)
        }
      })

      eventSource.addEventListener('completed', (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.result) {
            setProjectData(data.result)
          }
          setLoading(false)
        } catch (error) {
          console.error('Error parsing completed event:', error)
        } finally {
          eventSource.close()
        }
      })

      eventSource.addEventListener('error', (event) => {
        try {
          const data = JSON.parse(event.data)
          setStatus(`Error: ${data.error || 'Unknown error occurred'}`)
        } catch (error) {
          console.error('Error parsing error event:', error)
          setStatus('An error occurred during code generation')
        } finally {
          eventSource.close()
          setLoading(false)
        }
      })

      eventSource.addEventListener('message_stop', () => {
        eventSource.close()
        setLoading(false)
      })

      // Handle general errors
      eventSource.onerror = (error) => {
        console.error('EventSource error:', error)
        setStatus('Error connecting to the server')
        eventSource.close()
        setLoading(false)
      }
    } catch (error) {
      console.error('Error:', error)
      setStatus(`Error: ${error.message}`)
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

      // Make a request to download the file
      window.location.href = `${API_BASE_URL}/download-zip?path=${encodeURIComponent(zipFilePath)}&filename=${encodeURIComponent(repoName)}`

    } catch (error) {
      console.error('Download error:', error)
      setStatus(`Download error: ${error.message}`)
    }
  }

  return (
    <div className="app-container">
      <div className="theme-toggle" onClick={toggleTheme}>
        {theme === 'dark' ? <FaSun /> : <FaMoon />}
      </div>

      <header>
        <div className="logo-section">
          <div className="logo">
            <FaRocket className="rocket-icon" />
            <h1>engine</h1>
          </div>
          <p className="tagline">powering rocket</p>
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

        {loading && (
          <div className="progress-container">
            <div className="progress-bar">
              <div className="progress-fill"></div>
            </div>
          </div>
        )}

        {status && (
          <div className="status-container">
            <h2>Status</h2>
            <div className="status-box">
              <p>{status}</p>
            </div>
          </div>
        )}

        {endpoints.length > 0 && (
          <div className="endpoints-container">
            <h2>Generated API Endpoints</h2>
            <div className="endpoints-list">
              {endpoints.map((endpoint, index) => (
                <div key={index} className="endpoint-item">
                  <span className={`method ${endpoint.method.toLowerCase()}`}>{endpoint.method}</span>
                  <span className="path">{endpoint.path}</span>
                  <span className="description">{endpoint.description}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {projectData && (
          <div className="download-container">
            <button className="download-button" onClick={handleDownload}>
              <FaDownload className="button-icon" />
              <span>Download Generated Code</span>
            </button>
          </div>
        )}
      </main>

      <footer>
        <div className="footer-content">
          <div className="footer-logo">
            <FaRocket className="rocket-icon-small" />
            <span>engine</span>
          </div>
          <p>© 2023 Engine - All rights reserved</p>
        </div>
      </footer>
    </div>
  )
}

export default App