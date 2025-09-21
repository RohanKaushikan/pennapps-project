// Photo service for fetching country images
const UNSPLASH_ACCESS_KEY = 'your_unsplash_access_key' // You'll need to get this from Unsplash
const UNSPLASH_API_URL = 'https://api.unsplash.com'

// Fallback to Pixabay if Unsplash fails
const PIXABAY_API_KEY = 'your_pixabay_api_key' // Alternative free service
const PIXABAY_API_URL = 'https://pixabay.com/api'

// Country-specific search terms for better photo results
const COUNTRY_SEARCH_TERMS = {
  'United States': ['usa', 'america', 'united states'],
  'Canada': ['canada', 'canadian landscape'],
  'Mexico': ['mexico', 'mexican culture'],
  'United Kingdom': ['uk', 'britain', 'england'],
  'France': ['france', 'paris', 'french culture'],
  'Germany': ['germany', 'german culture'],
  'Spain': ['spain', 'spanish culture'],
  'Italy': ['italy', 'italian culture'],
  'Japan': ['japan', 'tokyo', 'japanese culture'],
  'China': ['china', 'chinese culture'],
  'South Korea': ['south korea', 'korean culture'],
  'India': ['india', 'indian culture'],
  'Australia': ['australia', 'australian landscape'],
  'New Zealand': ['new zealand', 'kiwi'],
  'Brazil': ['brazil', 'brazilian culture'],
  'Argentina': ['argentina', 'argentine culture'],
  'South Africa': ['south africa', 'african culture'],
  'Egypt': ['egypt', 'egyptian culture'],
}

export const getCountryPhoto = async (countryName) => {
  try {
    // Try Unsplash first
    const unsplashUrl = await getUnsplashPhoto(countryName)
    if (unsplashUrl) return unsplashUrl

    // Fallback to Pixabay
    const pixabayUrl = await getPixabayPhoto(countryName)
    if (pixabayUrl) return pixabayUrl

    // Final fallback to a generic travel photo
    return 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=600&fit=crop'
  } catch (error) {
    console.error('Error fetching country photo:', error)
    // Return a default travel image
    return 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=600&fit=crop'
  }
}

const getUnsplashPhoto = async (countryName) => {
  if (!UNSPLASH_ACCESS_KEY || UNSPLASH_ACCESS_KEY === 'your_unsplash_access_key') {
    return null
  }

  const searchTerms = COUNTRY_SEARCH_TERMS[countryName] || [countryName.toLowerCase()]
  const query = searchTerms[0]

  try {
    const response = await fetch(
      `${UNSPLASH_API_URL}/search/photos?query=${encodeURIComponent(query)}&per_page=1&orientation=landscape`,
      {
        headers: {
          'Authorization': `Client-ID ${UNSPLASH_ACCESS_KEY}`
        }
      }
    )

    if (!response.ok) return null

    const data = await response.json()
    if (data.results && data.results.length > 0) {
      return data.results[0].urls.regular
    }
  } catch (error) {
    console.error('Unsplash API error:', error)
  }

  return null
}

const getPixabayPhoto = async (countryName) => {
  if (!PIXABAY_API_KEY || PIXABAY_API_KEY === 'your_pixabay_api_key') {
    return null
  }

  const searchTerms = COUNTRY_SEARCH_TERMS[countryName] || [countryName.toLowerCase()]
  const query = searchTerms[0]

  try {
    const response = await fetch(
      `${PIXABAY_API_URL}/?key=${PIXABAY_API_KEY}&q=${encodeURIComponent(query)}&image_type=photo&orientation=horizontal&category=travel&per_page=3`
    )

    if (!response.ok) return null

    const data = await response.json()
    if (data.hits && data.hits.length > 0) {
      return data.hits[0].webformatURL
    }
  } catch (error) {
    console.error('Pixabay API error:', error)
  }

  return null
}

// For demo purposes, return some beautiful country images
export const getDemoCountryPhoto = (countryName) => {
  const demoPhotos = {
    'United States': 'https://images.unsplash.com/photo-1501594907352-04dda43d0b8c?w=800&h=600&fit=crop',
    'Canada': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop',
    'Mexico': 'https://images.unsplash.com/photo-1518105779142-d975f22f1d04?w=800&h=600&fit=crop',
    'United Kingdom': 'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800&h=600&fit=crop',
    'France': 'https://images.unsplash.com/photo-1502602898536-47ad22581b52?w=800&h=600&fit=crop',
    'Germany': 'https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=800&h=600&fit=crop',
    'Spain': 'https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=800&h=600&fit=crop',
    'Italy': 'https://images.unsplash.com/photo-1515542622106-78bda8ba0e5b?w=800&h=600&fit=crop',
    'Japan': 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&h=600&fit=crop',
    'China': 'https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=800&h=600&fit=crop',
    'South Korea': 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800&h=600&fit=crop',
    'India': 'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800&h=600&fit=crop',
    'Australia': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop',
    'New Zealand': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop',
    'Brazil': 'https://images.unsplash.com/photo-1483729558449-99ef09a8c325?w=800&h=600&fit=crop',
    'Argentina': 'https://images.unsplash.com/photo-1518105779142-d975f22f1d04?w=800&h=600&fit=crop',
    'South Africa': 'https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?w=800&h=600&fit=crop',
    'Egypt': 'https://images.unsplash.com/photo-1539650116574-75c0c6d73c6e?w=800&h=600&fit=crop',
  }

  return demoPhotos[countryName] || 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=600&fit=crop'
}
