import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Bell, Loader, Wifi, WifiOff, RefreshCw, MapPin, Plane, Users, MessageSquare } from 'lucide-react'

// Constants
const API_ENDPOINT = 'http://localhost:8000/api/country-info'
const DEMO_DATA = {
  name: "Japan",
  flag: "🇯🇵",
  welcome: [
    {
      icon: "🎌",
      title: "Welcome to Japan!",
      message: "Konnichiwa! Your travel companion is ready to help you navigate this amazing country."
    },
    {
      icon: "🏮",
      title: "Cultural Experience",
      message: "Discover the perfect blend of ancient traditions and cutting-edge modern innovations."
    },
    {
      icon: "🗾",
      title: "Geography & Climate",
      message: "From snowy Hokkaido to tropical Okinawa, Japan offers diverse landscapes and experiences."
    }
  ],
  transport: [
    "IC cards (Suica/Pasmo) work on all trains, subways, and buses",
    "Follow blue signs for domestic flights, red signs for international",
    "Shinkansen (bullet train) requires seat reservations for long distances",
    "Taxis are expensive but extremely reliable, clean, and safe",
    "Train stations have English announcements and signage",
    "Rush hours are 7-9 AM and 5-7 PM - expect crowded trains"
  ],
  culture: [
    "Remove shoes when entering homes, temples, and traditional restaurants",
    "Bowing is customary - a slight nod is perfectly acceptable for visitors",
    "Keep voices low on public transportation and avoid phone calls",
    "Cash is still preferred - many places don't accept credit cards",
    "Tipping is not expected and can sometimes be considered rude",
    "Wait for others to exit before boarding trains or elevators"
  ],
  language: [
    {
      native: "こんにちは (Konnichiwa)",
      meaning: "Hello (formal daytime greeting)",
      pronunciation: "kon-nee-chee-wah"
    },
    {
      native: "ありがとうございます (Arigatou gozaimasu)",
      meaning: "Thank you very much",
      pronunciation: "ah-ree-gah-toh go-zah-ee-mahs"
    },
    {
      native: "すみません (Sumimasen)",
      meaning: "Excuse me / I'm sorry",
      pronunciation: "soo-mee-mah-sen"
    },
    {
      native: "英語を話せますか？ (Eigo wo hanasemasu ka?)",
      meaning: "Do you speak English?",
      pronunciation: "eh-go wo hah-nah-seh-mahs kah"
    },
    {
      native: "トイレはどこですか？ (Toire wa doko desu ka?)",
      meaning: "Where is the bathroom?",
      pronunciation: "toy-reh wah doh-koh dess kah"
    }
  ]
}

