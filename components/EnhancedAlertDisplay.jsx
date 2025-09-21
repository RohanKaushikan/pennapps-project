import { useState, useEffect } from 'react'
import SmartAlertCard from './SmartAlertCard'
import SmartAlertSummary from './SmartAlertSummary'
import ComplianceChecklist from './ComplianceChecklist'
import IntelligencePanel from './IntelligencePanel'
import AlertCategorization from './AlertCategorization'

const EnhancedAlertDisplay = ({ countryCode, className = "" }) => {
  const [enhancedAlerts, setEnhancedAlerts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showIntelligencePanel, setShowIntelligencePanel] = useState(false)
  const [showComplianceChecklist, setShowComplianceChecklist] = useState(false)

  useEffect(() => {
    if (countryCode) {
      console.log('🔍 EnhancedAlertDisplay: Fetching alerts for', countryCode)
      fetchEnhancedAlerts()
    }
  }, [countryCode])

  const fetchEnhancedAlerts = async () => {
    setLoading(true)
    setError(null)

    try {
      console.log(`Fetching enhanced alerts for ${countryCode}...`)
      const response = await fetch(`http://localhost:8000/api/alerts/${countryCode}/enhanced`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch enhanced alerts: ${response.status}`)
      }
      
      const data = await response.json()
      console.log(`✅ Received ${data.length} enhanced alerts:`, data.slice(0, 2))
      console.log(`🧠 Alerts with intelligence: ${data.filter(a => a.intelligence).length}`)
      console.log(`🎯 Risk scores: ${data.map(a => a.intelligence?.risk_score).filter(Boolean).slice(0, 5)}`)
      console.log(`🔥 Critical alerts: ${data.filter(a => a.intelligence?.risk_score >= 70).length}`)
      console.log(`⚠️ Important alerts: ${data.filter(a => a.intelligence?.risk_score >= 40 && a.intelligence?.risk_score < 70).length}`)
      setEnhancedAlerts(data)
    } catch (err) {
      console.error('Error fetching enhanced alerts:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={`enhanced-alert-display ${className}`}>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div>Loading enhanced alerts with ML intelligence...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`enhanced-alert-display ${className}`}>
        <div style={{ textAlign: 'center', padding: '40px', color: '#dc2626' }}>
          <div>Error loading enhanced alerts: {error}</div>
          <button 
            onClick={fetchEnhancedAlerts}
            style={{ 
              marginTop: '16px', 
              padding: '8px 16px', 
              background: '#3b82f6', 
              color: 'white', 
              border: 'none', 
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (enhancedAlerts.length === 0) {
    return (
      <div className={`enhanced-alert-display ${className}`}>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div>No enhanced alerts available for {countryCode}</div>
          <div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '8px' }}>
            The ML system is still processing alerts in the background.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`enhanced-alert-display ${className}`}>
      <style jsx>{`
        .enhanced-alert-display {
          width: 100%;
        }

        .controls-section {
          margin-bottom: 20px;
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        .control-button {
          padding: 8px 16px;
          background: white;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.875rem;
          transition: all 0.2s ease;
        }

        .control-button:hover {
          background: #f9fafb;
          border-color: #9ca3af;
        }

        .control-button.active {
          background: #3b82f6;
          color: white;
          border-color: #3b82f6;
        }

        .debug-info {
          background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
          border: 2px solid #3b82f6;
          padding: 16px;
          border-radius: 12px;
          margin-bottom: 20px;
          font-size: 0.9rem;
          color: #1e40af;
          font-weight: 500;
          box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1);
        }
      `}</style>

      {/* Debug Info */}
      <div className="debug-info">
        <strong>🔍 Enhanced Alerts Debug:</strong> Found {enhancedAlerts.length} alerts for {countryCode}
        <br />
        <strong>🧠 With Intelligence:</strong> {enhancedAlerts.filter(a => a.intelligence).length} alerts have ML data
        <br />
        <strong>📊 Sample Risk Scores:</strong> {enhancedAlerts.slice(0, 3).map(a => a.intelligence?.risk_score || 'N/A').join(', ')}
        <br />
        <strong>🎯 Sample Categories:</strong> {enhancedAlerts.slice(0, 3).map(a => a.intelligence?.requirement_type || 'N/A').join(', ')}
        <br />
        <strong>⚡ Sample Urgency:</strong> {enhancedAlerts.slice(0, 3).map(a => a.intelligence?.urgency_level || 'N/A').join(', ')}
      </div>

      {/* Smart Alert Summary */}
      <SmartAlertSummary
        countryCode={countryCode}
        alerts={enhancedAlerts}
        className="intelligence-summary"
      />

      {/* Controls */}
      <div className="controls-section">
        <button
          className={`control-button ${showIntelligencePanel ? 'active' : ''}`}
          onClick={() => setShowIntelligencePanel(!showIntelligencePanel)}
        >
          🧠 Intelligence Panel {showIntelligencePanel ? '−' : '+'}
        </button>
        <button
          className={`control-button ${showComplianceChecklist ? 'active' : ''}`}
          onClick={() => setShowComplianceChecklist(!showComplianceChecklist)}
        >
          ✅ Compliance Checklist {showComplianceChecklist ? '−' : '+'}
        </button>
      </div>

      {/* Intelligence Panel */}
      {showIntelligencePanel && (
        <IntelligencePanel
          countryCode={countryCode}
          className="pattern-analysis-panel"
        />
      )}

      {/* Compliance Checklist */}
      {showComplianceChecklist && (
        <ComplianceChecklist
          countryCode={countryCode}
          alerts={enhancedAlerts}
          className="compliance-panel"
        />
      )}

      {/* Alert Categorization */}
      <AlertCategorization
        alerts={enhancedAlerts}
        className="enhanced-categorization"
      />
    </div>
  )
}

export default EnhancedAlertDisplay
