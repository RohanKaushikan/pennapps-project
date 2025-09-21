import { useState, useEffect } from 'react'
import { AlertTriangle, Clock, Shield, Phone, ExternalLink, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

const SmartAlertSummary = ({ countryCode, alerts = [], className = "" }) => {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (countryCode && alerts.length > 0) {
      generateSummary()
    }
  }, [countryCode, alerts])

  const generateSummary = async () => {
    setLoading(true)

    try {
      // Get enhanced alerts with ML intelligence
      const response = await fetch(`http://localhost:8000/api/alerts/${countryCode}/enhanced`)

      if (response.ok) {
        const enhancedAlerts = await response.json()
        generateSummaryFromEnhancedAlerts(enhancedAlerts)
      } else {
        // Generate fallback summary from available data
        generateFallbackSummary()
      }
    } catch (error) {
      console.warn('Failed to fetch enhanced alerts, using fallback:', error)
      generateFallbackSummary()
    }

    setLoading(false)
  }

  const generateSummaryFromEnhancedAlerts = (enhancedAlerts) => {
    let criticalCount = 0
    let deadlineCount = 0
    let generalCount = 0
    let requirementTypes = new Set()
    let deadlines = []
    let mandatoryItems = []
    let penalties = []
    let upcomingDeadlines = []

    enhancedAlerts.forEach(alert => {
      const intelligence = alert.intelligence

      if (intelligence) {
        // Use ML-generated risk scores and categories
        if (intelligence.risk_score >= 70 || intelligence.requirement_type === 'critical') {
          criticalCount++
          mandatoryItems.push(alert.title)
        } else if (intelligence.risk_score >= 40 || intelligence.requirement_type === 'important') {
          deadlineCount++
        } else {
          generalCount++
        }

        // Add requirement types from ML analysis
        if (intelligence.requirement_type) {
          requirementTypes.add(intelligence.requirement_type)
        }

        // Add compliance deadlines
        if (intelligence.compliance_deadline) {
          upcomingDeadlines.push(intelligence.compliance_deadline)
          deadlines.push(alert.title)
        }

        // Add penalties
        if (intelligence.penalties && intelligence.penalties.length > 0) {
          penalties.push(...intelligence.penalties.slice(0, 2))
        }
      } else {
        // Fallback for alerts without intelligence
        generalCount++
      }
    })

    setSummary({
      critical_count: criticalCount,
      deadline_count: deadlineCount,
      general_count: generalCount,
      requirement_types: Array.from(requirementTypes),
      upcoming_deadlines: upcomingDeadlines.slice(0, 3),
      mandatory_requirements: mandatoryItems.slice(0, 5),
      penalties: penalties.slice(0, 3),
      emergency_contacts: getEmergencyContacts(countryCode),
      compliance_status: {
        total_requirements: mandatoryItems.length,
        completed: 0,
        pending: mandatoryItems.length
      }
    })
  }

  const generateFallbackSummary = () => {
    // Analyze alerts for keywords to create basic summary
    const criticalKeywords = ['mandatory', 'required', 'must', 'prohibited', 'forbidden']
    const deadlineKeywords = ['deadline', 'before', 'within', 'days', 'weeks']
    const healthKeywords = ['health', 'vaccination', 'medical', 'certificate']
    const visaKeywords = ['visa', 'permit', 'entry', 'passport']

    let criticalCount = 0
    let deadlineCount = 0
    let generalCount = alerts.length
    let requirementTypes = new Set()
    let deadlines = []
    let mandatoryItems = []

    alerts.forEach(alert => {
      const content = alert.title.toLowerCase()

      if (criticalKeywords.some(keyword => content.includes(keyword))) {
        criticalCount++
        mandatoryItems.push(alert.title)
      }

      if (deadlineKeywords.some(keyword => content.includes(keyword))) {
        deadlineCount++
        deadlines.push(alert.title)
      }

      if (healthKeywords.some(keyword => content.includes(keyword))) {
        requirementTypes.add('health')
      }

      if (visaKeywords.some(keyword => content.includes(keyword))) {
        requirementTypes.add('visa')
      }
    })

    setSummary({
      critical_count: criticalCount,
      deadline_count: deadlineCount,
      general_count: generalCount - criticalCount,
      requirement_types: Array.from(requirementTypes),
      upcoming_deadlines: deadlines.slice(0, 3),
      mandatory_requirements: mandatoryItems.slice(0, 5),
      emergency_contacts: getEmergencyContacts(countryCode),
      compliance_status: {
        total_requirements: mandatoryItems.length,
        completed: 0,
        pending: mandatoryItems.length
      }
    })
  }

  const getEmergencyContacts = (countryCode) => {
    // Basic emergency contacts for common countries
    const contacts = {
      'NP': [
        { type: 'Embassy', number: '+977-1-4411179', service: 'US Embassy Nepal' },
        { type: 'Emergency', number: '100', service: 'Police' },
        { type: 'Medical', number: '102', service: 'Ambulance' }
      ],
      'IT': [
        { type: 'Embassy', number: '+39-06-46741', service: 'US Embassy Italy' },
        { type: 'Emergency', number: '112', service: 'General Emergency' },
        { type: 'Medical', number: '118', service: 'Medical Emergency' }
      ],
      'RU': [
        { type: 'Embassy', number: '+7-495-728-5000', service: 'US Embassy Russia' },
        { type: 'Emergency', number: '112', service: 'Emergency Services' },
        { type: 'Medical', number: '103', service: 'Medical Emergency' }
      ]
    }

    return contacts[countryCode] || [
      { type: 'Emergency', number: '112', service: 'International Emergency' }
    ]
  }

  const getRequirementIcon = (type) => {
    switch (type) {
      case 'visa': return '🛂'
      case 'health': return '🏥'
      case 'customs': return '📦'
      case 'entry': return '✈️'
      default: return '📋'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle size={16} className="text-green-600" />
      case 'warning': return <AlertCircle size={16} className="text-yellow-600" />
      case 'critical': return <XCircle size={16} className="text-red-600" />
      default: return <Clock size={16} className="text-gray-600" />
    }
  }

  if (loading) {
    return (
      <div className={`smart-summary loading ${className}`}>
        <div className="summary-header">
          <h3>📊 Analyzing Travel Requirements...</h3>
        </div>
      </div>
    )
  }

  if (!summary) {
    return null
  }

  return (
    <div className={`smart-summary ${className}`}>
      <style jsx>{`
        .smart-summary {
          background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
          border-radius: 16px;
          padding: 20px;
          margin-bottom: 20px;
          border: 1px solid #cbd5e1;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .smart-summary.loading {
          background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
          text-align: center;
          padding: 40px 20px;
        }

        .summary-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 2px solid #e2e8f0;
        }

        .summary-header h3 {
          margin: 0;
          font-size: 1.25rem;
          font-weight: 700;
          color: #1e293b;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .summary-stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
          margin-bottom: 20px;
        }

        .stat-card {
          background: white;
          border-radius: 12px;
          padding: 16px;
          text-align: center;
          border: 1px solid #e2e8f0;
          transition: all 0.2s ease;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .stat-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }

        .stat-number {
          font-size: 2rem;
          font-weight: 800;
          line-height: 1;
          margin-bottom: 4px;
        }

        .stat-number.critical {
          color: #dc2626;
        }

        .stat-number.warning {
          color: #f59e0b;
        }

        .stat-number.info {
          color: #3b82f6;
        }

        .stat-label {
          font-size: 0.875rem;
          color: #64748b;
          font-weight: 500;
        }

        .summary-content {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin-bottom: 20px;
        }

        .summary-section {
          background: white;
          border-radius: 12px;
          padding: 16px;
          border: 1px solid #e2e8f0;
        }

        .section-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
          font-weight: 600;
          color: #1e293b;
          font-size: 0.95rem;
        }

        .requirement-types {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .requirement-badge {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 6px 12px;
          background: #f1f5f9;
          border: 1px solid #cbd5e1;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 500;
          color: #475569;
        }

        .deadline-list, .mandatory-list {
          list-style: none;
          margin: 0;
          padding: 0;
        }

        .deadline-item, .mandatory-item {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 8px 0;
          border-bottom: 1px solid #f1f5f9;
          font-size: 0.875rem;
          line-height: 1.4;
        }

        .deadline-item:last-child, .mandatory-item:last-child {
          border-bottom: none;
        }

        .compliance-checklist {
          background: white;
          border-radius: 12px;
          padding: 16px;
          border: 1px solid #e2e8f0;
          margin-bottom: 16px;
        }

        .checklist-progress {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
        }

        .progress-bar {
          flex: 1;
          height: 8px;
          background: #e2e8f0;
          border-radius: 4px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #10b981, #059669);
          width: ${summary.compliance_status.total_requirements > 0
            ? (summary.compliance_status.completed / summary.compliance_status.total_requirements) * 100
            : 0}%;
          transition: width 0.3s ease;
        }

        .progress-text {
          font-size: 0.875rem;
          font-weight: 600;
          color: #374151;
        }

        .emergency-contacts {
          background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
          border: 1px solid #fecaca;
          border-radius: 12px;
          padding: 16px;
        }

        .contact-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .contact-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 12px;
          background: white;
          border-radius: 8px;
          border: 1px solid #f3f4f6;
        }

        .contact-info {
          display: flex;
          flex-direction: column;
        }

        .contact-service {
          font-weight: 600;
          color: #374151;
          font-size: 0.875rem;
        }

        .contact-type {
          font-size: 0.75rem;
          color: #6b7280;
        }

        .contact-number {
          font-family: monospace;
          font-weight: 600;
          color: #dc2626;
          font-size: 0.875rem;
        }

        @media (max-width: 768px) {
          .summary-content {
            grid-template-columns: 1fr;
            gap: 16px;
          }

          .summary-stats {
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
          }

          .stat-card {
            padding: 12px;
          }

          .stat-number {
            font-size: 1.5rem;
          }
        }
      `}</style>

      {/* Header */}
      <div className="summary-header">
        <h3>📊 Travel Intelligence Summary</h3>
        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>

      {/* Statistics */}
      <div className="summary-stats">
        <div className="stat-card">
          <div className="stat-number critical">{summary.critical_count}</div>
          <div className="stat-label">Critical Legal Requirements</div>
        </div>
        <div className="stat-card">
          <div className="stat-number warning">{summary.deadline_count}</div>
          <div className="stat-label">Upcoming Deadlines</div>
        </div>
        <div className="stat-card">
          <div className="stat-number info">{summary.general_count}</div>
          <div className="stat-label">General Updates</div>
        </div>
      </div>

      {/* Compliance Progress */}
      {summary.compliance_status.total_requirements > 0 && (
        <div className="compliance-checklist">
          <div className="section-header">
            <CheckCircle size={16} />
            Compliance Progress
          </div>
          <div className="checklist-progress">
            <div className="progress-bar">
              <div className="progress-fill"></div>
            </div>
            <div className="progress-text">
              {summary.compliance_status.completed}/{summary.compliance_status.total_requirements} Complete
            </div>
          </div>
        </div>
      )}

      {/* Content Sections */}
      <div className="summary-content">
        {/* Requirement Types */}
        <div className="summary-section">
          <div className="section-header">
            <Shield size={16} />
            Requirement Types
          </div>
          <div className="requirement-types">
            {summary.requirement_types.length > 0 ? (
              summary.requirement_types.map((type, index) => (
                <div key={index} className="requirement-badge">
                  <span>{getRequirementIcon(type)}</span>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </div>
              ))
            ) : (
              <div style={{ color: '#64748b', fontSize: '0.875rem' }}>
                No specific requirements identified
              </div>
            )}
          </div>
        </div>

        {/* Upcoming Deadlines */}
        <div className="summary-section">
          <div className="section-header">
            <Clock size={16} />
            Priority Deadlines
          </div>
          <ul className="deadline-list">
            {summary.upcoming_deadlines.length > 0 ? (
              summary.upcoming_deadlines.map((deadline, index) => (
                <li key={index} className="deadline-item">
                  {getStatusIcon('warning')}
                  <span>{deadline.length > 60 ? `${deadline.substring(0, 60)}...` : deadline}</span>
                </li>
              ))
            ) : (
              <li style={{ color: '#64748b', fontSize: '0.875rem' }}>
                No urgent deadlines identified
              </li>
            )}
          </ul>
        </div>
      </div>

      {/* Penalties Section */}
      {summary.penalties && summary.penalties.length > 0 && (
        <div className="summary-section" style={{ marginTop: '16px' }}>
          <div className="section-header">
            <AlertTriangle size={16} />
            Penalty Information
          </div>
          <ul className="deadline-list">
            {summary.penalties.map((penalty, index) => (
              <li key={index} className="deadline-item">
                {getStatusIcon('critical')}
                <span style={{ color: '#dc2626' }}>
                  {penalty.length > 80 ? `${penalty.substring(0, 80)}...` : penalty}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Emergency Contacts */}
      <div className="emergency-contacts">
        <div className="section-header">
          <Phone size={16} />
          Emergency Contacts
        </div>
        <div className="contact-list">
          {summary.emergency_contacts.map((contact, index) => (
            <div key={index} className="contact-item">
              <div className="contact-info">
                <div className="contact-service">{contact.service}</div>
                <div className="contact-type">{contact.type}</div>
              </div>
              <div className="contact-number">{contact.number}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default SmartAlertSummary