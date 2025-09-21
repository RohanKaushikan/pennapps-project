import { useState, useEffect } from 'react'
import { AlertTriangle, Clock, Info, Shield, Filter } from 'lucide-react'
import SmartAlertCard from './SmartAlertCard'

const AlertCategorization = ({ alerts = [], className = "" }) => {
  const [categorizedAlerts, setCategorizedAlerts] = useState({
    critical: [],
    important: [],
    general: []
  })
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    categorizeAlerts()
  }, [alerts])

  const categorizeAlerts = () => {
    if (!alerts.length) return

    setLoading(true)
    const categorized = {
      critical: [],
      important: [],
      general: []
    }

    alerts.forEach(alert => {
      // Use the intelligence data that's already in the alert object
      const intelligence = alert.intelligence

      // Categorize based on intelligence or fallback to simple heuristics
      if (intelligence) {
        if (intelligence.requirement_type === 'critical' || intelligence.risk_score >= 70) {
          categorized.critical.push(alert)
        } else if (intelligence.requirement_type === 'important' || intelligence.risk_score >= 40) {
          categorized.important.push(alert)
        } else {
          categorized.general.push(alert)
        }
      } else {
        // Fallback categorization based on keywords
        const title = alert.title.toLowerCase()
        if (title.includes('urgent') || title.includes('mandatory') || title.includes('required')) {
          categorized.critical.push(alert)
        } else if (title.includes('important') || title.includes('recommended')) {
          categorized.important.push(alert)
        } else {
          categorized.general.push(alert)
        }
      }
    })

    // Sort within each category by timestamp (newest first)
    Object.keys(categorized).forEach(key => {
      categorized[key].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    })

    setCategorizedAlerts(categorized)
    setLoading(false)
  }

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'critical': return <AlertTriangle size={16} className="text-red-600" />
      case 'important': return <Shield size={16} className="text-orange-500" />
      default: return <Info size={16} className="text-blue-500" />
    }
  }

  const getCategoryStats = (category) => {
    const alerts = categorizedAlerts[category]
    const urgentCount = alerts.filter(alert =>
      alert.intelligence?.urgency_level === 'immediate' ||
      alert.intelligence?.urgency_level === 'urgent'
    ).length

    return { total: alerts.length, urgent: urgentCount }
  }

  const getVisibleAlerts = () => {
    if (selectedCategory === 'all') {
      return [
        ...categorizedAlerts.critical,
        ...categorizedAlerts.important,
        ...categorizedAlerts.general
      ]
    }
    return categorizedAlerts[selectedCategory] || []
  }

  return (
    <div className={`alert-categorization ${className}`}>
      <style jsx>{`
        .alert-categorization {
          width: 100%;
        }

        .category-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          padding: 0 4px;
        }

        .category-title {
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .category-filters {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .filter-button {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 6px 12px;
          background: white;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .filter-button:hover {
          background: #f9fafb;
          border-color: #9ca3af;
        }

        .filter-button.active {
          background: #3b82f6;
          color: white;
          border-color: #3b82f6;
        }

        .category-section {
          margin-bottom: 32px;
        }

        .section-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          background: #f9fafb;
          border-radius: 8px;
          margin-bottom: 12px;
          border-left: 4px solid;
        }

        .section-header.critical {
          border-left-color: #dc2626;
          background: #fef2f2;
        }

        .section-header.important {
          border-left-color: #f59e0b;
          background: #fffbeb;
        }

        .section-header.general {
          border-left-color: #3b82f6;
          background: #eff6ff;
        }

        .section-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          font-size: 1rem;
        }

        .section-stats {
          display: flex;
          gap: 12px;
          font-size: 0.875rem;
        }

        .stat-item {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 2px 8px;
          background: white;
          border-radius: 4px;
          border: 1px solid #e5e7eb;
        }

        .urgent-indicator {
          color: #dc2626;
        }

        .alerts-grid {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .loading-state {
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 40px;
          color: #6b7280;
        }

        .empty-state {
          text-align: center;
          padding: 40px;
          color: #6b7280;
        }

        .time-sensitive-banner {
          background: linear-gradient(90deg, #fbbf24, #f59e0b);
          color: white;
          padding: 8px 16px;
          border-radius: 6px;
          margin-bottom: 16px;
          font-size: 0.875rem;
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        @media (max-width: 768px) {
          .category-header {
            flex-direction: column;
            gap: 12px;
            align-items: flex-start;
          }

          .category-filters {
            width: 100%;
          }

          .section-header {
            flex-direction: column;
            gap: 8px;
            align-items: flex-start;
          }

          .section-stats {
            flex-direction: column;
            gap: 4px;
          }
        }
      `}</style>

      <div className="category-header">
        <div className="category-title">
          <Filter size={20} />
          Travel Alert Categories
        </div>
        <div className="category-filters">
          <button
            className={`filter-button ${selectedCategory === 'all' ? 'active' : ''}`}
            onClick={() => setSelectedCategory('all')}
          >
            All Alerts ({alerts.length})
          </button>
          <button
            className={`filter-button ${selectedCategory === 'critical' ? 'active' : ''}`}
            onClick={() => setSelectedCategory('critical')}
          >
            {getCategoryIcon('critical')}
            Critical ({getCategoryStats('critical').total})
          </button>
          <button
            className={`filter-button ${selectedCategory === 'important' ? 'active' : ''}`}
            onClick={() => setSelectedCategory('important')}
          >
            {getCategoryIcon('important')}
            Important ({getCategoryStats('important').total})
          </button>
          <button
            className={`filter-button ${selectedCategory === 'general' ? 'active' : ''}`}
            onClick={() => setSelectedCategory('general')}
          >
            {getCategoryIcon('general')}
            General ({getCategoryStats('general').total})
          </button>
        </div>
      </div>

      {/* Time-sensitive alerts banner */}
      {(getCategoryStats('critical').urgent > 0 || getCategoryStats('important').urgent > 0) && (
        <div className="time-sensitive-banner">
          <Clock size={16} />
          {getCategoryStats('critical').urgent + getCategoryStats('important').urgent} time-sensitive alerts require immediate attention
        </div>
      )}

      {loading ? (
        <div className="loading-state">
          <div>Categorizing alerts with ML intelligence...</div>
        </div>
      ) : selectedCategory === 'all' ? (
        // Show all categories
        <>
          {categorizedAlerts.critical.length > 0 && (
            <div className="category-section">
              <div className="section-header critical">
                <div className="section-title">
                  {getCategoryIcon('critical')}
                  Critical Legal Requirements
                </div>
                <div className="section-stats">
                  <div className="stat-item">
                    Total: {getCategoryStats('critical').total}
                  </div>
                  {getCategoryStats('critical').urgent > 0 && (
                    <div className="stat-item urgent-indicator">
                      <Clock size={12} />
                      {getCategoryStats('critical').urgent} urgent
                    </div>
                  )}
                </div>
              </div>
              <div className="alerts-grid">
                {categorizedAlerts.critical.map(alert => (
                  <SmartAlertCard
                    key={alert.id}
                    alert={alert}
                    intelligence={alert.intelligence}
                  />
                ))}
              </div>
            </div>
          )}

          {categorizedAlerts.important.length > 0 && (
            <div className="category-section">
              <div className="section-header important">
                <div className="section-title">
                  {getCategoryIcon('important')}
                  Important Updates
                </div>
                <div className="section-stats">
                  <div className="stat-item">
                    Total: {getCategoryStats('important').total}
                  </div>
                  {getCategoryStats('important').urgent > 0 && (
                    <div className="stat-item urgent-indicator">
                      <Clock size={12} />
                      {getCategoryStats('important').urgent} urgent
                    </div>
                  )}
                </div>
              </div>
              <div className="alerts-grid">
                {categorizedAlerts.important.map(alert => (
                  <SmartAlertCard
                    key={alert.id}
                    alert={alert}
                    intelligence={alert.intelligence}
                  />
                ))}
              </div>
            </div>
          )}

          {categorizedAlerts.general.length > 0 && (
            <div className="category-section">
              <div className="section-header general">
                <div className="section-title">
                  {getCategoryIcon('general')}
                  General Information
                </div>
                <div className="section-stats">
                  <div className="stat-item">
                    Total: {getCategoryStats('general').total}
                  </div>
                </div>
              </div>
              <div className="alerts-grid">
                {categorizedAlerts.general.map(alert => (
                  <SmartAlertCard
                    key={alert.id}
                    alert={alert}
                    intelligence={alert.intelligence}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        // Show selected category only
        <div className="alerts-grid">
          {getVisibleAlerts().length > 0 ? (
            getVisibleAlerts().map(alert => (
              <SmartAlertCard
                key={alert.id}
                alert={alert}
                intelligence={alert.intelligence}
              />
            ))
          ) : (
            <div className="empty-state">
              No alerts in this category
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default AlertCategorization