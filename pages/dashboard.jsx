import { useState, useEffect } from 'react'
import { Bell, AlertTriangle, Globe, User, Settings, Search, Filter, RefreshCw } from 'lucide-react'

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('alerts')
  const [alerts, setAlerts] = useState([])
  const [countries, setCountries] = useState([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    search: '',
    country: '',
    riskLevel: '',
    category: '',
    unreadOnly: false
  })
  const [stats, setStats] = useState({ total: 0, unread: 0, countries: 0 })

  // Fetch alerts
  const fetchAlerts = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: '1',
        per_page: '20',
        sort_by: 'created_at',
        sort_order: 'desc'
      })

      if (filters.search) params.append('search', filters.search)
      if (filters.country) params.append('country_codes', filters.country)
      if (filters.riskLevel) params.append('risk_level', filters.riskLevel)
      if (filters.category) params.append('categories', filters.category)

      const response = await fetch(`http://localhost:8000/api/v1/alerts/?${params}`)
      if (response.ok) {
        const data = await response.json()
        setAlerts(data.alerts || [])
        setStats({
          total: data.total_count || 0,
          unread: data.alerts?.filter(a => !a.user_status?.is_read).length || 0,
          countries: new Set(data.alerts?.map(a => a.country?.code)).size || 0
        })
      }
    } catch (error) {
      console.error('Error fetching alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  // Fetch countries
  const fetchCountries = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/countries/')
      if (response.ok) {
        const data = await response.json()
        setCountries(data || [])
      }
    } catch (error) {
      console.error('Error fetching countries:', error)
    }
  }

  useEffect(() => {
    fetchAlerts()
    fetchCountries()
  }, [filters])

  const markAlertRead = async (alertId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/alerts/${alertId}/mark-read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 1, action: 'mark_read' })
      })
      if (response.ok) {
        fetchAlerts() // Refresh alerts
      }
    } catch (error) {
      console.error('Error marking alert as read:', error)
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

  return (
    <div style={{ backgroundColor: '#f8fafc', minHeight: '100vh' }}>
      <style>{`
        .header {
          background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
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
        .stats {
          display: flex;
          gap: 20px;
        }
        .stat-item {
          text-align: center;
        }
        .stat-number {
          font-size: 20px;
          font-weight: bold;
        }
        .stat-label {
          font-size: 12px;
          opacity: 0.8;
        }
        .nav-tabs {
          background: white;
          border-bottom: 1px solid #e5e7eb;
          padding: 0 20px;
        }
        .nav-content {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          gap: 0;
        }
        .nav-tab {
          padding: 16px 24px;
          background: none;
          border: none;
          cursor: pointer;
          font-weight: 500;
          color: #6b7280;
          border-bottom: 2px solid transparent;
          transition: all 0.2s;
        }
        .nav-tab.active {
          color: #1e40af;
          border-bottom-color: #1e40af;
        }
        .nav-tab:hover {
          color: #1e40af;
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
        .filter-input:focus, .filter-select:focus {
          outline: none;
          border-color: #3b82f6;
        }
        .filter-checkbox {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 8px;
        }
        .alert-card {
          background: white;
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          border-left: 4px solid #e5e7eb;
        }
        .alert-card.unread {
          border-left-color: #3b82f6;
        }
        .alert-header {
          display: flex;
          justify-content: between;
          align-items: flex-start;
          margin-bottom: 12px;
        }
        .alert-title {
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 4px 0;
          flex: 1;
        }
        .alert-meta {
          display: flex;
          gap: 12px;
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
          line-height: 1.5;
          margin-bottom: 12px;
        }
        .alert-categories {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
          flex-wrap: wrap;
        }
        .category-tag {
          background: #f3f4f6;
          color: #374151;
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 12px;
        }
        .alert-actions {
          display: flex;
          gap: 8px;
        }
        .btn {
          padding: 8px 16px;
          border-radius: 8px;
          border: none;
          cursor: pointer;
          font-size: 14px;
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
        .btn-secondary {
          background: #f3f4f6;
          color: #374151;
        }
        .btn-secondary:hover {
          background: #e5e7eb;
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
          .header-content {
            flex-direction: column;
            gap: 16px;
            text-align: center;
          }
          .stats {
            justify-content: center;
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
          <div>
            <h1>Travel Alert Dashboard</h1>
            <p>Stay informed about travel advisories worldwide</p>
          </div>
          <div className="stats">
            <div className="stat-item">
              <div className="stat-number">{stats.total}</div>
              <div className="stat-label">Total Alerts</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">{stats.unread}</div>
              <div className="stat-label">Unread</div>
            </div>
            <div className="stat-item">
              <div className="stat-number">{stats.countries}</div>
              <div className="stat-label">Countries</div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="nav-tabs">
        <div className="nav-content">
          <button 
            className={`nav-tab ${activeTab === 'alerts' ? 'active' : ''}`}
            onClick={() => setActiveTab('alerts')}
          >
            <AlertTriangle size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
            Alerts
          </button>
          <button 
            className={`nav-tab ${activeTab === 'countries' ? 'active' : ''}`}
            onClick={() => setActiveTab('countries')}
          >
            <Globe size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
            Countries
          </button>
          <button 
            className={`nav-tab ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            <User size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
            Profile
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="content">
        {activeTab === 'alerts' && (
          <>
            {/* Filters */}
            <div className="filters">
              <div className="filter-row">
                <div className="filter-group">
                  <label className="filter-label">Search</label>
                  <input
                    type="text"
                    className="filter-input"
                    placeholder="Search alerts..."
                    value={filters.search}
                    onChange={(e) => setFilters({...filters, search: e.target.value})}
                  />
                </div>
                <div className="filter-group">
                  <label className="filter-label">Country</label>
                  <select
                    className="filter-select"
                    value={filters.country}
                    onChange={(e) => setFilters({...filters, country: e.target.value})}
                  >
                    <option value="">All Countries</option>
                    {countries.map(country => (
                      <option key={country.code} value={country.code}>
                        {country.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="filter-group">
                  <label className="filter-label">Risk Level</label>
                  <select
                    className="filter-select"
                    value={filters.riskLevel}
                    onChange={(e) => setFilters({...filters, riskLevel: e.target.value})}
                  >
                    <option value="">All Levels</option>
                    <option value="1">Low (1)</option>
                    <option value="2">Moderate (2)</option>
                    <option value="3">High (3)</option>
                    <option value="4">Very High (4)</option>
                    <option value="5">Critical (5)</option>
                  </select>
                </div>
                <div className="filter-group">
                  <label className="filter-label">Category</label>
                  <select
                    className="filter-select"
                    value={filters.category}
                    onChange={(e) => setFilters({...filters, category: e.target.value})}
                  >
                    <option value="">All Categories</option>
                    <option value="visa">Visa</option>
                    <option value="health">Health</option>
                    <option value="safety">Safety</option>
                    <option value="legal">Legal</option>
                    <option value="entry">Entry Requirements</option>
                  </select>
                </div>
              </div>
              <div className="filter-checkbox">
                <input
                  type="checkbox"
                  id="unreadOnly"
                  checked={filters.unreadOnly}
                  onChange={(e) => setFilters({...filters, unreadOnly: e.target.checked})}
                />
                <label htmlFor="unreadOnly">Show unread alerts only</label>
              </div>
            </div>

            {/* Alerts List */}
            {loading ? (
              <div className="loading">
                <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: '12px' }} />
                <div>Loading alerts...</div>
              </div>
            ) : alerts.length === 0 ? (
              <div className="empty-state">
                <AlertTriangle size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
                <h3>No alerts found</h3>
                <p>Try adjusting your filters or check back later for new advisories.</p>
              </div>
            ) : (
              alerts.map(alert => (
                <div key={alert.id} className={`alert-card ${!alert.user_status?.is_read ? 'unread' : ''}`}>
                  <div className="alert-header">
                    <h3 className="alert-title">{alert.title}</h3>
                    <span 
                      className="risk-badge"
                      style={{ backgroundColor: getRiskColor(alert.risk_level) }}
                    >
                      {getRiskLabel(alert.risk_level)}
                    </span>
                  </div>
                  <div className="alert-meta">
                    <span>📍 {alert.country?.name || 'Unknown Country'}</span>
                    <span>📅 {new Date(alert.created_at).toLocaleDateString()}</span>
                    <span>🔗 {alert.source?.name || 'Unknown Source'}</span>
                  </div>
                  <div className="alert-description">
                    {alert.description}
                  </div>
                  {alert.categories && alert.categories.length > 0 && (
                    <div className="alert-categories">
                      {alert.categories.map((category, idx) => (
                        <span key={idx} className="category-tag">{category}</span>
                      ))}
                    </div>
                  )}
                  <div className="alert-actions">
                    <button 
                      className="btn btn-primary"
                      onClick={() => window.location.href = `/alert/${alert.id}`}
                    >
                      View Details
                    </button>
                    {!alert.user_status?.is_read && (
                      <button 
                        className="btn btn-secondary"
                        onClick={() => markAlertRead(alert.id)}
                      >
                        Mark as Read
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </>
        )}

        {activeTab === 'countries' && (
          <div className="empty-state">
            <Globe size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
            <h3>Countries View</h3>
            <p>Country-specific alerts will be displayed here. Click on a country to see its travel advisories.</p>
            <button className="btn btn-primary" style={{ marginTop: '16px' }}>
              Browse by Country
            </button>
          </div>
        )}

        {activeTab === 'profile' && (
          <div className="empty-state">
            <User size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
            <h3>Profile Management</h3>
            <p>Manage your travel preferences and notification settings.</p>
            <button className="btn btn-primary" style={{ marginTop: '16px' }}>
              Edit Profile
            </button>
          </div>
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
