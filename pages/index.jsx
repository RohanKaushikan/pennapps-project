import { useState, useEffect } from 'react'
import { Bell, Loader, AlertTriangle, Globe, User, LogIn } from 'lucide-react'

export default function TravelWelcomeApp() {
  const [countryData, setCountryData] = useState(null)
  const [activeTab, setActiveTab] = useState('welcome')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showApp, setShowApp] = useState(false)
  const [selectedCountry, setSelectedCountry] = useState('japan')

  // Function to fetch country data from backend
  const fetchCountryData = async () => {
    try {
      console.log('Fetching country data from:', 'http://localhost:8000/api/v1/countries/country-info')
      const response = await fetch('http://localhost:8000/api/v1/countries/country-info')
      console.log('Response status:', response.status)
      if (!response.ok) {
        throw new Error(`Failed to fetch country data: ${response.status}`)
      }
      const data = await response.json()
      console.log('Received data:', data)
      return data
    } catch (error) {
      console.error('Error:', error)
      throw error
    }
  }

  // Country data
  const countryOptions = {
    japan: {
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
    },
    nepal: {
      name: "Nepal",
      welcome: [
        {
          icon: "🏔️",
          title: "Welcome to Nepal!",
          message: "Namaste! Discover the land of the Himalayas and ancient temples."
        },
        {
          icon: "🕉️",
          title: "Spiritual Journey",
          message: "Experience the birthplace of Buddha and rich Hindu culture."
        }
      ],
      transport: [
        "Domestic flights connect major cities and tourist areas",
        "Bus services are the main mode of inter-city transport",
        "Taxis and rickshaws available in Kathmandu and Pokhara",
        "Trekking routes require proper permits and guides"
      ],
      culture: [
        "Say 'Namaste' with hands together as a greeting",
        "Remove shoes before entering temples and homes",
        "Dress modestly, especially when visiting religious sites",
        "Respect local customs and traditions"
      ],
      language: [
        {
          native: "नमस्ते (Namaste)",
          meaning: "Hello / Greetings"
        },
        {
          native: "धन्यवाद (Dhanyabad)",
          meaning: "Thank you"
        },
        {
          native: "माफ गर्नुहोस् (Maaf garnuhos)",
          meaning: "Excuse me / Sorry"
        },
        {
          native: "अंग्रेजी बोल्नुहुन्छ? (Angreji bolnuhunchha?)",
          meaning: "Do you speak English?"
        }
      ]
    },
    russia: {
      name: "Russia",
      welcome: [
        {
          icon: "🇷🇺",
          title: "Welcome to Russia!",
          message: "Добро пожаловать! Your travel companion is ready to help."
        },
        {
          icon: "❄️",
          title: "Winter Wonderland",
          message: "Experience the vast landscapes and rich cultural heritage of Russia."
        }
      ],
      transport: [
        "Metro systems are extensive and very cheap",
        "Long-distance trains are comfortable and reliable",
        "Taxis use apps like Yandex.Taxi",
        "Walking is common in city centers"
      ],
      culture: [
        "Remove outdoor shoes when entering homes",
        "Bring a small gift when visiting someone's home",
        "Dress warmly in winter - temperatures can drop to -30°C",
        "Learn basic Cyrillic alphabet for navigation"
      ],
      language: [
        {
          native: "Привет (Privet)",
          meaning: "Hello (informal)"
        },
        {
          native: "Спасибо (Spasibo)",
          meaning: "Thank you"
        },
        {
          native: "Извините (Izvinite)",
          meaning: "Excuse me / I'm sorry"
        },
        {
          native: "Вы говорите по-английски? (Vy govorite po-angliyski?)",
          meaning: "Do you speak English?"
        }
      ]
    }
  }

  // Initialize the app
  useEffect(() => {
    setCountryData(countryOptions[selectedCountry])
  }, [selectedCountry])

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
  const WelcomeTab = ({ welcome }) => (
    <div className="tab-content active">
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

  const TransportTab = ({ transport }) => (
    <div className="tab-content">
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

  const CultureTab = ({ culture }) => (
    <div className="tab-content">
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

  const LanguageTab = ({ language }) => (
    <div className="tab-content">
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

    switch (activeTab) {
      case 'welcome':
        return <WelcomeTab welcome={countryData.welcome} />
      case 'transport':
        return <TransportTab transport={countryData.transport} />
      case 'culture':
        return <CultureTab culture={countryData.culture} />
      case 'language':
        return <LanguageTab language={countryData.language} />
      default:
        return <WelcomeTab welcome={countryData.welcome} />
    }
  }

  if (showApp) {
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
      `}</style>

      {/* Header */}
      <div className="header">
        <div className="header-content">
          <div>
            <h1>Welcome</h1>
            <p>{loading ? 'Loading...' : countryData?.name || 'Unknown Location'}</p>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button 
              onClick={() => setShowApp(false)}
              style={{
                background: 'rgba(255, 255, 255, 0.2)',
                border: 'none',
                color: 'white',
                padding: '8px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              ← Back to Home
            </button>
            <Bell size={24} />
          </div>
        </div>
      </div>

      {/* Country Selector */}
      <div style={{ padding: '16px', maxWidth: '28rem', margin: '0 auto' }}>
        <select
          value={selectedCountry}
          onChange={(e) => setSelectedCountry(e.target.value)}
          style={{
            width: '100%',
            padding: '12px 16px',
            border: '1px solid #d1d5db',
            borderRadius: '12px',
            fontSize: '16px',
            backgroundColor: 'white',
            cursor: 'pointer'
          }}
        >
          <option value="japan">🇯🇵 Japan</option>
          <option value="nepal">🇳🇵 Nepal</option>
          <option value="russia">🇷🇺 Russia</option>
        </select>
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

    </div>
    )
  }

  // Landing page with app selection
  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <style>{`
        .landing-container {
          background: white;
          border-radius: 20px;
          padding: 40px;
          box-shadow: 0 20px 40px rgba(0,0,0,0.1);
          width: 100%;
          max-width: 600px;
          text-align: center;
        }
        .landing-header h1 {
          font-size: 32px;
          font-weight: bold;
          color: #1f2937;
          margin: 0 0 8px 0;
        }
        .landing-header p {
          color: #6b7280;
          margin: 0 0 32px 0;
          font-size: 16px;
        }
        .app-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
          margin-bottom: 32px;
        }
        .app-card {
          background: #f8fafc;
          border: 2px solid #e5e7eb;
          border-radius: 16px;
          padding: 24px;
          cursor: pointer;
          transition: all 0.3s;
          text-decoration: none;
          color: inherit;
        }
        .app-card:hover {
          border-color: #3b82f6;
          transform: translateY(-4px);
          box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        .app-card h3 {
          font-size: 18px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 8px 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .app-card p {
          color: #6b7280;
          margin: 0;
          font-size: 14px;
          line-height: 1.4;
        }
        .demo-note {
          background: #f3f4f6;
          border-radius: 12px;
          padding: 20px;
          margin-top: 24px;
          text-align: left;
        }
        .demo-note h4 {
          color: #374151;
          margin: 0 0 8px 0;
          font-size: 16px;
        }
        .demo-note p {
          color: #6b7280;
          margin: 0;
          font-size: 14px;
        }
        .feature-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-top: 12px;
        }
        .feature-item {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          color: #4b5563;
        }
      `}</style>

      <div className="landing-container">
        <div className="landing-header">
          <h1>Travel Alert System</h1>
          <p>Stay informed about travel advisories and safety information worldwide</p>
        </div>

        <div className="app-grid">
          <a href="/auth" className="app-card">
            <h3>
              <LogIn size={20} />
              Travel Alerts App
            </h3>
            <p>Complete travel advisory system with user accounts, alert management, and real-time updates from official government sources.</p>
          </a>

          <div className="app-card" onClick={() => setShowApp(true)}>
            <h3>
              <Globe size={20} />
              Travel Guide Demo
            </h3>
            <p>Simple travel information app showing country-specific tips, culture, and language guides for travelers.</p>
          </div>
        </div>

        <div className="demo-note">
          <h4>🚀 Travel Alerts App Features:</h4>
          <div className="feature-list">
            <div className="feature-item">
              <AlertTriangle size={16} />
              <span>Real-time travel advisories from US State Department, UK Foreign Office, and Canadian sources</span>
            </div>
            <div className="feature-item">
              <User size={16} />
              <span>User accounts with personalized travel preferences and country selections</span>
            </div>
            <div className="feature-item">
              <Globe size={16} />
              <span>Country-specific alert browsing and filtering by risk level, category, and date</span>
            </div>
            <div className="feature-item">
              <Bell size={16} />
              <span>Mark alerts as read/unread and receive notifications for new advisories</span>
            </div>
          </div>
          <p style={{ marginTop: '12px', fontStyle: 'italic' }}>
            Click "Travel Alerts App" to access the full system, or try the "Travel Guide Demo" for a simpler experience.
          </p>
        </div>
      </div>
    </div>
  )
}
