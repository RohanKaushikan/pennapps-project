import { useState, useEffect, useRef } from 'react'
import { Bell, Loader, Globe, AlertTriangle, CheckCircle, MapPin, Plane, Eye, EyeOff } from 'lucide-react'

export default function TravelWelcomeApp() {
  const [countryData, setCountryData] = useState(null)
  const [activeTab, setActiveTab] = useState('alerts')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedCountry, setSelectedCountry] = useState('NP')
  const [availableCountries, setAvailableCountries] = useState([])
  const [alerts, setAlerts] = useState(null)
  
  // Location simulation state
  const [currentLocation, setCurrentLocation] = useState(null)
  const [showDemoPanel, setShowDemoPanel] = useState(false)
  const [dKeyCount, setDKeyCount] = useState(0)
  const [showLocationAlerts, setShowLocationAlerts] = useState(false)
  const [locationAlerts, setLocationAlerts] = useState(null)
  const [isBackgroundMode, setIsBackgroundMode] = useState(true)
  const dKeyTimeoutRef = useRef(null)
  
  // Location tracking state
  const [userLocation, setUserLocation] = useState(null)
  const [detectedCountry, setDetectedCountry] = useState(null)
  const [locationPermission, setLocationPermission] = useState('prompt') // 'prompt', 'granted', 'denied'

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

  // Function to get user's current location
  const getUserLocation = async () => {
    // First try IP-based geolocation (works with VPNs)
    try {
      const ipResponse = await fetch('https://ipapi.co/json/')
      if (ipResponse.ok) {
        const ipData = await ipResponse.json()
        console.log('IP-based location:', ipData)
        
        if (ipData.country_code) {
          const countryInfo = {
            code: ipData.country_code,
            name: ipData.country_name,
            city: ipData.city || 'Unknown City',
            method: 'ip'
          }
          setDetectedCountry(countryInfo)
          setLocationPermission('granted')
          console.log('Detected country from IP:', countryInfo)
          return
        }
      }
    } catch (error) {
      console.error('Error getting IP-based location:', error)
    }

    // Fallback to GPS if IP detection fails
    if (!navigator.geolocation) {
      console.error('Geolocation is not supported by this browser')
      setLocationPermission('denied')
      detectCountryFromTimezone()
      return
    }

    setLocationPermission('prompt')

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const location = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy
        }
        setUserLocation(location)
        setLocationPermission('granted')
        console.log('Location obtained:', location)

        // Reverse geocode to get country
        reverseGeocode(location.latitude, location.longitude)
      },
      (error) => {
        console.error('Error getting location:', error)
        setLocationPermission('denied')

        // Fallback: try to detect country from timezone
        detectCountryFromTimezone()
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000 // 5 minutes
      }
    )
  }

  // Function to reverse geocode coordinates to country
  const reverseGeocode = async (lat, lng) => {
    try {
      // Using a free reverse geocoding service
      const response = await fetch(
        `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lng}&localityLanguage=en`
      )
      
      if (!response.ok) {
        throw new Error('Reverse geocoding failed')
      }
      
      const data = await response.json()
      console.log('Reverse geocoding result:', data)
      
      if (data.countryCode) {
        const countryInfo = {
          code: data.countryCode,
          name: data.countryName,
          city: data.city || data.locality || 'Unknown City'
        }
        setDetectedCountry(countryInfo)
        console.log('Detected country:', countryInfo)
      }
    } catch (error) {
      console.error('Error reverse geocoding:', error)
      // Fallback to timezone detection
      detectCountryFromTimezone()
    }
  }

  // Fallback function to detect country from timezone
  const detectCountryFromTimezone = () => {
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
      console.log('Detected timezone:', timezone)
      
      // Map common timezones to country codes
      const timezoneToCountry = {
        'America/New_York': 'US',
        'America/Los_Angeles': 'US',
        'America/Chicago': 'US',
        'America/Denver': 'US',
        'Europe/London': 'GB',
        'Europe/Paris': 'FR',
        'Europe/Berlin': 'DE',
        'Europe/Rome': 'IT',
        'Europe/Madrid': 'ES',
        'Asia/Tokyo': 'JP',
        'Asia/Shanghai': 'CN',
        'Asia/Kolkata': 'IN',
        'Asia/Dubai': 'AE',
        'Australia/Sydney': 'AU',
        'America/Toronto': 'CA',
        'America/Mexico_City': 'MX',
        'America/Sao_Paulo': 'BR',
        'Asia/Seoul': 'KR',
        'Asia/Singapore': 'SG',
        'Europe/Amsterdam': 'NL',
        'Europe/Stockholm': 'SE',
        'Europe/Zurich': 'CH',
        'Asia/Bangkok': 'TH',
        'Asia/Manila': 'PH',
        'Asia/Jakarta': 'ID',
        'Asia/Kuala_Lumpur': 'MY',
        'Pacific/Auckland': 'NZ',
        'America/Argentina/Buenos_Aires': 'AR',
        'America/Chile/Santiago': 'CL',
        'America/Colombia/Bogota': 'CO',
        'America/Peru/Lima': 'PE',
        'Africa/Cairo': 'EG',
        'Africa/Johannesburg': 'ZA',
        'Asia/Tehran': 'IR',
        'Asia/Karachi': 'PK',
        'Asia/Dhaka': 'BD',
        'Asia/Kathmandu': 'NP',
        'Asia/Colombo': 'LK',
        'Europe/Moscow': 'RU',
        'Europe/Kiev': 'UA',
        'Europe/Warsaw': 'PL',
        'Europe/Prague': 'CZ',
        'Europe/Budapest': 'HU',
        'Europe/Athens': 'GR',
        'Europe/Lisbon': 'PT',
        'Europe/Dublin': 'IE',
        'Europe/Helsinki': 'FI',
        'Europe/Oslo': 'NO',
        'Europe/Copenhagen': 'DK',
        'Europe/Brussels': 'BE',
        'Europe/Vienna': 'AT'
      }
      
      const countryCode = timezoneToCountry[timezone]
      if (countryCode) {
        const countryInfo = {
          code: countryCode,
          name: getCountryName(countryCode),
          city: 'Detected from timezone',
          method: 'timezone'
        }
        setDetectedCountry(countryInfo)
        console.log('Detected country from timezone:', countryInfo)
      }
    } catch (error) {
      console.error('Error detecting country from timezone:', error)
    }
  }

  // Helper function to get country name from code
  const getCountryName = (code) => {
    const countryNames = {
      'US': 'United States',
      'GB': 'United Kingdom',
      'FR': 'France',
      'DE': 'Germany',
      'IT': 'Italy',
      'ES': 'Spain',
      'JP': 'Japan',
      'CN': 'China',
      'IN': 'India',
      'AE': 'United Arab Emirates',
      'AU': 'Australia',
      'CA': 'Canada',
      'MX': 'Mexico',
      'BR': 'Brazil',
      'KR': 'South Korea',
      'SG': 'Singapore',
      'NL': 'Netherlands',
      'SE': 'Sweden',
      'CH': 'Switzerland',
      'TH': 'Thailand',
      'PH': 'Philippines',
      'ID': 'Indonesia',
      'MY': 'Malaysia',
      'NZ': 'New Zealand',
      'AR': 'Argentina',
      'CL': 'Chile',
      'CO': 'Colombia',
      'PE': 'Peru',
      'EG': 'Egypt',
      'ZA': 'South Africa',
      'IR': 'Iran',
      'PK': 'Pakistan',
      'BD': 'Bangladesh',
      'NP': 'Nepal',
      'LK': 'Sri Lanka',
      'RU': 'Russia',
      'UA': 'Ukraine',
      'PL': 'Poland',
      'CZ': 'Czech Republic',
      'HU': 'Hungary',
      'GR': 'Greece',
      'PT': 'Portugal',
      'IE': 'Ireland',
      'FI': 'Finland',
      'NO': 'Norway',
      'DK': 'Denmark',
      'BE': 'Belgium',
      'AT': 'Austria'
    }
    return countryNames[code] || code
  }

  // Helper function to get country flag emoji
  const getCountryFlag = (code) => {
    const flags = {
      'US': '🇺🇸',
      'GB': '🇬🇧',
      'FR': '🇫🇷',
      'DE': '🇩🇪',
      'IT': '🇮🇹',
      'ES': '🇪🇸',
      'JP': '🇯🇵',
      'CN': '🇨🇳',
      'IN': '🇮🇳',
      'AE': '🇦🇪',
      'AU': '🇦🇺',
      'CA': '🇨🇦',
      'MX': '🇲🇽',
      'BR': '🇧🇷',
      'KR': '🇰🇷',
      'SG': '🇸🇬',
      'NL': '🇳🇱',
      'SE': '🇸🇪',
      'CH': '🇨🇭',
      'TH': '🇹🇭',
      'PH': '🇵🇭',
      'ID': '🇮🇩',
      'MY': '🇲🇾',
      'NZ': '🇳🇿',
      'AR': '🇦🇷',
      'CL': '🇨🇱',
      'CO': '🇨🇴',
      'PE': '🇵🇪',
      'EG': '🇪🇬',
      'ZA': '🇿🇦',
      'IR': '🇮🇷',
      'PK': '🇵🇰',
      'BD': '🇧🇩',
      'NP': '🇳🇵',
      'LK': '🇱🇰',
      'RU': '🇷🇺',
      'UA': '🇺🇦',
      'PL': '🇵🇱',
      'CZ': '🇨🇿',
      'HU': '🇭🇺',
      'GR': '🇬🇷',
      'PT': '🇵🇹',
      'IE': '🇮🇪',
      'FI': '🇫🇮',
      'NO': '🇳🇴',
      'DK': '🇩🇰',
      'BE': '🇧🇪',
      'AT': '🇦🇹'
    }
    return flags[code] || '🌍'
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
    setIsBackgroundMode(true)
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
        const countries = await fetchCountries()
        setAvailableCountries(countries)
        
        const data = await fetchCountryData(selectedCountry)
        setCountryData(data)

        const alertsData = await fetchAlerts()
        setAlerts(alertsData)
        
        // Get current location from simulation
        await getCurrentLocation()
        
        // Initialize location detection
        getUserLocation()
        
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
    <div className="loading-container">
      <div className="modern-loader">
        <div className="loader-ring"></div>
        <div className="loader-ring"></div>
        <div className="loader-ring"></div>
      </div>
      <p className="loading-text">Loading your travel guide...</p>
    </div>
  )

  // Error message component
  const ErrorMessage = ({ message }) => (
    <div className="error-card">
      <AlertTriangle size={24} className="error-icon" />
      <p>{message}</p>
    </div>
  )

  // Tab content components
  const WelcomeTab = ({ welcome, isActive }) => (
    <div className={`tab-content ${isActive ? 'active' : ''}`}>
      <div className="welcome-grid">
        {welcome?.map((item, index) => (
          <div key={index} className="welcome-card">
            <div className="welcome-icon">{item.icon}</div>
            <div className="welcome-content">
              <h3 className="welcome-title">{item.title}</h3>
              <p className="welcome-message">{item.message}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )

  const TransportTab = ({ transport, isActive }) => (
    <div className={`tab-content ${isActive ? 'active' : ''}`}>
      <div className="content-card">
        <div className="card-header">
          <MapPin className="header-icon" />
          <h3 className="card-title">Transportation Guide</h3>
        </div>
        <div className="transport-list">
          {transport?.map((tip, index) => (
            <div key={index} className="transport-item">
              <div className="transport-number">{index + 1}</div>
              <p className="transport-text">{tip}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const CultureTab = ({ culture, isActive }) => (
    <div className={`tab-content ${isActive ? 'active' : ''}`}>
      <div className="content-card">
        <div className="card-header">
          <Globe className="header-icon" />
          <h3 className="card-title">Cultural Guidelines</h3>
        </div>
        <div className="culture-grid">
          {culture?.map((tip, index) => (
            <div key={index} className="culture-item">
              <div className="culture-dot"></div>
              <p className="culture-text">{tip}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const LanguageTab = ({ language, isActive }) => (
    <div className={`tab-content ${isActive ? 'active' : ''}`}>
      <div className="content-card">
        <div className="card-header">
          <Globe className="header-icon" />
          <h3 className="card-title">Essential Phrases</h3>
        </div>
        <div className="phrases-container">
          {language?.map((phrase, index) => (
            <div key={index} className="phrase-card">
              <div className="phrase-native">{phrase.native}</div>
              <div className="phrase-meaning">{phrase.meaning}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const AlertsTab = ({ isActive }) => {
    const currentCountryAlerts = alerts?.find(alert => alert.country_code === selectedCountry)

    return (
      <div className={`tab-content ${isActive ? 'active' : ''}`}>
        <div className="content-card">
          <div className="card-header">
            {currentCountryAlerts?.is_anomaly ? 
              <AlertTriangle className="header-icon alert" /> : 
              <CheckCircle className="header-icon safe" />
            }
            <h3 className="card-title">Travel Status</h3>
          </div>
          
          <div className={`status-banner ${currentCountryAlerts?.is_anomaly ? 'alert' : 'safe'}`}>
            {currentCountryAlerts?.is_anomaly ? (
              <div className="status-content">
                <div className="status-badge alert">⚠️ Alert</div>
                <h4>Unusual Activity Detected</h4>
                <div className="alert-metrics">
                  <div className="metric">
                    <span className="metric-value">{currentCountryAlerts.spike_factor}x</span>
                    <span className="metric-label">Spike Factor</span>
                  </div>
                  <div className="metric">
                    <span className="metric-value">{currentCountryAlerts.current_count}</span>
                    <span className="metric-label">News Articles</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="status-content">
                <div className="status-badge safe">✓ Safe</div>
                <h4>Normal Travel Conditions</h4>
                <p>No unusual news activity detected</p>
              </div>
            )}
          </div>

          {currentCountryAlerts?.top_headlines?.length > 0 && (
            <div className="headlines-section">
              <h4 className="headlines-title">Latest Headlines</h4>
              <div className="headlines-grid">
                {currentCountryAlerts.top_headlines.map((headline, index) => (
                  <div key={index} className="headline-card">
                    <a href={headline.url} target="_blank" rel="noopener noreferrer" className="headline-link">
                      {headline.title}
                    </a>
                    <div className="headline-meta">
                      <span className="headline-source">{headline.source}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
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
          <h2>TravelLegal</h2>
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
            <div className="demo-header-buttons">
              <button 
                className="refresh-location"
                onClick={getUserLocation}
                title="Refresh location (useful when changing VPN)"
              >
                🔄 Refresh Location
              </button>
              <button 
                className="close-demo"
                onClick={() => setShowDemoPanel(false)}
              >
                ✕
              </button>
            </div>
          </div>
          <div className="demo-buttons">
            {detectedCountry && (
              <button 
                className="demo-button detected-location"
                onClick={() => simulateTravel(detectedCountry.code)}
              >
                <MapPin size={16} />
                Your Location: {detectedCountry.name} {getCountryFlag(detectedCountry.code)}
                <span className="location-method">
                  {detectedCountry.method === 'timezone' ? '📍 Detected from timezone' : 
                   detectedCountry.method === 'ip' ? '🌐 Location detected' : 
                   '📍 GPS detected'}
                </span>
              </button>
            )}
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
            {locationPermission === 'denied' && (
              <div className="location-error">
                <AlertTriangle size={16} />
                Location access denied. Using timezone detection.
              </div>
            )}
          </div>
          <div className="demo-info">
            <p className="demo-hint">Press 'D' 3 times to toggle this panel</p>
            <p className="available-countries">
              🌍 Any country detected - data scraped in real time
            </p>
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

          .demo-header-buttons {
            display: flex;
            gap: 8px;
            align-items: center;
          }

          .refresh-location {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #93c5fd;
            padding: 6px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s ease;
            white-space: nowrap;
          }

          .refresh-location:hover {
            background: rgba(59, 130, 246, 0.2);
            border-color: rgba(59, 130, 246, 0.5);
            color: #60a5fa;
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
            position: relative;
          }

          .demo-button:hover {
            background: #4b5563;
          }

          .demo-button.detected-location {
            background: linear-gradient(135deg, #3182ce 0%, #2c5282 100%);
            border: 2px solid #3182ce;
            flex-direction: column;
            align-items: flex-start;
            padding: 16px;
          }

          .demo-button.detected-location:hover {
            background: linear-gradient(135deg, #2c5282 0%, #2a4a7c 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(49, 130, 206, 0.3);
          }

          .location-method {
            font-size: 0.75rem;
            opacity: 0.8;
            margin-top: 4px;
            font-style: italic;
          }

          .location-error {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #fed7d7;
            color: #c53030;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 0.875rem;
            border: 1px solid #feb2b2;
          }

          .location-unavailable {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            background: #f7fafc;
            color: #4a5568;
            padding: 16px;
            border-radius: 8px;
            font-size: 0.875rem;
            border: 1px solid #e2e8f0;
            margin-bottom: 12px;
          }

          .location-unavailable div {
            display: flex;
            flex-direction: column;
            gap: 4px;
          }

          .location-unavailable strong {
            color: #1a202c;
            font-size: 0.9rem;
          }

          .unavailable-note {
            font-size: 0.8rem;
            color: #718096;
            font-style: italic;
            margin-top: 4px;
          }

          .demo-info {
            text-align: center;
          }

          .demo-hint {
            margin: 0 0 8px 0;
            font-size: 0.75rem;
            color: #9ca3af;
          }

          .available-countries {
            margin: 0;
            font-size: 0.7rem;
            color: #6b7280;
            font-style: italic;
          }
        `}</style>
        <BackgroundMonitoringScreen />
      </div>
    )
  }

  return (
    <div className="app-container">
      <style>{`
        * {
          box-sizing: border-box;
        }
        
        .app-container {
          background: #ffffff;
          min-height: 100vh;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
          position: relative;
          overflow-x: hidden;
        }
        
        .app-container::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: 
            linear-gradient(135deg, rgba(248, 250, 252, 0.8) 0%, rgba(241, 245, 249, 0.4) 100%);
          pointer-events: none;
        }

        .header {
          position: relative;
          z-index: 10;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          color: #1a202c;
          padding: 40px 24px;
          margin: 20px;
          border-radius: 16px;
          box-shadow: 
            0 4px 6px -1px rgba(0, 0, 0, 0.1),
            0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        .header-content {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          max-width: 480px;
          margin: 0 auto;
        }

        .header-left h1 {
          font-size: 2.5rem;
          font-weight: 800;
          margin: 0 0 12px 0;
          color: #1a202c;
          letter-spacing: -0.025em;
        }

        .header-left .location {
          font-size: 1.125rem;
          color: #4a5568;
          margin: 0 0 20px 0;
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 500;
        }

        .country-selector {
          background: #ffffff;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          padding: 12px 16px;
          color: #1a202c;
          font-size: 1rem;
          cursor: pointer;
          transition: all 0.3s ease;
          min-width: 200px;
          font-weight: 500;
        }

        .country-selector:hover {
          border-color: #3182ce;
          box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1);
        }

        .country-selector:focus {
          outline: none;
          border-color: #3182ce;
          box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.1);
        }

        .country-selector:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .country-selector option {
          background: #ffffff;
          color: #1a202c;
          padding: 8px;
        }

        .header-right {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 56px;
          height: 56px;
          background: #f7fafc;
          border-radius: 16px;
          border: 1px solid #e2e8f0;
          transition: all 0.3s ease;
          color: #4a5568;
        }

        .header-right:hover {
          background: #edf2f7;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .tabs-container {
          position: relative;
          z-index: 10;
          padding: 0 16px;
          margin-bottom: 24px;
        }

        .tabs {
          display: flex;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 16px;
          padding: 8px;
          max-width: 480px;
          margin: 0 auto;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .tab-button {
          flex: 1;
          padding: 12px 16px;
          border-radius: 12px;
          font-weight: 600;
          font-size: 0.9rem;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          background: none;
          border: none;
          cursor: pointer;
          color: #4a5568;
          position: relative;
          text-align: center;
        }

        .tab-button.active {
          background: #3182ce;
          color: #ffffff;
          box-shadow: 0 2px 4px rgba(49, 130, 206, 0.2);
          transform: translateY(-1px);
        }

        .tab-button:hover:not(.active) {
          background: #f7fafc;
          color: #1a202c;
        }

        .content-area {
          position: relative;
          z-index: 10;
          padding: 0 16px 32px;
          max-width: 480px;
          margin: 0 auto;
        }

        .tab-content {
          display: none;
          animation: fadeIn 0.4s ease-out;
        }

        .tab-content.active {
          display: block;
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .content-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 16px;
          padding: 32px;
          margin-bottom: 24px;
          box-shadow: 
            0 4px 6px -1px rgba(0, 0, 0, 0.1),
            0 2px 4px -1px rgba(0, 0, 0, 0.06);
          transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .content-card:hover {
          transform: translateY(-2px);
          box-shadow: 
            0 10px 15px -3px rgba(0, 0, 0, 0.1),
            0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }

        .card-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 24px;
          padding-bottom: 20px;
          border-bottom: 1px solid rgba(0, 0, 0, 0.1);
        }

        .header-icon {
          color: #3182ce;
        }

        .header-icon.alert {
          color: #e53e3e;
        }

        .header-icon.safe {
          color: #38a169;
        }

        .card-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: #1a202c;
          margin: 0;
          letter-spacing: -0.025em;
        }

        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 60px 20px;
        }

        .modern-loader {
          position: relative;
          width: 60px;
          height: 60px;
        }

        .loader-ring {
          position: absolute;
          width: 60px;
          height: 60px;
          border: 3px solid transparent;
          border-top-color: #667eea;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .loader-ring:nth-child(2) {
          width: 45px;
          height: 45px;
          top: 7.5px;
          left: 7.5px;
          border-top-color: #764ba2;
          animation-duration: 0.8s;
          animation-direction: reverse;
        }

        .loader-ring:nth-child(3) {
          width: 30px;
          height: 30px;
          top: 15px;
          left: 15px;
          border-top-color: #ff7b9c;
          animation-duration: 0.6s;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .loading-text {
          margin-top: 24px;
          color: #4a5568;
          font-size: 1rem;
          font-weight: 500;
        }

        .error-card {
          background: #fed7d7;
          border: 1px solid #feb2b2;
          border-radius: 16px;
          padding: 24px;
          display: flex;
          align-items: center;
          gap: 12px;
          color: #c53030;
          font-weight: 500;
        }

        .error-icon {
          flex-shrink: 0;
        }

        .welcome-grid {
          display: grid;
          gap: 20px;
        }

        .welcome-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 16px;
          padding: 24px;
          display: flex;
          align-items: flex-start;
          gap: 16px;
          transition: all 0.3s ease;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .welcome-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
          border-color: #3182ce;
        }

        .welcome-icon {
          font-size: 2rem;
          flex-shrink: 0;
        }

        .welcome-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: #1a202c;
          margin: 0 0 8px 0;
          letter-spacing: -0.025em;
        }

        .welcome-message {
          color: #4a5568;
          margin: 0;
          line-height: 1.6;
          font-size: 1rem;
        }

        .transport-list {
          display: grid;
          gap: 16px;
        }

        .transport-item {
          display: flex;
          align-items: flex-start;
          gap: 16px;
          padding: 16px 0;
        }

        .transport-number {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          background: #3182ce;
          color: white;
          border-radius: 50%;
          font-weight: 700;
          font-size: 0.9rem;
          flex-shrink: 0;
        }

        .transport-text {
          color: #4a5568;
          margin: 0;
          line-height: 1.6;
          font-size: 1rem;
        }

        .culture-grid {
          display: grid;
          gap: 16px;
        }

        .culture-item {
          display: flex;
          align-items: flex-start;
          gap: 16px;
          padding: 16px 0;
        }

        .culture-dot {
          width: 12px;
          height: 12px;
          background: #3182ce;
          border-radius: 50%;
          margin-top: 6px;
          flex-shrink: 0;
        }

        .culture-text {
          color: #4a5568;
          margin: 0;
          line-height: 1.6;
          font-size: 1rem;
        }

        .phrases-container {
          display: grid;
          gap: 16px;
        }

        .phrase-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 16px;
          padding: 20px;
          transition: all 0.3s ease;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .phrase-card:hover {
          transform: translateX(4px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
          border-color: #3182ce;
        }

        .phrase-native {
          font-weight: 700;
          color: #1a202c;
          font-size: 1.125rem;
          margin-bottom: 8px;
          letter-spacing: -0.025em;
        }

        .phrase-meaning {
          color: #4a5568;
          font-size: 1rem;
        }

        .status-banner {
          border-radius: 20px;
          padding: 24px;
          margin: 20px 0;
          backdrop-filter: blur(10px);
        }

        .status-banner.alert {
          background: #fed7d7;
          border: 1px solid #feb2b2;
        }

        .status-banner.safe {
          background: #c6f6d5;
          border: 1px solid #9ae6b4;
        }

        .status-badge {
          display: inline-block;
          padding: 6px 12px;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 700;
          margin-bottom: 12px;
        }

        .status-badge.alert {
          background: #e53e3e;
          color: #ffffff;
        }

        .status-badge.safe {
          background: #38a169;
          color: #ffffff;
        }

        .status-content h4 {
          font-size: 1.25rem;
          font-weight: 700;
          color: #1a202c;
          margin: 0 0 8px 0;
          letter-spacing: -0.025em;
        }

        .alert-metrics {
          display: flex;
          gap: 24px;
          margin-top: 16px;
        }

        .metric {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .metric-value {
          font-size: 1.5rem;
          font-weight: 800;
          color: #e53e3e;
        }

        .metric-label {
          font-size: 0.875rem;
          color: #4a5568;
          margin-top: 4px;
          font-weight: 500;
        }

        .headlines-section {
          margin-top: 32px;
        }

        .headlines-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: #1a202c;
          margin: 0 0 20px 0;
          letter-spacing: -0.025em;
        }

        .headlines-grid {
          display: grid;
          gap: 16px;
        }

        .headline-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 16px;
          padding: 20px;
          transition: all 0.3s ease;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .headline-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
          border-color: #3182ce;
        }

        .headline-link {
          color: #3182ce;
          text-decoration: none;
          font-weight: 600;
          line-height: 1.5;
          display: block;
          margin-bottom: 8px;
          font-size: 1rem;
        }

        .headline-link:hover {
          text-decoration: underline;
          color: #2c5282;
        }

        .headline-source {
          color: #4a5568;
          font-size: 0.875rem;
          font-weight: 500;
        }

        .mode-toggle {
          position: fixed;
          top: 20px;
          right: 20px;
          z-index: 100;
        }

        .mode-toggle-button {
          background: #ffffff;
          color: #4a5568;
          border: 1px solid #e2e8f0;
          padding: 8px 12px;
          border-radius: 20px;
          font-size: 0.75rem;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          font-weight: 500;
        }

        .mode-toggle-button:hover {
          background: #f7fafc;
          border-color: #3182ce;
        }

        @media (max-width: 480px) {
          .header {
            margin: 8px;
            padding: 24px 20px;
          }
          
          .tabs-container {
            padding: 0 8px;
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
          <div className="header-left">
            <h1>TravelLegal</h1>
            <div className="location">
              <MapPin size={16} />
              {loading ? 'Loading...' : countryData?.name || 'Unknown Location'}
            </div>
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
          <div className="header-right">
            <Bell size={24} />
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="tabs-container">
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
