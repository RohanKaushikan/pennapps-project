import { useState, useEffect } from 'react'
import { Globe, AlertTriangle, ArrowLeft, Search, Filter, RefreshCw } from 'lucide-react'

export default function CountriesPage() {
  const [countries, setCountries] = useState([])
  const [alerts, setAlerts] = useState({})
  const [selectedCountry, setSelectedCountry] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterRegion, setFilterRegion] = useState('')

  useEffect(() => {
    fetchCountries()
  }, [])

  const fetchCountries = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/countries/')
      if (response.ok) {
        const data = await response.json()
        setCountries(data || [])
      }
    } catch (error) {
      console.error('Error fetching countries:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchCountryAlerts = async (countryCode) => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/alerts/country/${countryCode}`)
      if (response.ok) {
        const data = await response.json()
        setAlerts(prev => ({ ...prev, [countryCode]: data.alerts || [] }))
      }
    } catch (error) {
      console.error('Error fetching country alerts:', error)
    }
  }

  const handleCountrySelect = (country) => {
    setSelectedCountry(country)
    if (!alerts[country.code]) {
      fetchCountryAlerts(country.code)
    }
  }

  const getRiskColor = (level) => {
    const colors = {
      1: '#10b981', // green
      2: '#f59e0b', // yellow
      3: '#f97316', // orange
      4: '#ef4444', // red
      5: '#dc2626'  // dark red
    }
    return colors[level] || '#6b7280'
  }

  const getRiskLabel = (level) => {
    const labels = {
      1: 'Low',
      2: 'Moderate',
      3: 'High',
      4: 'Very High',
      5: 'Critical'
    }
    return labels[level] || 'Unknown'
  }

  const filteredCountries = countries.filter(country => {
    const matchesSearch = country.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         country.code.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesRegion = !filterRegion || country.region === filterRegion
    return matchesSearch && matchesRegion
  })

  const regions = [...new Set(countries.map(c => c.region).filter(Boolean))]

  return (
    <div style={{ backgroundColor: '#f8fafc', minHeight: '100vh' }}>
      <style>{`
        .header {
          background: linear-gradient(135deg, #059669 0%, #10b981 100%);
          color: white;
          padding: 20px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .header-content {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .header h1 {
          font-size: 24px;
          font-weight: bold;
          margin: 0;
        }
        .back-btn {
          background: rgba(255, 255, 255, 0.2);
          border: none;
          color: white;
          padding: 8px 12px;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 8px;
          transition: background 0.2s;
        }
        .back-btn:hover {
          background: rgba(255, 255, 255, 0.3);
        }
        .content {
          max-width: 1200px;
          margin: 0 auto;
          padding: 20px;
        }
        .filters {
          background: white;
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .filter-row {
          display: flex;
          gap: 16px;
          align-items: end;
          flex-wrap: wrap;
        }
        .filter-group {
          flex: 1;
          min-width: 200px;
        }
        .filter-label {
          display: block;
          font-weight: 500;
          color: #374151;
          margin-bottom: 8px;
          font-size: 14px;
        }
        .filter-input, .filter-select {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          font-size: 14px;
        }
        .countries-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px;
          margin-bottom: 20px;
        }
        .country-card {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          cursor: pointer;
          transition: all 0.2s;
          border: 2px solid transparent;
        }
        .country-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .country-card.selected {
          border-color: #10b981;
          background: #f0fdf4;
        }
        .country-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }
        .country-name {
          font-size: 18px;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
        }
        .country-code {
          background: #f3f4f6;
          color: #6b7280;
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 500;
        }
        .country-region {
          color: #6b7280;
          font-size: 14px;
          margin-bottom: 12px;
        }
        .alert-summary {
          display: flex;
          gap: 8px;
          align-items: center;
          font-size: 14px;
          color: #4b5563;
        }
        .alert-count {
          background: #dbeafe;
          color: #1e40af;
          padding: 4px 8px;
          border-radius: 6px;
          font-weight: 500;
        }
        .alerts-panel {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .alerts-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          padding-bottom: 16px;
          border-bottom: 1px solid #e5e7eb;
        }
        .alerts-title {
          font-size: 20px;
          font-weight: 600;
          color: #1f2937;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .alert-item {
          background: #f8fafc;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 12px;
          border-left: 4px solid #e5e7eb;
        }
        .alert-item.high-risk {
          border-left-color: #ef4444;
        }
        .alert-item.medium-risk {
          border-left-color: #f59e0b;
        }
        .alert-item.low-risk {
          border-left-color: #10b981;
        }
        .alert-title {
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 8px 0;
        }
        .alert-meta {
          display: flex;
          gap: 16px;
          align-items: center;
          font-size: 12px;
          color: #6b7280;
          margin-bottom: 8px;
        }
        .risk-badge {
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 600;
          color: white;
        }
        .alert-description {
          color: #4b5563;
          font-size: 14px;
          line-height: 1.4;
          margin-bottom: 12px;
        }
        .alert-actions {
          display: flex;
          gap: 8px;
        }
        .btn {
          padding: 6px 12px;
          border-radius: 6px;
          border: none;
          cursor: pointer;
          font-size: 12px;
          font-weight: 500;
          transition: all 0.2s;
        }
        .btn-primary {
          background: #3b82f6;
          color: white;
        }
        .btn-primary:hover {
          background: #2563eb;
        }
        .loading {
          text-align: center;
          padding: 40px;
          color: #6b7280;
        }
        .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: #6b7280;
        }
        .empty-state h3 {
          color: #374151;
          margin-bottom: 8px;
        }
        @media (max-width: 768px) {
          .countries-grid {
            grid-template-columns: 1fr;
          }
          .filter-row {
            flex-direction: column;
          }
          .filter-group {
            min-width: auto;
          }
        }
      `}</style>

      {/* Header */}
      <div className="header">
        <div className="header-content">
          <button className="back-btn" onClick={() => window.location.href = '/dashboard'}>
            <ArrowLeft size={16} />
            Back to Dashboard
          </button>
          <h1>Browse by Country</h1>
        </div>
      </div>

      {/* Content */}
      <div className="content">
        {/* Filters */}
        <div className="filters">
          <div className="filter-row">
            <div className="filter-group">
              <label className="filter-label">
                <Search size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                Search Countries
              </label>
              <input
                type="text"
                className="filter-input"
                placeholder="Search by country name or code..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="filter-group">
              <label className="filter-label">
                <Filter size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                Region
              </label>
              <select
                className="filter-select"
                value={filterRegion}
                onChange={(e) => setFilterRegion(e.target.value)}
              >
                <option value="">All Regions</option>
                {regions.map(region => (
                  <option key={region} value={region}>{region}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Countries Grid */}
        {loading ? (
          <div className="loading">
            <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '12px' }} />
            <div>Loading countries...</div>
          </div>
        ) : (
          <>
            <div className="countries-grid">
              {filteredCountries.map(country => (
                <div 
                  key={country.code}
                  className={`country-card ${selectedCountry?.code === country.code ? 'selected' : ''}`}
                  onClick={() => handleCountrySelect(country)}
                >
                  <div className="country-header">
                    <h3 className="country-name">{country.name}</h3>
                    <span className="country-code">{country.code}</span>
                  </div>
                  {country.region && (
                    <div className="country-region">📍 {country.region}</div>
                  )}
                  <div className="alert-summary">
                    <AlertTriangle size={16} />
                    <span className="alert-count">
                      {alerts[country.code]?.length || 0} alerts
                    </span>
                    <span>• Click to view details</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Selected Country Alerts */}
            {selectedCountry && (
              <div className="alerts-panel">
                <div className="alerts-header">
                  <h2 className="alerts-title">
                    <Globe size={20} />
                    Travel Advisories for {selectedCountry.name}
                  </h2>
                  <span className="country-code">{selectedCountry.code}</span>
                </div>

                {alerts[selectedCountry.code]?.length === 0 ? (
                  <div className="empty-state">
                    <AlertTriangle size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
                    <h3>No alerts available</h3>
                    <p>There are currently no travel advisories for {selectedCountry.name}.</p>
                  </div>
                ) : (
                  alerts[selectedCountry.code]?.map(alert => (
                    <div 
                      key={alert.id} 
                      className={`alert-item ${
                        alert.risk_level >= 4 ? 'high-risk' : 
                        alert.risk_level >= 3 ? 'medium-risk' : 'low-risk'
                      }`}
                    >
                      <h4 className="alert-title">{alert.title}</h4>
                      <div className="alert-meta">
                        <span>📅 {new Date(alert.created_at).toLocaleDateString()}</span>
                        <span 
                          className="risk-badge"
                          style={{ backgroundColor: getRiskColor(alert.risk_level) }}
                        >
                          {getRiskLabel(alert.risk_level)}
                        </span>
                        <span>🔗 {alert.source?.name}</span>
                      </div>
                      <div className="alert-description">
                        {alert.description}
                      </div>
                      <div className="alert-actions">
                        <button 
                          className="btn btn-primary"
                          onClick={() => window.location.href = `/alert/${alert.id}`}
                        >
                          View Details
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
