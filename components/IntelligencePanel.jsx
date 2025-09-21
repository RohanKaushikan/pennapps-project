import { useState, useEffect } from 'react'
import { Brain, TrendingUp, Link, Lightbulb, Globe, Clock, AlertTriangle } from 'lucide-react'

const IntelligencePanel = ({ countryCode, className = "" }) => {
  const [intelligence, setIntelligence] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('patterns')

  useEffect(() => {
    if (countryCode) {
      fetchIntelligence()
    }
  }, [countryCode])

  const fetchIntelligence = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Fetch comprehensive pattern analysis and predictive insights
      const [patternResponse, predictiveResponse] = await Promise.all([
        fetch(`http://localhost:8000/api/intelligence/pattern-analysis/${countryCode}`),
        fetch(`http://localhost:8000/api/predictions/country/${countryCode}`)
      ])
      
      if (!patternResponse.ok) {
        throw new Error(`Failed to fetch pattern analysis: ${patternResponse.status}`)
      }
      
      const patternData = await patternResponse.json()
      let predictiveData = null
      
      if (predictiveResponse.ok) {
        predictiveData = await predictiveResponse.json()
      }
      
      setIntelligence({
        ...patternData,
        predictive_insights: predictiveData
      })
    } catch (err) {
      console.error('Error fetching intelligence:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getTrendIcon = (direction) => {
    switch (direction) {
      case 'increasing': return <TrendingUp size={16} className="text-red-500" />
      case 'decreasing': return <TrendingUp size={16} className="text-green-500 rotate-180" />
      default: return <TrendingUp size={16} className="text-gray-500" />
    }
  }

  const getRelationshipIcon = (type) => {
    switch (type) {
      case 'dependency': return <Link size={16} className="text-blue-500" />
      case 'conflict': return <AlertTriangle size={16} className="text-red-500" />
      case 'similar': return <Link size={16} className="text-green-500" />
      default: return <Link size={16} className="text-gray-500" />
    }
  }

  if (loading) {
    return (
      <div className={`intelligence-panel ${className}`}>
        <div className="loading-state">
          <Brain size={20} className="animate-spin" />
          <span>Analyzing patterns...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`intelligence-panel ${className}`}>
        <div className="error-state">
          <AlertTriangle size={20} />
          <span>Failed to load intelligence: {error}</span>
        </div>
      </div>
    )
  }

  if (!intelligence) {
    return null
  }

  return (
    <div className={`intelligence-panel ${className}`}>
      <style jsx>{`
        .intelligence-panel {
          background: white;
          border-radius: 16px;
          border: 1px solid #e5e7eb;
          overflow: hidden;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .panel-header {
          background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
          color: white;
          padding: 16px 20px;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .panel-tabs {
          display: flex;
          background: #f8fafc;
          border-bottom: 1px solid #e5e7eb;
        }

        .tab-button {
          flex: 1;
          padding: 12px 16px;
          background: none;
          border: none;
          cursor: pointer;
          font-size: 0.875rem;
          font-weight: 500;
          color: #6b7280;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
        }

        .tab-button.active {
          background: white;
          color: #374151;
          border-bottom: 2px solid #6366f1;
        }

        .tab-button:hover:not(.active) {
          background: #f1f5f9;
        }

        .tab-content {
          padding: 20px;
          max-height: 400px;
          overflow-y: auto;
        }

        .section {
          margin-bottom: 24px;
        }

        .section:last-child {
          margin-bottom: 0;
        }

        .section-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 12px;
        }

        .item {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 8px;
          transition: all 0.2s ease;
        }

        .item:hover {
          background: #f3f4f6;
          border-color: #d1d5db;
        }

        .item:last-child {
          margin-bottom: 0;
        }

        .item-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 6px;
        }

        .item-title {
          font-weight: 600;
          color: #1f2937;
          font-size: 0.875rem;
        }

        .confidence-badge {
          background: #dbeafe;
          color: #1e40af;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 500;
        }

        .item-description {
          color: #6b7280;
          font-size: 0.8rem;
          line-height: 1.4;
        }

        .countries-list {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 6px;
        }

        .country-tag {
          background: #e0e7ff;
          color: #3730a3;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.7rem;
          font-weight: 500;
        }

        .action-items {
          margin-top: 8px;
        }

        .action-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.75rem;
          color: #059669;
          margin-bottom: 4px;
        }

        .loading-state, .error-state {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 40px;
          color: #6b7280;
        }

        .error-state {
          color: #dc2626;
        }

        .empty-state {
          text-align: center;
          padding: 20px;
          color: #6b7280;
          font-size: 0.875rem;
        }
      `}</style>

      <div className="panel-header">
        <Brain size={20} />
        <span>Travel Intelligence</span>
      </div>

      <div className="panel-tabs">
        <button
          className={`tab-button ${activeTab === 'patterns' ? 'active' : ''}`}
          onClick={() => setActiveTab('patterns')}
        >
          <Globe size={14} />
          Patterns
        </button>
        <button
          className={`tab-button ${activeTab === 'trends' ? 'active' : ''}`}
          onClick={() => setActiveTab('trends')}
        >
          <TrendingUp size={14} />
          Trends
        </button>
        <button
          className={`tab-button ${activeTab === 'relationships' ? 'active' : ''}`}
          onClick={() => setActiveTab('relationships')}
        >
          <Link size={14} />
          Links
        </button>
        <button
          className={`tab-button ${activeTab === 'recommendations' ? 'active' : ''}`}
          onClick={() => setActiveTab('recommendations')}
        >
          <Lightbulb size={14} />
          Tips
        </button>
        <button
          className={`tab-button ${activeTab === 'predictive' ? 'active' : ''}`}
          onClick={() => setActiveTab('predictive')}
        >
          <Clock size={14} />
          Predictions
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'patterns' && (
          <div className="section">
            <div className="section-title">
              <Globe size={16} />
              Cross-Country Patterns
            </div>
            {intelligence.cross_country_patterns.length > 0 ? (
              intelligence.cross_country_patterns.slice(0, 5).map((pattern, index) => (
                <div key={index} className="item">
                  <div className="item-header">
                    <div className="item-title">{pattern.pattern_type}</div>
                    <div className="confidence-badge">{Math.round(pattern.confidence * 100)}%</div>
                  </div>
                  <div className="item-description">{pattern.requirement_text}</div>
                  <div className="countries-list">
                    {pattern.countries.map(country => (
                      <span key={country} className="country-tag">{country}</span>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">No cross-country patterns found</div>
            )}
          </div>
        )}

        {activeTab === 'trends' && (
          <div className="section">
            <div className="section-title">
              <TrendingUp size={16} />
              Historical Trends
            </div>
            {intelligence.historical_trends.length > 0 ? (
              intelligence.historical_trends.map((trend, index) => (
                <div key={index} className="item">
                  <div className="item-header">
                    <div className="item-title">{trend.requirement_type}</div>
                    {getTrendIcon(trend.trend_direction)}
                  </div>
                  <div className="item-description">
                    {trend.trend_direction} trend ({trend.change_frequency} changes)
                    {trend.seasonal_pattern && ` • Seasonal: ${trend.seasonal_pattern}`}
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">No historical trends available</div>
            )}
          </div>
        )}

        {activeTab === 'relationships' && (
          <div className="section">
            <div className="section-title">
              <Link size={16} />
              Alert Relationships
            </div>
            {intelligence.alert_relationships.length > 0 ? (
              intelligence.alert_relationships.slice(0, 5).map((rel, index) => (
                <div key={index} className="item">
                  <div className="item-header">
                    <div className="item-title">{rel.relationship_type}</div>
                    <div className="confidence-badge">{Math.round(rel.confidence * 100)}%</div>
                  </div>
                  <div className="item-description">{rel.description}</div>
                </div>
              ))
            ) : (
              <div className="empty-state">No alert relationships found</div>
            )}
          </div>
        )}

        {activeTab === 'recommendations' && (
          <div className="section">
            <div className="section-title">
              <Lightbulb size={16} />
              Smart Recommendations
            </div>
            {intelligence.smart_recommendations.length > 0 ? (
              intelligence.smart_recommendations.slice(0, 5).map((rec, index) => (
                <div key={index} className="item">
                  <div className="item-header">
                    <div className="item-title">{rec.title}</div>
                    <div className="confidence-badge">{Math.round(rec.confidence * 100)}%</div>
                  </div>
                  <div className="item-description">{rec.description}</div>
                  {rec.action_items.length > 0 && (
                    <div className="action-items">
                      {rec.action_items.map((action, actionIndex) => (
                        <div key={actionIndex} className="action-item">
                          <Clock size={12} />
                          {action}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="empty-state">No recommendations available</div>
            )}
          </div>
        )}

        {activeTab === 'predictive' && (
          <div className="section">
            <div className="section-title">
              <Clock size={16} />
              Predictive Insights
            </div>
            {intelligence.predictive_insights ? (
              <div className="item">
                <div className="item-header">
                  <div className="item-title">Country Risk Assessment</div>
                  <div className="confidence-badge">
                    {intelligence.predictive_insights.risk_level.toUpperCase()}
                  </div>
                </div>
                <div className="item-description">
                  Average violation probability: {Math.round(intelligence.predictive_insights.violation_probability_avg * 100)}%
                </div>
                
                {intelligence.predictive_insights.top_concerns.length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#6b7280', marginBottom: '4px' }}>
                      TOP CONCERNS
                    </div>
                    <div className="countries-list">
                      {intelligence.predictive_insights.top_concerns.map((concern, index) => (
                        <span key={index} className="country-tag">{concern}</span>
                      ))}
                    </div>
                  </div>
                )}

                {intelligence.predictive_insights.upcoming_deadlines.length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#6b7280', marginBottom: '4px' }}>
                      UPCOMING DEADLINES
                    </div>
                    {intelligence.predictive_insights.upcoming_deadlines.map((deadline, index) => (
                      <div key={index} className="action-item">
                        <Clock size={12} />
                        {deadline}
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ marginTop: '8px', fontSize: '0.8rem', color: '#059669' }}>
                  💡 Suggested preparation time: {intelligence.predictive_insights.suggested_preparation_days} days
                </div>
              </div>
            ) : (
              <div className="empty-state">No predictive insights available</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default IntelligencePanel
