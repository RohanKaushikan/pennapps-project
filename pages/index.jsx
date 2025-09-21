import { useState, useEffect, useRef } from 'react'
import { Bell, Loader, MapPin, Eye, EyeOff, Plane, AlertTriangle, Filter, Shield, Toggle } from 'lucide-react'
import AlertCategorization from '../components/AlertCategorization'
import SmartAlertCard from '../components/SmartAlertCard'
import SmartAlertSummary from '../components/SmartAlertSummary'
import ComplianceChecklist from '../components/ComplianceChecklist'
import EnhancedFiltering from '../components/EnhancedFiltering'
import IntelligencePanel from '../components/IntelligencePanel'
import EnhancedAlertDisplay from '../components/EnhancedAlertDisplay'

export default function TravelWelcomeApp() {
  const [countryData, setCountryData] = useState(null)
  const [activeTab, setActiveTab] = useState('alerts')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedCountry, setSelectedCountry] = useState('NP')
  const [availableCountries, setAvailableCountries] = useState([])
  const [alerts, setAlerts] = useState(null)

  // Enhanced alerts state - Will be set to true after alerts load
  const [showEnhancedView, setShowEnhancedView] = useState(false)
  
  // Location simulation state
  const [currentLocation, setCurrentLocation] = useState(null)
  const [showDemoPanel, setShowDemoPanel] = useState(false)
  const [dKeyCount, setDKeyCount] = useState(0)
  const [showLocationAlerts, setShowLocationAlerts] = useState(false)
  const [locationAlerts, setLocationAlerts] = useState(null)
  const [isBackgroundMode, setIsBackgroundMode] = useState(true)
  const dKeyTimeoutRef = useRef(null)

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

  // Function to fetch alerts/anomalies data
  const fetchAlerts = async () => {
    try {
      const url = `http://localhost:8000/api/anomalies`
      console.log('Fetching alerts from:', url)
      const response = await fetch(url)
      console.log('Alerts response status:', response.status)
      if (!response.ok) {
        throw new Error(`Failed to fetch alerts: ${response.status}`)
      }
      const data = await response.json()
      console.log('Alerts data:', data)
      return data
    } catch (error) {
      console.error('Error fetching alerts:', error)
      throw error
    }
  }


  // Location simulation functions
  const simulateTravel = async (countryCode) => {
    try {
      const response = await fetch('/api/simulate-travel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ countryCode, action: 'setLocation' })
      })
      
      const result = await response.json()
      
      if (result.success) {
        setCurrentLocation(result.currentLocation)
        setSelectedCountry(countryCode)
        
        // Load country data and alerts when traveling
        try {
          const [countryData, alertsData] = await Promise.all([
            fetchCountryData(countryCode),
            fetchAlerts()
          ])
          console.log('🎯 Loaded country data and alerts:', { countryData, alertsData })
          setCountryData(countryData)
          setAlerts(alertsData)
          
          // Auto-switch to alerts tab and enable enhanced view to show ML features
          setActiveTab('alerts')
          setShowEnhancedView(true)
          setIsBackgroundMode(false) // Make sure we're not in background mode
          console.log('🧠 Auto-enabled Enhanced View and switched to Alerts tab for', countryCode)
        } catch (error) {
          console.error('Error loading country data:', error)
        }
        
        if (result.locationChanged && result.alerts) {
          setLocationAlerts(result.alerts)
          setShowLocationAlerts(true)
          setIsBackgroundMode(false)
          
          // Request notification permission and show notification
          if (Notification.permission === 'granted') {
            const spikeFactor = result.alerts?.alerts?.[0]?.spike_factor || 1;
            const alertLevel = spikeFactor >= 2 ? '🚨 CRITICAL' : spikeFactor >= 1.5 ? '⚠️ WARNING' : 'ℹ️ INFO';
            
            new Notification(`${alertLevel} - Entered ${result.alerts.country}`, {
              body: spikeFactor >= 2 
                ? `${spikeFactor}x more travel news than normal! Click to view details.`
                : 'Travel alert detected! Click to view details.',
              icon: '/favicon.ico',
              tag: 'travel-alert',
              requireInteraction: true
            })
          } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
              if (permission === 'granted') {
                const spikeFactor = result.alerts?.alerts?.[0]?.spike_factor || 1;
                const alertLevel = spikeFactor >= 2 ? '🚨 CRITICAL' : spikeFactor >= 1.5 ? '⚠️ WARNING' : 'ℹ️ INFO';
                
                new Notification(`${alertLevel} - Entered ${result.alerts.country}`, {
                  body: spikeFactor >= 2 
                    ? `${spikeFactor}x more travel news than normal! Click to view details.`
                    : 'Travel alert detected! Click to view details.',
                  icon: '/favicon.ico',
                  tag: 'travel-alert',
                  requireInteraction: true
                })
              }
            })
          }
        }
      }
    } catch (error) {
      console.error('Error simulating travel:', error)
    }
  }

  const getCurrentLocation = async () => {
    try {
      const response = await fetch('/api/simulate-travel')
      const result = await response.json()
      if (result.success) {
        setCurrentLocation(result.currentLocation)
      }
    } catch (error) {
      console.error('Error getting current location:', error)
    }
  }

  const dismissLocationAlerts = () => {
    setShowLocationAlerts(false)
    setLocationAlerts(null)
    setIsBackgroundMode(false) // Stay in app mode to show ML features
    // Keep enhanced view enabled and alerts tab active to show ML data
    setActiveTab('alerts')
    setShowEnhancedView(true)
  }

  // Keyboard handler for demo panel
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key.toLowerCase() === 'd') {
        setDKeyCount(prev => prev + 1)
        
        // Clear existing timeout
        if (dKeyTimeoutRef.current) {
          clearTimeout(dKeyTimeoutRef.current)
        }
        
        // Set new timeout
        dKeyTimeoutRef.current = setTimeout(() => {
          setDKeyCount(0)
        }, 2000)
        
        // Show demo panel after 3 D presses
        if (dKeyCount + 1 >= 3) {
          setShowDemoPanel(true)
          setDKeyCount(0)
        }
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [dKeyCount])

  // Initialize the app
  useEffect(() => {
    const initApp = async () => {
      try {
        setLoading(true)
        setError(null) // Clear any previous errors
        
        // Always start in background mode
        setIsBackgroundMode(true)
        
        // Load countries and basic data in background
        const countries = await fetchCountries()
        setAvailableCountries(countries)
        
        // Get current location from simulation
        await getCurrentLocation()
        
        setLoading(false)
      } catch (error) {
        console.error('Error initializing app:', error)
        setError('Failed to load country information. Please try again later.')
        setLoading(false)
      }
    }

    initApp()
  }, [])

  // Auto-enable Enhanced View when alerts are available
  useEffect(() => {
    if (alerts && alerts.length > 0) {
      console.log('🚀 Auto-enabling Enhanced View - alerts loaded:', alerts.length)
      setShowEnhancedView(true)
    }
  }, [alerts])

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

  const AlertsTab = ({ isActive }) => {
    const currentCountryAlerts = alerts?.find(alert => alert.country_code === selectedCountry)

    const toggleEnhancedView = () => {
      setShowEnhancedView(!showEnhancedView)
    }

    return (
      <div className={`tab-content ${isActive ? 'active' : ''}`}>
        {/* Enhanced View Toggle */}
        <div className="enhanced-controls">
          <div className="view-toggle">
            <button
              className={`toggle-button ${!showEnhancedView ? 'active' : ''}`}
              onClick={() => !showEnhancedView || toggleEnhancedView()}
            >
              <Shield size={16} />
              Standard View
            </button>
            <button
              className={`toggle-button ${showEnhancedView ? 'active' : ''}`}
              onClick={toggleEnhancedView}
            >
              <Filter size={16} />
              🧠 Enhanced View {showEnhancedView ? '(ML Active)' : ''}
            </button>
          </div>

        </div>

        {/* Standard View (existing functionality) */}
        {!showEnhancedView && (
          <div className="card">
            <h3 className="title">
              {currentCountryAlerts?.is_anomaly ? '🚨' : '✅'} Travel Alerts
            </h3>
            {currentCountryAlerts?.is_anomaly ? (
              <div className="alert-anomaly">
                <p><strong>Unusual Activity Detected!</strong></p>
                <p>Spike Factor: {currentCountryAlerts.spike_factor}x normal</p>
                <p>Current News Volume: {currentCountryAlerts.current_count} articles</p>
              </div>
            ) : (
              <div className="alert-normal">
                <p>✅ Normal travel conditions</p>
                <p>No unusual news activity detected</p>
              </div>
            )}

            {currentCountryAlerts?.top_headlines?.length > 0 && (
              <div className="headlines">
                <h4>Recent Headlines:</h4>
                {currentCountryAlerts.top_headlines.map((headline, index) => (
                  <div key={index} className="headline-item">
                    <a href={headline.url} target="_blank" rel="noopener noreferrer">
                      {headline.title}
                    </a>
                    <div className="headline-source">{headline.source}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Enhanced View (ML-powered) - Using full EnhancedAlertDisplay component */}
        {showEnhancedView && (
          <div className="enhanced-view">
            <EnhancedAlertDisplay 
              countryCode={selectedCountry} 
              className="full-enhanced-display"
            />
          </div>
        )}

        {/* Anomaly Status (always visible) */}
        {currentCountryAlerts?.is_anomaly && showEnhancedView && (
          <div className="anomaly-banner">
            <AlertTriangle size={16} />
            <span>
              <strong>Anomaly Detected:</strong> {currentCountryAlerts.spike_factor}x normal activity
              ({currentCountryAlerts.current_count} articles)
            </span>
          </div>
        )}
      </div>
    )
  }

  // Location Alerts Component
  const LocationAlertsScreen = () => (
    <div className="location-alerts-overlay">
      <div className="location-alerts-container">
        <div className="location-alerts-header">
          <h2>{locationAlerts?.flag} {locationAlerts?.country} Travel Alerts</h2>
          <button 
            className="dismiss-button"
            onClick={dismissLocationAlerts}
          >
            ✕
          </button>
        </div>
        
        <div className="location-alerts-content">
          {locationAlerts?.alerts?.map((alert, index) => (
            <div key={alert.id} className={`location-alert ${alert.level}`}>
              <div className="alert-header">
                <div className="alert-icon">
                  {alert.level === 'critical' && <span style={{ fontSize: '20px' }}>🚨</span>}
                  {alert.level === 'warning' && <span style={{ fontSize: '20px' }}>⚠️</span>}
                  {alert.level === 'info' && <span style={{ fontSize: '20px' }}>ℹ️</span>}
                </div>
                <h3>{alert.title}</h3>
                <span className={`alert-level ${alert.level}`}>
                  {alert.level.toUpperCase()}
                </span>
              </div>
              <p className="alert-message">{alert.message}</p>
              <p className="alert-details">{alert.details}</p>
              
              {/* Show spike factor for anomaly alerts */}
              {alert.spike_factor && (
                <div className="spike-info">
                  <strong>Spike Factor: {alert.spike_factor}x normal</strong>
                  <span>Articles: {alert.current_count}</span>
                </div>
              )}
              
              {/* Show clickable link for news headlines */}
              {alert.url && (
                <a 
                  href={alert.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="news-link"
                >
                  Read full article →
                </a>
              )}
            </div>
          ))}
        </div>
        
        <div className="location-alerts-footer">
          <button 
            className="acknowledge-button"
            onClick={dismissLocationAlerts}
          >
            Acknowledge & Continue
          </button>
        </div>
      </div>
    </div>
  )

  // Background Monitoring Component
  const BackgroundMonitoringScreen = () => (
    <div className="background-monitoring">
      <div className="monitoring-header">
        <div className="monitoring-icon">
          <MapPin size={24} />
        </div>
        <div className="monitoring-text">
          <h2>TravelSense</h2>
          <p>Running in background</p>
        </div>
        <div className="monitoring-status">
          <div className="status-dot"></div>
          <span>Monitoring active</span>
        </div>
      </div>
      
      <div className="current-location">
        <p>Currently in: <strong>{currentLocation || 'Unknown'}</strong></p>
      </div>
      
      <div className="monitoring-visualization">
        <div className="pulse-ring"></div>
        <div className="pulse-ring delay-1"></div>
        <div className="pulse-ring delay-2"></div>
      </div>
      
      {showDemoPanel && (
        <div className="demo-panel">
          <div className="demo-header">
            <h3>Demo Controls</h3>
            <button 
              className="close-demo"
              onClick={() => setShowDemoPanel(false)}
            >
              ✕
            </button>
          </div>
          <div className="demo-buttons">
            <button 
              className="demo-button"
              onClick={() => simulateTravel('NP')}
            >
              <Plane size={16} />
              Travel to Nepal 🇳🇵
            </button>
            <button 
              className="demo-button"
              onClick={() => simulateTravel('IT')}
            >
              <Plane size={16} />
              Travel to Italy 🇮🇹
            </button>
            <button 
              className="demo-button"
              onClick={() => simulateTravel('RU')}
            >
              <Plane size={16} />
              Travel to Russia 🇷🇺
            </button>
          </div>
          <p className="demo-hint">Press 'D' 3 times to toggle this panel</p>
          <div style={{ marginTop: '12px', padding: '8px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '6px', fontSize: '0.75rem', color: '#3b82f6' }}>
            💡 <strong>To see ML features:</strong> Select a country → Go to "Alerts" tab → Enhanced View is now ON by default!
          </div>
        </div>
      )}
    </div>
  )

  const renderTabContent = () => {
    return (
      <>
        <AlertsTab isActive={activeTab === 'alerts'} />
        {countryData && (
          <>
            <WelcomeTab welcome={countryData.welcome} isActive={activeTab === 'welcome'} />
            <TransportTab transport={countryData.transport} isActive={activeTab === 'transport'} />
            <CultureTab culture={countryData.culture} isActive={activeTab === 'culture'} />
            <LanguageTab language={countryData.language} isActive={activeTab === 'language'} />
          </>
        )}
      </>
    )
  }

  // Show location alerts if they exist
  if (showLocationAlerts && locationAlerts) {
    return (
      <div style={{ backgroundColor: '#f3f4f6', minHeight: '100vh' }}>
        <style>{`
        .location-alerts-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: linear-gradient(135deg, rgba(0, 0, 0, 0.9) 0%, rgba(0, 0, 0, 0.7) 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 20px;
          backdrop-filter: blur(10px);
          animation: fadeIn 0.3s ease-out;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .location-alerts-container {
          background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
          border-radius: 24px;
          max-width: 600px;
          width: 100%;
          max-height: 85vh;
          overflow: hidden;
          box-shadow: 
            0 25px 50px -12px rgba(0, 0, 0, 0.25),
            0 0 0 1px rgba(255, 255, 255, 0.1);
          animation: slideUp 0.4s ease-out;
          border: 1px solid rgba(255, 255, 255, 0.2);
        }

        @keyframes slideUp {
          from { 
            opacity: 0;
            transform: translateY(30px) scale(0.95);
          }
          to { 
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }

        .location-alerts-header {
          background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
          color: white;
          padding: 24px;
          position: relative;
          overflow: hidden;
        }

        .location-alerts-header::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/><circle cx="50" cy="10" r="0.5" fill="white" opacity="0.1"/><circle cx="10" cy="60" r="0.5" fill="white" opacity="0.1"/><circle cx="90" cy="40" r="0.5" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
          opacity: 0.3;
        }

        .location-alerts-header h2 {
          margin: 0;
          font-size: 1.5rem;
          font-weight: 700;
          position: relative;
          z-index: 1;
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .dismiss-button {
          background: rgba(255, 255, 255, 0.2);
          border: none;
          color: white;
          font-size: 1.5rem;
          cursor: pointer;
          padding: 8px;
          border-radius: 50%;
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
          position: relative;
          z-index: 1;
        }

        .dismiss-button:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: scale(1.1);
        }

        .location-alerts-content {
          padding: 24px;
          max-height: 50vh;
          overflow-y: auto;
        }

        .location-alerts-content::-webkit-scrollbar {
          width: 6px;
        }

        .location-alerts-content::-webkit-scrollbar-track {
          background: #f1f5f9;
          border-radius: 3px;
        }

        .location-alerts-content::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 3px;
        }

        .location-alerts-content::-webkit-scrollbar-thumb:hover {
          background: #94a3b8;
        }

        .location-alert {
          margin-bottom: 20px;
          padding: 20px;
          border-radius: 16px;
          border: 1px solid;
          position: relative;
          overflow: hidden;
          transition: all 0.3s ease;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          animation: slideInAlert 0.5s ease-out;
        }

        @keyframes slideInAlert {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        .location-alert:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 15px -3px rgba(0, 0, 0, 0.1);
        }

        .location-alert.critical {
          background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
          border-color: #fecaca;
          border-left: 4px solid #dc2626;
        }

        .location-alert.warning {
          background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
          border-color: #fed7aa;
          border-left: 4px solid #f59e0b;
        }

        .location-alert.info {
          background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
          border-color: #bfdbfe;
          border-left: 4px solid #3b82f6;
        }

        .alert-header {
          display: flex;
          align-items: center;
          margin-bottom: 12px;
        }

        .alert-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: rgba(0, 0, 0, 0.1);
          margin-right: 12px;
        }

        .alert-header h3 {
          margin: 0 12px;
          font-size: 1.1rem;
          color: #1f2937;
          font-weight: 600;
        }

        .alert-level {
          padding: 4px 12px;
          border-radius: 20px;
          font-size: 0.75rem;
          font-weight: 700;
          margin-left: auto;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .alert-level.critical {
          background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
          color: white;
          box-shadow: 0 2px 4px rgba(220, 38, 38, 0.3);
        }

        .alert-level.warning {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          color: white;
          box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);
        }

        .alert-level.info {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          color: white;
          box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
        }

        .alert-message {
          margin: 12px 0;
          font-weight: 600;
          color: #374151;
          font-size: 1rem;
          line-height: 1.5;
        }

        .alert-details {
          margin: 8px 0 0 0;
          font-size: 0.9rem;
          color: #6b7280;
          line-height: 1.4;
        }

        .spike-info {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 12px;
          padding: 12px 16px;
          background: rgba(0, 0, 0, 0.05);
          border-radius: 12px;
          font-size: 0.9rem;
          border: 1px solid rgba(0, 0, 0, 0.1);
        }

        .spike-info strong {
          color: #1f2937;
          font-weight: 600;
        }

        .spike-info span {
          color: #6b7280;
          font-weight: 500;
        }

        .news-link {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          margin-top: 12px;
          color: #2563eb;
          text-decoration: none;
          font-weight: 600;
          font-size: 0.9rem;
          padding: 8px 16px;
          background: rgba(37, 99, 235, 0.1);
          border-radius: 8px;
          transition: all 0.2s ease;
          border: 1px solid rgba(37, 99, 235, 0.2);
        }

        .news-link:hover {
          background: rgba(37, 99, 235, 0.2);
          transform: translateY(-1px);
          box-shadow: 0 4px 8px rgba(37, 99, 235, 0.2);
        }

        .location-alerts-footer {
          padding: 24px;
          background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
          border-top: 1px solid #e2e8f0;
          text-align: center;
        }

        .acknowledge-button {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          border: none;
          padding: 16px 32px;
          border-radius: 12px;
          font-weight: 600;
          cursor: pointer;
          font-size: 1rem;
          transition: all 0.3s ease;
          box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.3);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .acknowledge-button:hover {
          background: linear-gradient(135deg, #059669 0%, #047857 100%);
          transform: translateY(-2px);
          box-shadow: 0 8px 15px -3px rgba(16, 185, 129, 0.4);
        }

        .acknowledge-button:active {
          transform: translateY(0);
        }
        `}</style>
        <LocationAlertsScreen />
      </div>
    )
  }

  // Show background monitoring if in background mode
  if (isBackgroundMode) {
    return (
      <div style={{ backgroundColor: '#1f2937', minHeight: '100vh', color: 'white' }}>
        <style>{`
          .background-monitoring {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
          }

          .monitoring-header {
            display: flex;
            align-items: center;
            margin-bottom: 40px;
            text-align: center;
          }

          .monitoring-icon {
            margin-right: 16px;
            color: #10b981;
          }

          .monitoring-text h2 {
            margin: 0 0 4px 0;
            font-size: 2rem;
            font-weight: bold;
          }

          .monitoring-text p {
            margin: 0;
            color: #9ca3af;
            font-size: 1rem;
          }

          .monitoring-status {
            display: flex;
            align-items: center;
            margin-left: 20px;
            color: #10b981;
            font-size: 0.875rem;
          }

          .status-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
          }

          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }

          .current-location {
            margin-bottom: 60px;
            text-align: center;
          }

          .current-location p {
            margin: 0;
            font-size: 1.125rem;
            color: #d1d5db;
          }

          .monitoring-visualization {
            position: relative;
            width: 120px;
            height: 120px;
            margin-bottom: 40px;
          }

          .pulse-ring {
            position: absolute;
            top: 0;
            left: 0;
            width: 120px;
            height: 120px;
            border: 2px solid #10b981;
            border-radius: 50%;
            animation: pulse-ring 2s infinite;
          }

          .pulse-ring.delay-1 {
            animation-delay: 0.5s;
          }

          .pulse-ring.delay-2 {
            animation-delay: 1s;
          }

          @keyframes pulse-ring {
            0% {
              transform: scale(0.8);
              opacity: 1;
            }
            100% {
              transform: scale(1.4);
              opacity: 0;
            }
          }

          .demo-panel {
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.9);
            border-radius: 12px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
          }

          .demo-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
          }

          .demo-header h3 {
            margin: 0;
            color: white;
            font-size: 1.125rem;
          }

          .close-demo {
            background: none;
            border: none;
            color: #9ca3af;
            font-size: 1.25rem;
            cursor: pointer;
            padding: 4px;
          }

          .demo-buttons {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 16px;
          }

          .demo-button {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #374151;
            color: white;
            border: none;
            padding: 12px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: background 0.2s;
          }

          .demo-button:hover {
            background: #4b5563;
          }

          .demo-hint {
            margin: 0;
            font-size: 0.75rem;
            color: #9ca3af;
            text-align: center;
          }
        `}</style>
        <BackgroundMonitoringScreen />
      </div>
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

        .alert-anomaly {
          background: #fef2f2;
          border: 1px solid #fecaca;
          border-radius: 8px;
          padding: 16px;
          margin: 16px 0;
          color: #dc2626;
        }

        .alert-normal {
          background: #f0fdf4;
          border: 1px solid #bbf7d0;
          border-radius: 8px;
          padding: 16px;
          margin: 16px 0;
          color: #16a34a;
        }

        .headlines {
          margin-top: 20px;
        }

        .headlines h4 {
          font-size: 1rem;
          font-weight: 600;
          margin-bottom: 12px;
          color: #374151;
        }

        .headline-item {
          margin-bottom: 12px;
          padding: 8px 0;
          border-bottom: 1px solid #e5e7eb;
        }

        .headline-item:last-child {
          border-bottom: none;
        }

        .headline-item a {
          color: #2563eb;
          text-decoration: none;
          font-weight: 500;
          line-height: 1.4;
        }

        .headline-item a:hover {
          text-decoration: underline;
        }

        .headline-source {
          font-size: 0.875rem;
          color: #6b7280;
          margin-top: 4px;
        }

        .mode-toggle {
          position: fixed;
          top: 20px;
          right: 20px;
          z-index: 100;
        }

        .mode-toggle-button {
          background: rgba(0, 0, 0, 0.7);
          color: white;
          border: none;
          padding: 8px 12px;
          border-radius: 20px;
          font-size: 0.75rem;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
          backdrop-filter: blur(10px);
        }

        .mode-toggle-button:hover {
          background: rgba(0, 0, 0, 0.9);
        }

        .enhanced-controls {
          margin-bottom: 20px;
          background: white;
          border-radius: 12px;
          padding: 16px;
          border: 1px solid #e5e7eb;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .view-toggle {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
          background: #f9fafb;
          padding: 4px;
          border-radius: 8px;
        }

        .toggle-button {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 8px 12px;
          border: none;
          background: transparent;
          border-radius: 6px;
          font-size: 0.875rem;
          font-weight: 500;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .toggle-button.active {
          background: white;
          color: #2563eb;
          box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
          border: 1px solid #e5e7eb;
        }

        .toggle-button:hover:not(.active) {
          background: rgba(255, 255, 255, 0.5);
        }

        .toggle-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .filter-controls {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .filter-toggle {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 6px 12px;
          border: 1px solid #d1d5db;
          background: white;
          border-radius: 6px;
          font-size: 0.75rem;
          font-weight: 500;
          color: #374151;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .filter-toggle.active {
          background: #3b82f6;
          color: white;
          border-color: #3b82f6;
        }

        .filter-toggle:hover:not(.active) {
          background: #f9fafb;
          border-color: #9ca3af;
        }

        .enhanced-view {
          margin-top: 0;
        }

        .enhanced-categorization {
          margin: 0;
        }

        .full-enhanced-display {
          margin: 0;
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .anomaly-banner {
          background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
          border: 1px solid #fecaca;
          border-radius: 8px;
          padding: 12px 16px;
          margin-top: 16px;
          display: flex;
          align-items: center;
          gap: 8px;
          color: #dc2626;
          font-size: 0.875rem;
        }

        @media (max-width: 768px) {
          .view-toggle {
            flex-direction: column;
          }

          .filter-controls {
            justify-content: center;
          }

          .filter-toggle {
            font-size: 0.7rem;
            padding: 5px 10px;
          }
        }

        .intelligence-controls {
          display: flex;
          gap: 12px;
          margin-bottom: 20px;
          justify-content: center;
          flex-wrap: wrap;
        }

        .intelligence-toggle {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 20px;
          background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
          border: 1px solid #cbd5e1;
          border-radius: 10px;
          font-weight: 600;
          color: #374151;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          font-size: 0.875rem;
        }

        .intelligence-toggle:hover {
          background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }

        .intelligence-toggle.active {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          color: white;
          border-color: #2563eb;
        }

        .intelligence-panel {
          margin-bottom: 20px;
          animation: slideDown 0.3s ease-out;
        }

        .compliance-panel {
          margin-bottom: 20px;
          animation: slideDown 0.3s ease-out;
        }

        .intelligence-summary {
          margin-bottom: 20px;
        }

        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @media (max-width: 768px) {
          .intelligence-controls {
            flex-direction: column;
            align-items: center;
          }

          .intelligence-toggle {
            width: 100%;
            justify-content: center;
            padding: 10px 16px;
          }
        }
      `}</style>

      {/* Mode Toggle Button */}
      <div className="mode-toggle">
        <button 
          className="mode-toggle-button"
          onClick={() => setIsBackgroundMode(!isBackgroundMode)}
        >
          {isBackgroundMode ? <Eye size={14} /> : <EyeOff size={14} />}
          {isBackgroundMode ? 'Show App' : 'Background'}
        </button>
      </div>

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
                className="country-selector enhanced"
                disabled={loading}
                title="Select country to view travel intelligence"
              >
                {availableCountries.map(country => {
                  // Get preview of alerts for this country
                  const countryAlerts = alerts?.find(alert => alert.country_code === country.code)
                  const alertInfo = countryAlerts?.is_anomaly
                    ? `🚨 ${countryAlerts.spike_factor}x activity`
                    : '✅ Normal'

                  return (
                    <option key={country.code} value={country.code}>
                      {country.flag} {country.name} - {alertInfo}
                    </option>
                  )
                })}
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
          className={`tab-button ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          Alerts
        </button>
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
