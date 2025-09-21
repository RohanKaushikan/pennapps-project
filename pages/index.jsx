
import { useState, useEffect } from 'react'
import { Bell, Loader, AlertTriangle, Globe, User, LogIn } from 'lucide-react'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Bell, Loader, Wifi, WifiOff, RefreshCw, MapPin, Plane, Users, MessageSquare, User, LogOut, LogIn } from 'lucide-react'
import { useLocation } from '../src/hooks/useLocation'
import { getCountryFromCoordinates, getCountryCoordinates } from '../src/utils/countryMapping'
import { getDemoCountryPhoto } from '../src/utils/photoService'
import Globe from '../src/components/Globe'

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


// Alternative country data for demo users
const FRANCE_DATA = {
  name: "France",
  flag: "🇫🇷",
  welcome: [
    {
      icon: "🥖",
      title: "Bienvenue en France!",
      message: "Welcome to France! Your travel companion is ready to help you explore the country of art, culture, and cuisine."
    },
    {
      icon: "🗼",
      title: "City of Light",
      message: "From the Eiffel Tower to charming countryside villages, France offers endless discoveries."
    }
  ],
  transport: [
    "Metro tickets work on buses, trains, and the subway in Paris",
    "TGV high-speed trains connect major cities efficiently", 
    "Validate your ticket before boarding regional trains",
    "Taxis are metered but can be expensive in city centers"
  ],
  culture: [
    "Greeting with 'Bonjour' is essential when entering shops",
    "Lunch is typically 12-2 PM, dinner after 7:30 PM",
    "Tipping 5-10% is appreciated but not mandatory",
    "Dress codes tend to be more formal than other countries"
  ],
  language: [
    {
      native: "Bonjour",
      meaning: "Hello / Good morning",
      pronunciation: "bon-ZHOOR"
    },
    {
      native: "Merci beaucoup", 
      meaning: "Thank you very much",
      pronunciation: "mer-SEE bo-KOO"
    },
    {
      native: "Excusez-moi",
      meaning: "Excuse me",
      pronunciation: "ex-kew-ZAY mwah"
    }
  ]
}

