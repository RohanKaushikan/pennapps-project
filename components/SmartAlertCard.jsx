import { useState, useEffect } from 'react'
import { AlertTriangle, Clock, FileText, Shield, AlertCircle, CheckCircle, Info } from 'lucide-react'

const SmartAlertCard = ({ alert, intelligence, className = "" }) => {
  // Fallback to basic display if no intelligence available
  if (!intelligence) {
    return <BasicAlertCard alert={alert} className={className} />
  }

  const getRiskLevelColor = (riskScore) => {
    if (riskScore >= 70) return '#dc2626' // red
    if (riskScore >= 40) return '#f59e0b' // orange
    return '#10b981' // green
  }

  const getRequirementTypeIcon = (type) => {
    switch (type) {
      case 'critical': return <AlertTriangle size={16} className="text-red-600" />
      case 'important': return <AlertCircle size={16} className="text-orange-500" />
      default: return <Info size={16} className="text-blue-500" />
    }
  }

  const getUrgencyBadge = (urgency) => {
    const urgencyLabels = {
      immediate: 'Immediate Action',
      urgent: 'Before Travel',
      moderate: 'Plan Ahead',
      low: 'Informational Only'
    }

    const styles = {
      immediate: 'bg-red-100 text-red-800 border-red-200',
      urgent: 'bg-orange-100 text-orange-800 border-orange-200',
      moderate: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      low: 'bg-green-100 text-green-800 border-green-200'
    }

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${styles[urgency] || styles.low}`}>
        {urgencyLabels[urgency] || 'Informational Only'}
      </span>
    )
  }

  const getLegalCategoryBadge = (category) => {
    const styles = {
      mandatory: 'bg-red-50 text-red-700 border-red-200',
      recommended: 'bg-blue-50 text-blue-700 border-blue-200',
      prohibited: 'bg-gray-50 text-gray-700 border-gray-200',
      mixed: 'bg-purple-50 text-purple-700 border-purple-200'
    }

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded border ${styles[category] || styles.mixed}`}>
        {category}
      </span>
    )
  }

  const getLegalHighlight = (intelligence) => {
    // Use the ML-generated legal category and requirement type from backend
    if (!intelligence.legal_category || intelligence.legal_category === 'mixed') return null
    
    const category = intelligence.legal_category.charAt(0).toUpperCase() + intelligence.legal_category.slice(1)
    const requirementType = intelligence.requirement_type || 'requirement'
    
    return `${category}: ${requirementType.charAt(0).toUpperCase() + requirementType.slice(1)} requirement`
  }

  return (
    <div className={`smart-alert-card ${className}`}>
      <style jsx>{`
        .smart-alert-card {
          background: white;
          border-radius: 16px;
          border: 1px solid #e5e7eb;
          overflow: hidden;
          transition: all 0.3s ease;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .smart-alert-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 15px -3px rgba(0, 0, 0, 0.1);
        }

        .risk-indicator {
          height: 4px;
          background: ${getRiskLevelColor(intelligence.risk_score)};
          width: 100%;
        }

        .alert-header {
          padding: 16px 20px 12px;
          border-bottom: 1px solid #f3f4f6;
        }

        .alert-title {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          margin-bottom: 8px;
        }

        .alert-badges {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-bottom: 8px;
        }

        .alert-content {
          padding: 0 20px 16px;
        }

        .original-content {
          color: #374151;
          font-size: 0.9rem;
          line-height: 1.5;
          margin-bottom: 12px;
        }

        .intelligence-overlay {
          background: #f9fafb;
          border-radius: 8px;
          padding: 12px;
          margin-top: 12px;
        }

        .overlay-section {
          margin-bottom: 8px;
        }

        .overlay-section:last-child {
          margin-bottom: 0;
        }

        .overlay-label {
          font-size: 0.75rem;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 4px;
        }

        .overlay-content {
          font-size: 0.85rem;
          color: #374151;
        }

        .penalty-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .penalty-item {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px 0;
          font-size: 0.8rem;
          color: #dc2626;
        }

        .document-list {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .document-tag {
          background: #dbeafe;
          color: #1e40af;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.7rem;
          font-weight: 500;
        }

        .compliance-timeline {
          background: #fef3c7;
          border: 1px solid #f59e0b;
          border-radius: 6px;
          padding: 8px;
          margin-top: 8px;
        }

        .timeline-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.8rem;
          color: #92400e;
        }

        .confidence-indicator {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.7rem;
          color: #6b7280;
          margin-top: 8px;
        }

        .confidence-bar {
          width: 40px;
          height: 4px;
          background: #e5e7eb;
          border-radius: 2px;
          overflow: hidden;
        }

        .confidence-fill {
          height: 100%;
          background: ${intelligence.confidence_score > 0.8 ? '#10b981' :
                       intelligence.confidence_score > 0.6 ? '#f59e0b' : '#dc2626'};
          width: ${intelligence.confidence_score * 100}%;
          transition: width 0.3s ease;
        }

        .risk-score {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.8rem;
          font-weight: 600;
          color: ${getRiskLevelColor(intelligence.risk_score)};
        }
      `}</style>

      {/* Risk level indicator bar */}
      <div className="risk-indicator"></div>

      {/* Alert header with badges */}
      <div className="alert-header">
        <div className="alert-title">
          {getRequirementTypeIcon(intelligence.requirement_type)}
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '600', color: '#1f2937', lineHeight: '1.4' }}>
            {alert.title}
          </h3>
        </div>

        <div className="alert-badges">
          {getUrgencyBadge(intelligence.urgency_level)}
          {getLegalCategoryBadge(intelligence.legal_category)}
          <div className="risk-score">
            <Shield size={12} />
            Risk: {intelligence.risk_score}/100
          </div>
        </div>
      </div>

      {/* Alert content */}
      <div className="alert-content">
        {/* Original content (unchanged) */}
        <div className="original-content">
          <a href={alert.url} target="_blank" rel="noopener noreferrer"
             style={{ color: '#2563eb', textDecoration: 'none' }}>
            {alert.title}
          </a>
          <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '4px' }}>
            {alert.source} • {new Date(alert.timestamp).toLocaleDateString()}
          </div>
        </div>

        {/* Intelligence overlay */}
        <div className="intelligence-overlay">
          {/* Legal Highlight */}
          {getLegalHighlight(intelligence) && (
            <div className="overlay-section">
              <div className="overlay-label">Legal Requirement</div>
              <div className="overlay-content" style={{ 
                fontWeight: '600', 
                color: intelligence.legal_category === 'mandatory' ? '#dc2626' : 
                       intelligence.legal_category === 'prohibited' ? '#7c2d12' : '#1d4ed8'
              }}>
                {getLegalHighlight(intelligence)}
              </div>
            </div>
          )}

          {/* Penalties */}
          {intelligence.penalties && intelligence.penalties.length > 0 && (
            <div className="overlay-section">
              <div className="overlay-label">Penalties Identified</div>
              <ul className="penalty-list">
                {intelligence.penalties.slice(0, 2).map((penalty, index) => (
                  <li key={index} className="penalty-item">
                    <AlertTriangle size={12} />
                    {penalty.length > 60 ? `${penalty.substring(0, 60)}...` : penalty}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Fine amounts */}
          {intelligence.fine_amounts && intelligence.fine_amounts.length > 0 && (
            <div className="overlay-section">
              <div className="overlay-label">Fines</div>
              <div className="overlay-content" style={{ color: '#dc2626', fontWeight: '600' }}>
                {intelligence.fine_amounts.join(', ')}
              </div>
            </div>
          )}

          {/* Document requirements */}
          {intelligence.document_requirements && intelligence.document_requirements.length > 0 && (
            <div className="overlay-section">
              <div className="overlay-label">Documents Required</div>
              <div className="document-list">
                {intelligence.document_requirements.map((doc, index) => (
                  <span key={index} className="document-tag">
                    <FileText size={10} style={{ display: 'inline', marginRight: '2px' }} />
                    {doc}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Compliance deadline */}
          {intelligence.compliance_deadline && (
            <div className="compliance-timeline">
              <div className="timeline-item">
                <Clock size={12} />
                Deadline: {intelligence.compliance_deadline}
              </div>
            </div>
          )}

          {/* Confidence indicator */}
          <div className="confidence-indicator">
            Analysis confidence:
            <div className="confidence-bar">
              <div className="confidence-fill"></div>
            </div>
            {Math.round(intelligence.confidence_score * 100)}%
          </div>
        </div>
      </div>
    </div>
  )
}

// Basic fallback component
const BasicAlertCard = ({ alert, className = "" }) => {
  return (
    <div className={`basic-alert-card ${className}`}>
      <style jsx>{`
        .basic-alert-card {
          background: white;
          border-radius: 16px;
          padding: 20px;
          margin-bottom: 16px;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
          border: 1px solid #e5e7eb;
        }

        .basic-content {
          color: #374151;
          line-height: 1.5;
        }

        .basic-meta {
          font-size: 0.875rem;
          color: #6b7280;
          margin-top: 8px;
        }
      `}</style>

      <div className="basic-content">
        <a href={alert.url} target="_blank" rel="noopener noreferrer"
           style={{ color: '#2563eb', textDecoration: 'none', fontWeight: '500' }}>
          {alert.title}
        </a>
        <div className="basic-meta">
          {alert.source} • {new Date(alert.timestamp).toLocaleDateString()}
        </div>
      </div>
    </div>
  )
}

export default SmartAlertCard