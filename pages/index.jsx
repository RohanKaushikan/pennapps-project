import { useState, useEffect } from 'react'
import { Bell, Loader } from 'lucide-react'

export default function TravelWelcomeApp() {
  const [countryData, setCountryData] = useState(null)
  const [activeTab, setActiveTab] = useState('welcome')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedCountry, setSelectedCountry] = useState('NP')
  const [availableCountries, setAvailableCountries] = useState([])

  // Function to fetch available countries
  const fetchCountries = async () => {
    try {
      console.log('Fetching countries from:', 'http://localhost:8000/api/countries')
      const response = await fetch('http://localhost:8000/api/countries')
      console.log('Countries response status:', response.status)
      if (!response.ok) {
        throw new Error(`Failed to fetch countries: ${response.status}`)
      }
      const data = await response.json()
      console.log('Countries data:', data)
      return data.countries
    } catch (error) {
      console.error('Error fetching countries:', error)
      return []
    }
  }

  // Function to fetch country data from backend
  const fetchCountryData = async (countryCode = 'NP') => {
    try {
      const url = `http://localhost:8000/api/country-info?country_code=${countryCode}`
      console.log('Fetching country data from:', url)
      const response = await fetch(url)
      console.log('Country data response status:', response.status)
      if (!response.ok) {
        throw new Error(`Failed to fetch country data: ${response.status}`)
      }
      const data = await response.json()
      console.log('Country data:', data)
      return data
    } catch (error) {
      console.error('Error fetching country data:', error)
      throw error
    }
  }

  // Initialize the app
  useEffect(() => {
    const initApp = async () => {
      try {
        setLoading(true)
        setError(null) // Clear any previous errors
        const countries = await fetchCountries()
        setAvailableCountries(countries)
        
        const data = await fetchCountryData(selectedCountry)
        setCountryData(data)
        setLoading(false)
      } catch (error) {
        console.error('Error initializing app:', error)
        setError('Failed to load country information. Please try again later.')
        setLoading(false)
      }
    }

    initApp()
  }, [])

  // Handle country selection
  const handleCountryChange = async (countryCode) => {
    try {
      setLoading(true)
      setError(null) // Clear any previous errors
      setSelectedCountry(countryCode)
      const data = await fetchCountryData(countryCode)
      setCountryData(data)
      setLoading(false)
    } catch (error) {
      console.error('Error changing country:', error)
      setError('Failed to load country information. Please try again later.')
      setLoading(false)
    }
  }

  // Loading spinner component
  const LoadingSpinner = () => (
    <div className="flex justify-center items-center py-20">
      <div className="loader"></div>
    </div>
  )

  // Error message component
  const ErrorMessage = ({ message }) => (
    <div className="error-message">
      {message}
    </div>
  )

  // Tab content components
  const WelcomeTab = ({ welcome, isActive }) => (
    <div className={`tab-content ${isActive ? 'active' : ''}`}>
      {welcome?.map((item, index) => (
        <div key={index} className="card">
          <div className="info-item">
            <div>{item.icon}</div>
            <div style={{ marginLeft: '10px' }}>
              <h3>{item.title}</h3>
              <p style={{ color: '#666' }}>{item.message}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )

  const TransportTab = ({ transport, isActive }) => (
    <div className={`tab-content ${isActive ? 'active' : ''}`}>
      <div className="card">
        <h3 className="title">Transportation Tips</h3>
        {transport?.map((tip, index) => (
          <div key={index} className="info-item">
            <div className="dot"></div>
            <div>{tip}</div>
          </div>
        ))}
      </div>
    </div>
  )

  const CultureTab = ({ culture, isActive }) => (
    <div className={`tab-content ${isActive ? 'active' : ''}`}>
      <div className="card">
        <h3 className="title">Cultural Guidelines</h3>
        {culture?.map((tip, index) => (
          <div key={index} className="info-item">
            <div className="dot"></div>
            <div>{tip}</div>
          </div>
        ))}
      </div>
    </div>
  )

  const LanguageTab = ({ language, isActive }) => (
    <div className={`tab-content ${isActive ? 'active' : ''}`}>
      <div className="card">
        <h3 className="title">Essential Phrases</h3>
        {language?.map((phrase, index) => (
          <div key={index} className="phrase">
            <div className="phrase-native">{phrase.native}</div>
            <div className="phrase-meaning">{phrase.meaning}</div>
          </div>
        ))}
      </div>
    </div>
  )

  const renderTabContent = () => {
    if (!countryData) return null

    return (
      <>
        <WelcomeTab welcome={countryData.welcome} isActive={activeTab === 'welcome'} />
        <TransportTab transport={countryData.transport} isActive={activeTab === 'transport'} />
        <CultureTab culture={countryData.culture} isActive={activeTab === 'culture'} />
        <LanguageTab language={countryData.language} isActive={activeTab === 'language'} />
      </>
    )
  }

  return (
    <div style={{ backgroundColor: '#f3f4f6', minHeight: '100vh' }}>
      <style>{`
        .header {
          background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
          color: white;
          padding: 24px;
          border-radius: 0 0 24px 24px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .header-content {
          display: flex;
          justify-content: space-between;
          align-items: center;
          max-width: 28rem;
          margin: 0 auto;
        }

        .header h1 {
          font-size: 1.5rem;
          font-weight: bold;
          margin: 0 0 4px 0;
        }

        .header p {
          font-size: 0.875rem;
          opacity: 0.9;
          margin: 0;
        }

        .tabs {
          display: flex;
          background: rgba(255, 255, 255, 0.5);
          margin: 16px;
          border-radius: 16px;
          padding: 4px;
          border: 1px solid #d1d5db;
          max-width: 28rem;
          margin: 16px auto;
        }

        .tab-button {
          flex: 1;
          padding: 12px 16px;
          border-radius: 12px;
          font-weight: 500;
          transition: all 0.2s;
          background: none;
          border: none;
          cursor: pointer;
          font-size: 0.875rem;
          color: #6b7280;
        }

        .tab-button.active {
          background: white;
          color: #1f2937;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
          border: 1px solid #d1d5db;
        }

        .tab-button:hover:not(.active) {
          background: rgba(255, 255, 255, 0.5);
        }

        .content-area {
          padding: 0 16px 24px;
          max-width: 28rem;
          margin: 0 auto;
        }

        .tab-content {
          display: none;
        }

        .tab-content.active {
          display: block;
        }

        .card {
          background: white;
          border-radius: 16px;
          padding: 20px;
          margin-bottom: 16px;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
          border: 1px solid #e5e7eb;
        }

        .info-item {
          display: flex;
          align-items: flex-start;
          padding: 12px 0;
        }

        .info-item h3 {
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 4px 0;
        }

        .info-item p {
          margin: 0;
          font-size: 0.875rem;
        }

        .title {
          font-size: 1.125rem;
          font-weight: bold;
          margin-bottom: 16px;
          color: #1f2937;
          display: flex;
          align-items: center;
        }

        .dot {
          width: 8px;
          height: 8px;
          background: #3b82f6;
          border-radius: 50%;
          margin-right: 12px;
          margin-top: 6px;
          flex-shrink: 0;
        }

        .phrase {
          padding: 12px 0;
          border-bottom: 1px solid #f3f4f6;
        }

        .phrase:last-child {
          border-bottom: none;
        }

        .phrase-native {
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 4px;
        }

        .phrase-meaning {
          font-size: 0.875rem;
          color: #6b7280;
        }

        .loader {
          border: 4px solid #f3f3f3;
          border-radius: 50%;
          border-top: 4px solid #2563eb;
          width: 40px;
          height: 40px;
          animation: spin 1s linear infinite;
          margin: 20px auto;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .error-message {
          color: #dc2626;
          text-align: center;
          padding: 20px;
          background: #fef2f2;
          border-radius: 8px;
          margin: 20px;
          border: 1px solid #fecaca;
        }

        .country-selector {
          margin-top: 8px;
          padding: 6px 12px;
          border-radius: 8px;
          border: 1px solid rgba(255, 255, 255, 0.3);
          background: rgba(255, 255, 255, 0.2);
          color: white;
          font-size: 0.875rem;
          cursor: pointer;
        }

        .country-selector:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .country-selector option {
          background: #1f2937;
          color: white;
        }
      `}</style>

      {/* Header */}
      <div className="header">
        <div className="header-content">
          <div>
            <h1>Welcome</h1>
            <p>{loading ? 'Loading...' : countryData?.name || 'Unknown Location'}</p>
            {availableCountries.length > 0 && (
              <select 
                value={selectedCountry} 
                onChange={(e) => handleCountryChange(e.target.value)}
                className="country-selector"
                disabled={loading}
              >
                {availableCountries.map(country => (
                  <option key={country.code} value={country.code}>
                    {country.flag} {country.name}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div>
            <Bell size={24} />
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="tabs">
        <button
          className={`tab-button ${activeTab === 'welcome' ? 'active' : ''}`}
          onClick={() => setActiveTab('welcome')}
        >
          Welcome
        </button>
        <button
          className={`tab-button ${activeTab === 'transport' ? 'active' : ''}`}
          onClick={() => setActiveTab('transport')}
        >
          Transport
        </button>
        <button
          className={`tab-button ${activeTab === 'culture' ? 'active' : ''}`}
          onClick={() => setActiveTab('culture')}
        >
          Culture
        </button>
        <button
          className={`tab-button ${activeTab === 'language' ? 'active' : ''}`}
          onClick={() => setActiveTab('language')}
        >
          Language
        </button>
      </div>

      {/* Content Area */}
      <div className="content-area">
        {loading && <LoadingSpinner />}
        {error && <ErrorMessage message={error} />}
        {!loading && !error && renderTabContent()}
      </div>

      {/* Demo Data - Remove when connecting to real backend */}
      {!loading && !error && !countryData && (
        <div className="content-area">
          <div className="card">
            <h3>Demo Mode</h3>
            <p>This app is running in demo mode. Connect to your backend API to see real country data.</p>
            <button
              onClick={() => {
                // Simulate loading demo data
                setLoading(true)
                setTimeout(() => {
                  setCountryData({
                    name: "Japan",
                    welcome: [
                      {
                        icon: "🎌",
                        title: "Welcome to Japan!",
                        message: "Konnichiwa! Your travel companion is ready to help."
                      },
                      {
                        icon: "🏮",
                        title: "Cultural Experience",
                        message: "Discover the rich traditions and modern innovations of Japan."
                      }
                    ],
                    transport: [
                      "IC cards work on all trains and subways",
                      "Follow blue signs for domestic, red for international",
                      "Shinkansen (bullet train) requires reserved seats for long distances",
                      "Taxis are expensive but very reliable and clean"
                    ],
                    culture: [
                      "Remove shoes when entering homes and some restaurants",
                      "Bowing is customary - a slight nod is perfectly acceptable",
                      "Keep voices low on public transportation",
                      "Cash is still king - many places don't accept cards"
                    ],
                    language: [
                      {
                        native: "こんにちは (Konnichiwa)",
                        meaning: "Hello (formal greeting)"
                      },
                      {
                        native: "ありがとうございます (Arigatou gozaimasu)",
                        meaning: "Thank you very much"
                      },
                      {
                        native: "すみません (Sumimasen)",
                        meaning: "Excuse me / I'm sorry"
                      },
                      {
                        native: "英語を話せますか？ (Eigo wo hanasemasu ka?)",
                        meaning: "Do you speak English?"
                      }
                    ]
                  })
                  setLoading(false)
                }, 1000)
              }}
              className="tab-button active"
              style={{ width: '100%', marginTop: '10px' }}
            >
              Load Demo Data
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
