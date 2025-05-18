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
      // Connect to the server-sent events endpoint
      const apiUrl = new URL('http://localhost:8000/stream-code-gen')

      const eventSource = new EventSource(`http://localhost:8000/stream-code-gen`)
      eventSourceRef.current = eventSource

      // Listen for different event types
      eventSource.addEventListener('status', (event) => {
        const data = JSON.parse(event.data)
        setStatus(data.status)
      })

      eventSource.addEventListener('endpoints', (event) => {
        const data = JSON.parse(event.data)
        const formattedEndpoints = data.endpoints.map(endpoint => ({
          method: endpoint.method || 'GET',
          path: endpoint.path || '',
          description: endpoint.description || ''
        }))
        setEndpoints(formattedEndpoints)
      })

      eventSource.addEventListener('completed', (event) => {
        const data = JSON.parse(event.data)
        setProjectData(data.result)
        eventSource.close()
        setLoading(false)
      })

      eventSource.addEventListener('error', (event) => {
        const data = JSON.parse(event.data)
        setStatus(`Error: ${data.error}`)
        eventSource.close()
        setLoading(false)
      })

      eventSource.addEventListener('message_stop', () => {
        eventSource.close()
        setLoading(false)
      })

      // Handle connection error
      eventSource.onerror = (error) => {
        console.error('EventSource error:', error)
        setStatus('Error connecting to the server')
        eventSource.close()
        setLoading(false)
      }

      // Initialize with a POST request to start the process
      await fetch('http://localhost:8000/stream-code-gen', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: repoUrl }),
      })
    } catch (error) {
      console.error('Error:', error)
      setStatus(`Error: ${error.message}`)
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    if (!projectData) return

    try {
      const response = await fetch(`http://localhost:8000/download-code?project_uuid=${projectData.project_uuid}`)

      if (!response.ok) {
        throw new Error('Failed to download generated code')
      }

      // Get the blob from the response
      const blob = await response.blob()

      // Create a download link
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `${projectData.repo_name}-backend.zip`

      // Trigger download
      document.body.appendChild(link)
      link.click()

      // Cleanup
      window.URL.revokeObjectURL(downloadUrl)
      document.body.removeChild(link)

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