const TravelWelcomeApp = () => {
  // State management
  const [countryData, setCountryData] = useState(null)
  const [activeTab, setActiveTab] = useState('welcome')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isOnline, setIsOnline] = useState(true) // Default to true, will be updated on client

  // Memoized tab configuration
  const tabs = useMemo(() => [
    { id: 'welcome', label: 'Welcome', icon: MapPin },
    { id: 'transport', label: 'Transport', icon: Plane },
    { id: 'culture', label: 'Culture', icon: Users },
    { id: 'language', label: 'Language', icon: MessageSquare }
  ], [])

  // Network status monitoring
  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return

    // Set initial online status
    setIsOnline(navigator.onLine)

    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // API call with better error handling
  const fetchCountryData = useCallback(async () => {
    if (!isOnline) {
      throw new Error('No internet connection. Please check your network and try again.')
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout

    try {
      const response = await fetch(API_ENDPOINT, {
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
        },
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      
      // Validate data structure
      if (!data.name || !data.welcome) {
        throw new Error('Invalid data format received from server')
      }

      return data
    } catch (error) {
      clearTimeout(timeoutId)
      
      if (error.name === 'AbortError') {
        throw new Error('Request timed out. Please try again.')
      }
      
      console.error('API Error:', error)
      throw error
    }
  }, [isOnline])

  // Load demo data
  const loadDemoData = useCallback(() => {
    setLoading(true)
    setError(null)
    
    // Simulate API delay
    setTimeout(() => {
      setCountryData(DEMO_DATA)
      setLoading(false)
    }, 1500)
  }, [])

  // Retry mechanism
  const retryDataFetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      const data = await fetchCountryData()
      setCountryData(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [fetchCountryData])

  // Initialize the app
  useEffect(() => {
    const initApp = async () => {
      try {
        const data = await fetchCountryData()
        setCountryData(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    initApp()
  }, [fetchCountryData])

  // Keyboard navigation for tabs
  const handleKeyDown = useCallback((event, tabId) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      setActiveTab(tabId)
    }
  }, [])

  // Components
  const LoadingSpinner = () => (
    <div className="text-center py-20 px-5" role="status" aria-label="Loading country information">
      <div className="inline-block w-12 h-12 border-3 border-slate-200 rounded-full border-t-blue-600 animate-spin mb-4" aria-hidden="true"></div>
      <p className="text-slate-600 text-sm">Loading country information...</p>
    </div>
  )

  const ErrorMessage = ({ message }) => (
    <div className="py-20 px-5 text-center" role="alert">
      <div className="bg-white rounded-2xl p-8 mx-5 border border-red-200 shadow-sm">
        <WifiOff size={24} className="text-red-500 mx-auto mb-4 block" />
        <h3 className="text-red-600 text-xl font-bold mb-2">Connection Error</h3>
        <p className="text-gray-600 mb-6 leading-relaxed">{message}</p>
        <div className="flex gap-3 justify-center flex-wrap">
          <button 
            onClick={retryDataFetch} 
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold text-sm border-none cursor-pointer transition-all flex items-center gap-2 hover:bg-blue-700 hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={loading}
          >
            <RefreshCw size={16} />
            {loading ? 'Retrying...' : 'Try Again'}
          </button>
          <button 
            onClick={loadDemoData} 
            className="px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-semibold text-sm border border-gray-300 cursor-pointer transition-all flex items-center gap-2 hover:bg-gray-200"
            disabled={loading}
          >
            Load Demo Data
          </button>
        </div>
      </div>
    </div>
  )

  const WelcomeTab = ({ welcome }) => (
    <div className="animate-fadeIn" role="tabpanel" aria-labelledby="welcome-tab">
      {welcome?.map((item, index) => (
        <div key={index} className="bg-white rounded-2xl p-6 mb-4 shadow-sm border border-black/5 border-l-4 border-l-blue-600">
          <div className="flex items-start gap-4">
            <div className="text-3xl flex-shrink-0 w-12 h-12 flex items-center justify-center bg-blue-100 rounded-xl" aria-hidden="true">{item.icon}</div>
            <div>
              <h3 className="font-bold text-gray-800 mb-2 text-lg">{item.title}</h3>
              <p className="text-gray-600 leading-relaxed">{item.message}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )

  const TransportTab = ({ transport }) => (
    <div className="animate-fadeIn" role="tabpanel" aria-labelledby="transport-tab">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-black/5">
        <h3 className="text-xl font-bold mb-5 text-gray-800 flex items-center gap-3 pb-3 border-b-2 border-gray-100">
          <Plane size={20} aria-hidden="true" />
          Transportation Tips
        </h3>
        <ul className="space-y-3" role="list">
          {transport?.map((tip, index) => (
            <li key={index} className="flex items-start gap-3 py-3 border-b border-slate-50 last:border-b-0" role="listitem">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0" aria-hidden="true"></div>
              <span className="text-gray-700 leading-relaxed">{tip}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )

  const CultureTab = ({ culture }) => (
    <div className="animate-fadeIn" role="tabpanel" aria-labelledby="culture-tab">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-black/5">
        <h3 className="text-xl font-bold mb-5 text-gray-800 flex items-center gap-3 pb-3 border-b-2 border-gray-100">
          <Users size={20} aria-hidden="true" />
          Cultural Guidelines
        </h3>
        <ul className="space-y-3" role="list">
          {culture?.map((tip, index) => (
            <li key={index} className="flex items-start gap-3 py-3 border-b border-slate-50 last:border-b-0" role="listitem">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0" aria-hidden="true"></div>
              <span className="text-gray-700 leading-relaxed">{tip}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )

  const LanguageTab = ({ language }) => (
    <div className="animate-fadeIn" role="tabpanel" aria-labelledby="language-tab">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-black/5">
        <h3 className="text-xl font-bold mb-5 text-gray-800 flex items-center gap-3 pb-3 border-b-2 border-gray-100">
          <MessageSquare size={20} aria-hidden="true" />
          Essential Phrases
        </h3>
        <div className="space-y-4">
          {language?.map((phrase, index) => (
            <div key={index} className="bg-slate-50 rounded-2xl p-5 border border-slate-200 transition-all hover:bg-slate-100 hover:border-slate-300">
              <div className="font-bold text-blue-800 mb-2 text-lg" lang="ja">{phrase.native}</div>
              <div className="text-gray-700 mb-1.5 font-medium">{phrase.meaning}</div>
              {phrase.pronunciation && (
                <div className="text-gray-500 italic">
                  <small>Pronunciation: {phrase.pronunciation}</small>
                </div>
              )}
            </div>
          ))}
        </div>
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

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      {/* Header */}
      <header className="bg-gradient-to-br from-blue-800 via-blue-600 to-blue-400 text-white p-6 rounded-b-3xl shadow-lg relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-transparent pointer-events-none"></div>
        <div className="flex justify-between items-center max-w-sm mx-auto relative z-10">
          <div>
            <h1 className="text-3xl font-bold mb-1 text-shadow-sm">Welcome {countryData?.flag || ''}</h1>
            <p className="text-sm opacity-90 font-medium">
              {loading ? 'Loading...' : 
               countryData?.name || 
               'Unknown Location'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div 
              className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'} ${isOnline ? 'animate-pulse' : ''}`}
              title={isOnline ? 'Connected' : 'Offline'}
              aria-label={isOnline ? 'Online' : 'Offline'}
            />
            <Bell size={24} aria-label="Notifications" />
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="flex bg-white/80 backdrop-blur-sm mx-4 my-5 rounded-2xl p-1.5 border border-white/20 shadow-sm max-w-sm mx-auto" role="tablist">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            id={`${id}-tab`}
            className={`flex-1 px-2 py-3.5 rounded-2xl font-semibold text-xs transition-all duration-300 ease-out bg-none border-none cursor-pointer text-slate-600 relative flex flex-col items-center gap-1 ${
              activeTab === id
                ? 'bg-white text-blue-800 shadow-lg border border-blue-100 -translate-y-0.5'
                : 'hover:bg-white/60 hover:-translate-y-0.5'
            }`}
            onClick={() => setActiveTab(id)}
            onKeyDown={(e) => handleKeyDown(e, id)}
            role="tab"
            aria-selected={activeTab === id}
            aria-controls={`${id}-panel`}
          >
            <Icon size={16} className="w-4 h-4 mb-0.5" />
            {label}
          </button>
        ))}
      </nav>

      {/* Content Area */}
      <main className="px-4 pb-8 max-w-sm mx-auto">
        {loading && <LoadingSpinner />}
        {error && <ErrorMessage message={error} />}
        {!loading && !error && renderTabContent()}
      </main>
    </div>
  )
}

export default TravelWelcomeApp