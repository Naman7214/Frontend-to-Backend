import { useEffect, useState } from 'react'
import { FaCode, FaGithub, FaMoon, FaRocket, FaSun } from 'react-icons/fa'
import './App.css'

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [endpoints, setEndpoints] = useState([])
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  const handleClone = async () => {
    if (!repoUrl) return

    setLoading(true)
    setStatus('Starting backend generation...')

    try {
      // Mock response for demo
      setTimeout(() => {
        setStatus('Backend generation completed!')
        setEndpoints([
          { method: 'GET', path: '/api/users', description: 'Get all users' },
          { method: 'POST', path: '/api/users', description: 'Create a user' },
          { method: 'GET', path: '/api/products', description: 'Get all products' }
        ])
        setLoading(false)
      }, 2000)

      // Uncomment when real API is ready
      /*
      const response = await fetch('http://localhost:8000/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_url: repoUrl }),
      })
      
      if (response.ok) {
        const data = await response.json()
        setStatus(data.status || 'Backend generation completed!')
        setEndpoints(data.endpoints || [])
      } else {
        setStatus('Error generating backend')
      }
      */
    } catch (error) {
      setStatus(`Error: ${error.message}`)
      setLoading(false)
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