const TravelWelcomeApp = () => {
  // State management
  const [countryData, setCountryData] = useState(null)
  const [activeTab, setActiveTab] = useState('welcome')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [showApp, setShowApp] = useState(false)
  const [selectedCountry, setSelectedCountry] = useState('japan')

  const [isOnline, setIsOnline] = useState(true) // Default to true, will be updated on client
  const [isSignedIn, setIsSignedIn] = useState(false)
  const [showSignInModal, setShowSignInModal] = useState(false)
  const [user, setUser] = useState(null)
  const [showUserMenu, setShowUserMenu] = useState(false)
  
  // Location and globe state
  const { location, loading: locationLoading, error: locationError } = useLocation()
  const [currentCountry, setCurrentCountry] = useState(null)
  const [targetCountry, setTargetCountry] = useState(null)
  const [targetCountryPhoto, setTargetCountryPhoto] = useState(null)
  const [isGlobeAnimating, setIsGlobeAnimating] = useState(false)
  const [globeAnimationComplete, setGlobeAnimationComplete] = useState(false)
  const [showContent, setShowContent] = useState(false)

  // Location detection and country mapping
  useEffect(() => {
    if (location) {
      const detectedCountry = getCountryFromCoordinates(location.latitude, location.longitude)
      setCurrentCountry(detectedCountry)
      
      // If signed in and we have a target country, start globe animation
      if (isSignedIn && countryData && countryData.name !== detectedCountry.name) {
        const targetCoords = getCountryCoordinates(countryData.name)
        const targetPhoto = getDemoCountryPhoto(countryData.name)
        setTargetCountry(targetCoords)
        setTargetCountryPhoto(targetPhoto)
        setIsGlobeAnimating(true)
      }
    }
  }, [location, isSignedIn, countryData])

  // Sign in/out functions
  const handleSignIn = useCallback((userData) => {
    setUser(userData)
    setIsSignedIn(true)
    setShowSignInModal(false)
    setShowUserMenu(false)
    
    // Filter out user's home country from current data
    if (countryData && countryData.name === userData.homeCountry) {
      setCountryData(null)
      loadDemoData() // Load different country data
    }
  }, [countryData])

  const handleSignOut = useCallback(() => {
    setUser(null)
    setIsSignedIn(false)
    setShowUserMenu(false)
    setTargetCountry(null)
    setIsGlobeAnimating(false)
    setGlobeAnimationComplete(false)
  }, [])

  // Globe animation completion handler
  const handleGlobeAnimationComplete = useCallback(() => {
    setIsGlobeAnimating(false)
    setGlobeAnimationComplete(true)
    // Show content after animation completes
    setTimeout(() => {
      setShowContent(true)
    }, 500)
  }, [])

  // Filter function to exclude user's home country
  const shouldShowCountryData = useCallback((data) => {
    if (!isSignedIn || !user?.homeCountry) return true
    return data?.name !== user.homeCountry
  }, [isSignedIn, user?.homeCountry])

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

  // API call with better error handling and country filtering
  const fetchCountryData = useCallback(async () => {
    if (!isOnline) {
      throw new Error('No internet connection. Please check your network and try again.')
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout


    try {

      console.log('Fetching country data from:', 'http://localhost:8000/api/v1/countries/country-info')
      const response = await fetch('http://localhost:8000/api/v1/countries/country-info')
      console.log('Response status:', response.status)
      if (!response.ok) {
        throw new Error(`Failed to fetch country data: ${response.status}`)

      const response = await fetch(API_ENDPOINT, {
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...(isSignedIn && user?.id && {
            'Authorization': `Bearer ${user.token}`,
            'X-User-Home-Country': user.homeCountry
          })
        },
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`)

      }

      const data = await response.json()

      console.log('Received data:', data)

      
      // Validate data structure
      if (!data.name || !data.welcome) {
        throw new Error('Invalid data format received from server')
      }

      // Filter out home country data if signed in
      if (!shouldShowCountryData(data)) {
        throw new Error("Currently in your home country. Travel information will appear when you visit other countries.")
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
  }, [isOnline, isSignedIn, user, shouldShowCountryData])

  // Load demo data with country filtering
  const loadDemoData = useCallback(() => {
    setLoading(true)
    setError(null)
    
    // If signed in, provide different country data based on user's home country
    let demoCountry = DEMO_DATA
    if (isSignedIn && user?.homeCountry) {
      // If user is from Japan, show different country (e.g., France)
      if (user.homeCountry === 'Japan') {
        demoCountry = FRANCE_DATA
      }
      // Add more country alternatives based on user's home country
      else if (user.homeCountry === 'United States') {
        // Show Japan data for US users, etc.
        demoCountry = DEMO_DATA
      }
    }
    
    // Simulate API delay
    setTimeout(() => {
      if (shouldShowCountryData(demoCountry)) {
        setCountryData(demoCountry)
      } else {
        setCountryData(null)
        setError("Currently showing your home country. Travel to see location-specific information.")
      }
      setLoading(false)
    }, 1500)
  }, [isSignedIn, user?.homeCountry, shouldShowCountryData])

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

  // Initialize the app
  useEffect(() => {
    const initApp = async () => {
      try {
        const data = await fetchCountryData()
        setCountryData(data)
        
        // If not signed in, show content immediately
        if (!isSignedIn) {
          setShowContent(true)
          setLoading(false)
        }
        // If signed in, wait for globe animation to complete
        else {
          setLoading(false)
        }
      } catch (err) {
        setError(err.message)
        setLoading(false)
        setShowContent(true)
      }

    }
  }


  // Initialize the app
  useEffect(() => {
    setCountryData(countryOptions[selectedCountry])
  }, [selectedCountry])

    initApp()
  }, [fetchCountryData, isSignedIn])

  // Keyboard navigation for tabs
  const handleKeyDown = useCallback((event, tabId) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      setActiveTab(tabId)
    }
  }, [])


  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showUserMenu && !event.target.closest('.user-menu-container')) {
        setShowUserMenu(false)
      }
    }

    if (showUserMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showUserMenu])

  // Components
  const SignInModal = () => (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm" onClick={() => setShowSignInModal(false)}>
      <div className="bg-white rounded-2xl w-11/12 max-w-md max-h-[90vh] overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="p-6 pb-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-800">Sign In to TravelEase</h2>
          <button 
            onClick={() => setShowSignInModal(false)}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"
            aria-label="Close modal"
          >
            ×
          </button>
        </div>
        <div className="p-6">
          <p className="text-gray-600 mb-5 leading-relaxed">Sign in to get personalized travel information that excludes your home country.</p>
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Demo Users:</h3>
            <button 
              onClick={() => handleSignIn({
                id: '1',
                name: 'John Smith',
                email: 'john@example.com',
                homeCountry: 'United States',
                token: 'demo-token-us'
              })}
              className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl cursor-pointer text-sm font-medium text-gray-700 flex items-center gap-3 transition-all hover:bg-gray-100 hover:border-gray-300 hover:-translate-y-0.5 mb-2 text-left"
            >
              <User size={16} />
              John Smith (USA) - See Japan info
            </button>
            <button 
              onClick={() => handleSignIn({
                id: '2', 
                name: 'Yuki Tanaka',
                email: 'yuki@example.com',
                homeCountry: 'Japan',
                token: 'demo-token-jp'
              })}
              className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl cursor-pointer text-sm font-medium text-gray-700 flex items-center gap-3 transition-all hover:bg-gray-100 hover:border-gray-300 hover:-translate-y-0.5 text-left"
            >
              <User size={16} />
              Yuki Tanaka (Japan) - See France info
            </button>
          </div>
        </div>
      </div>
    </div>
  )

  const UserMenu = () => (
    <div className="absolute top-full right-0 mt-2 bg-white rounded-xl shadow-xl border border-gray-200 min-w-[220px] overflow-hidden z-50">
      <div className="p-4 border-b border-gray-100 flex items-center gap-3">
        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
          <User size={18} className="text-blue-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-gray-800 truncate">{user?.name}</div>
          <div className="text-xs text-gray-500 truncate">From {user?.homeCountry}</div>
          <div className="text-xs text-gray-400 truncate">{user?.email}</div>
        </div>
      </div>
      <button 
        onClick={handleSignOut} 
        className="w-full p-3 bg-none border-none text-red-600 cursor-pointer text-sm font-medium flex items-center gap-2 transition-colors hover:bg-red-50"
      >
        <LogOut size={16} />
        Sign Out
      </button>
    </div>
  )

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

  return (
    <div className="min-h-screen font-sans relative">
      {/* Globe Background */}
      <div className="fixed inset-0 z-0">
        <Globe
          currentLocation={location}
          targetCountry={targetCountry}
          targetCountryPhoto={targetCountryPhoto}
          isAnimating={isGlobeAnimating}
          onAnimationComplete={handleGlobeAnimationComplete}
          isSignedIn={isSignedIn}
        />
      </div>
      
      {/* Content Overlay */}
      <div className="relative z-10 min-h-screen bg-black/20 backdrop-blur-sm">
        {/* Header */}
        <header className="bg-gradient-to-br from-blue-800/90 via-blue-600/90 to-blue-400/90 text-white p-6 rounded-b-3xl shadow-lg relative overflow-visible backdrop-blur-md">
        <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-transparent pointer-events-none"></div>
        <div className="flex justify-between items-center max-w-sm mx-auto relative z-10">
          <div className="flex-1 min-w-0">
            <h1 className="text-3xl font-bold mb-1 text-shadow-sm">Welcome {countryData?.flag || ''}</h1>
            <p className="text-sm opacity-90 font-medium">
              {loading ? 'Loading...' : 
               countryData?.name || 
               'Unknown Location'}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <div 
              className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'} ${isOnline ? 'animate-pulse' : ''}`}
              title={isOnline ? 'Connected' : 'Offline'}
              aria-label={isOnline ? 'Online' : 'Offline'}
            />
            <Bell size={20} aria-label="Notifications" />
            {isSignedIn ? (
              <div className="relative user-menu-container">
                <button 
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="w-9 h-9 rounded-full bg-white/20 border-2 border-white/30 text-white cursor-pointer flex items-center justify-center transition-all hover:bg-white/30 hover:-translate-y-0.5 backdrop-blur-sm"
                  aria-label="User menu"
                >
                  <User size={20} />
                </button>
                {showUserMenu && <UserMenu />}
              </div>
            ) : (
              <button 
                onClick={() => setShowSignInModal(true)}
                className="bg-white/20 border border-white/30 text-white px-3 py-2 rounded-xl text-sm font-semibold cursor-pointer transition-all flex items-center gap-2 hover:bg-white/30 hover:-translate-y-0.5 backdrop-blur-sm"
                aria-label="Sign in"
              >
                <LogIn size={18} />
                <span className="hidden sm:inline">Sign In</span>
              </button>
            )}

          </div>
        </div>
      </header>

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
      {showContent && (
        <nav className="flex bg-white/90 backdrop-blur-md mx-4 my-5 rounded-2xl p-1.5 border border-white/30 shadow-lg max-w-sm mx-auto" role="tablist">
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
      )}

      {/* Content Area */}
      <main className="px-4 pb-8 max-w-sm mx-auto">
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

        {!loading && !error && showContent && (
          <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20">
            {renderTabContent()}
          </div>
        )}
      </main>

      {/* Sign In Modal */}
      {showSignInModal && <SignInModal />}

      </div>
    </div>
  )
}

export default TravelWelcomeApp