import { useState } from 'react'
import EnhancedAlertDisplay from '../components/EnhancedAlertDisplay'

export default function TestEnhanced() {
  const [selectedCountry, setSelectedCountry] = useState('NP')

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Enhanced Alerts Test Page</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <label>Select Country: </label>
        <select 
          value={selectedCountry} 
          onChange={(e) => setSelectedCountry(e.target.value)}
          style={{ padding: '8px', marginLeft: '8px' }}
        >
          <option value="NP">Nepal 🇳🇵</option>
          <option value="IT">Italy 🇮🇹</option>
          <option value="RU">Russia 🇷🇺</option>
        </select>
      </div>

      <EnhancedAlertDisplay countryCode={selectedCountry} />
    </div>
  )
}
