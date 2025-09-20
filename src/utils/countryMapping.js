// Country mapping utilities
export const getCountryFromCoordinates = (latitude, longitude) => {
  // This is a simplified mapping - in production, you'd use a proper geocoding service
  // or a comprehensive country boundary database
  
  const countryMappings = [
    // North America
    { name: 'United States', flag: '🇺🇸', bounds: { north: 49, south: 25, east: -66, west: -125 } },
    { name: 'Canada', flag: '🇨🇦', bounds: { north: 84, south: 41, east: -52, west: -141 } },
    { name: 'Mexico', flag: '🇲🇽', bounds: { north: 32, south: 14, east: -86, west: -118 } },
    
    // Europe
    { name: 'United Kingdom', flag: '🇬🇧', bounds: { north: 61, south: 50, east: 2, west: -8 } },
    { name: 'France', flag: '🇫🇷', bounds: { north: 51, south: 42, east: 8, west: -5 } },
    { name: 'Germany', flag: '🇩🇪', bounds: { north: 55, south: 47, east: 15, west: 6 } },
    { name: 'Spain', flag: '🇪🇸', bounds: { north: 44, south: 36, east: 4, west: -9 } },
    { name: 'Italy', flag: '🇮🇹', bounds: { north: 47, south: 36, east: 19, west: 7 } },
    
    // Asia
    { name: 'Japan', flag: '🇯🇵', bounds: { north: 46, south: 24, east: 146, west: 123 } },
    { name: 'China', flag: '🇨🇳', bounds: { north: 54, south: 18, east: 135, west: 73 } },
    { name: 'South Korea', flag: '🇰🇷', bounds: { north: 39, south: 33, east: 132, west: 125 } },
    { name: 'India', flag: '🇮🇳', bounds: { north: 37, south: 6, east: 97, west: 68 } },
    
    // Oceania
    { name: 'Australia', flag: '🇦🇺', bounds: { north: -10, south: -44, east: 154, west: 113 } },
    { name: 'New Zealand', flag: '🇳🇿', bounds: { north: -34, south: -48, east: 179, west: 166 } },
    
    // South America
    { name: 'Brazil', flag: '🇧🇷', bounds: { north: 5, south: -34, east: -34, west: -74 } },
    { name: 'Argentina', flag: '🇦🇷', bounds: { north: -22, south: -55, east: -53, west: -74 } },
    
    // Africa
    { name: 'South Africa', flag: '🇿🇦', bounds: { north: -22, south: -35, east: 33, west: 16 } },
    { name: 'Egypt', flag: '🇪🇬', bounds: { north: 32, south: 22, east: 36, west: 25 } },
  ]

  for (const country of countryMappings) {
    const { bounds } = country
    if (
      latitude >= bounds.south &&
      latitude <= bounds.north &&
      longitude >= bounds.west &&
      longitude <= bounds.east
    ) {
      return country
    }
  }

  // Default fallback
  return { name: 'Unknown', flag: '🌍', bounds: null }
}

export const getCountryCoordinates = (countryName) => {
  // Approximate center coordinates for major countries
  const countryCenters = {
    'United States': { latitude: 39.8283, longitude: -98.5795 },
    'Canada': { latitude: 56.1304, longitude: -106.3468 },
    'Mexico': { latitude: 23.6345, longitude: -102.5528 },
    'United Kingdom': { latitude: 55.3781, longitude: -3.4360 },
    'France': { latitude: 46.2276, longitude: 2.2137 },
    'Germany': { latitude: 51.1657, longitude: 10.4515 },
    'Spain': { latitude: 40.4637, longitude: -3.7492 },
    'Italy': { latitude: 41.8719, longitude: 12.5674 },
    'Japan': { latitude: 36.2048, longitude: 138.2529 },
    'China': { latitude: 35.8617, longitude: 104.1954 },
    'South Korea': { latitude: 35.9078, longitude: 127.7669 },
    'India': { latitude: 20.5937, longitude: 78.9629 },
    'Australia': { latitude: -25.2744, longitude: 133.7751 },
    'New Zealand': { latitude: -40.9006, longitude: 174.8860 },
    'Brazil': { latitude: -14.2350, longitude: -51.9253 },
    'Argentina': { latitude: -38.4161, longitude: -63.6167 },
    'South Africa': { latitude: -30.5595, longitude: 22.9375 },
    'Egypt': { latitude: 26.0975, longitude: 30.0444 },
  }

  return countryCenters[countryName] || { latitude: 0, longitude: 0 }
}
