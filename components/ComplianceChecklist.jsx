import { useState, useEffect } from 'react'
import { CheckCircle, Circle, Clock, AlertTriangle, ExternalLink, Calendar, FileText } from 'lucide-react'

const ComplianceChecklist = ({ countryCode, alerts = [], className = "" }) => {
  const [checklist, setChecklist] = useState(null)
  const [completedItems, setCompletedItems] = useState(new Set())
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (countryCode && alerts.length > 0) {
      generateChecklist()
    }
  }, [countryCode, alerts])

  const generateChecklist = async () => {
    setLoading(true)

    try {
      // Get enhanced alerts with ML intelligence to generate checklist
      const response = await fetch(`http://localhost:8000/api/alerts/${countryCode}/enhanced`)

      if (response.ok) {
        const enhancedAlerts = await response.json()
        generateChecklistFromEnhancedAlerts(enhancedAlerts)
      } else {
        // Generate fallback checklist from available data
        generateFallbackChecklist()
      }
    } catch (error) {
      console.warn('Failed to fetch enhanced alerts for checklist, using fallback:', error)
      generateFallbackChecklist()
    }

    setLoading(false)
  }

  const generateChecklistFromEnhancedAlerts = (enhancedAlerts) => {
    const items = []
    const categories = new Set()

    enhancedAlerts.forEach((alert, index) => {
      const intelligence = alert.intelligence

      if (intelligence) {
        // Use ML-generated data to create checklist items
        const urgencyLevel = intelligence.urgency_level || 'low'
        const requirementType = intelligence.requirement_type || 'informational'
        const legalCategory = intelligence.legal_category || 'mixed'

        // Determine timeline based on urgency
        let timeline = 'Before travel'
        if (urgencyLevel === 'immediate') timeline = 'Immediate action required'
        else if (urgencyLevel === 'urgent') timeline = 'Before travel (1-2 weeks)'
        else if (intelligence.compliance_deadline) timeline = intelligence.compliance_deadline

        // Determine urgency level for display
        let urgency = 'moderate'
        if (intelligence.risk_score >= 70 || legalCategory === 'mandatory') urgency = 'critical'
        else if (intelligence.risk_score >= 40 || urgencyLevel === 'urgent') urgency = 'important'

        // Create checklist item
        const item = {
          id: `ml-${alert.id}`,
          category: requirementType,
          title: `${legalCategory.charAt(0).toUpperCase() + legalCategory.slice(1)} Requirement`,
          description: alert.title,
          urgency: urgency,
          timeline: timeline,
          status: 'pending',
          links: [
            { title: 'View Details', url: alert.url, type: 'official' }
          ],
          source: alert.title,
          penalties: intelligence.penalties || [],
          documents: intelligence.document_requirements || []
        }

        items.push(item)
        categories.add(requirementType)

        // Add document requirements as separate items
        if (intelligence.document_requirements && intelligence.document_requirements.length > 0) {
          intelligence.document_requirements.forEach((doc, docIndex) => {
            items.push({
              id: `doc-${alert.id}-${docIndex}`,
              category: 'documents',
              title: doc,
              description: `Required document identified from: ${alert.title.substring(0, 50)}...`,
              urgency: urgency,
              timeline: timeline,
              status: 'pending',
              links: [
                { title: 'Source Alert', url: alert.url, type: 'official' }
              ]
            })
            categories.add('documents')
          })
        }
      }
    })

    // Create timeline
    const timeline = [
      {
        period: 'Immediate action',
        items: items.filter(item => item.timeline.includes('Immediate') || item.urgency === 'critical')
      },
      {
        period: '1-2 weeks before',
        items: items.filter(item => item.timeline.includes('1-2 weeks') || item.timeline.includes('Before travel'))
      },
      {
        period: 'Upon arrival',
        items: items.filter(item => item.timeline.includes('arrival'))
      }
    ]

    setChecklist({
      country_code: countryCode,
      total_items: items.length,
      critical_items: items.filter(item => item.urgency === 'critical').length,
      categories: Array.from(categories),
      items: items,
      timeline: timeline,
      last_updated: new Date().toISOString()
    })
  }

  const generateFallbackChecklist = () => {
    const items = []

    // Analyze alerts for requirements
    alerts.forEach((alert, index) => {
      const content = alert.title.toLowerCase()

      // Visa requirements
      if (content.includes('visa') || content.includes('permit')) {
        items.push({
          id: `visa-${index}`,
          category: 'visa',
          title: 'Visa or Entry Permit',
          description: 'Check if visa is required for your nationality',
          urgency: content.includes('mandatory') || content.includes('required') ? 'critical' : 'important',
          timeline: 'Before travel (2-4 weeks)',
          status: 'pending',
          links: [
            { title: 'Check Visa Requirements', url: '#', type: 'official' }
          ],
          source: alert.title
        })
      }

      // Health requirements
      if (content.includes('health') || content.includes('vaccination') || content.includes('medical')) {
        items.push({
          id: `health-${index}`,
          category: 'health',
          title: 'Health Documentation',
          description: 'Required health certificates or vaccination records',
          urgency: 'important',
          timeline: 'Before travel (2-8 weeks)',
          status: 'pending',
          links: [
            { title: 'Health Requirements', url: '#', type: 'official' }
          ],
          source: alert.title
        })
      }

      // Document requirements
      if (content.includes('passport') || content.includes('document')) {
        items.push({
          id: `document-${index}`,
          category: 'documents',
          title: 'Travel Documents',
          description: 'Ensure passport validity and required documentation',
          urgency: 'critical',
          timeline: 'Before travel',
          status: 'pending',
          links: [
            { title: 'Document Checklist', url: '#', type: 'guide' }
          ],
          source: alert.title
        })
      }

      // Insurance and financial
      if (content.includes('insurance') || content.includes('financial')) {
        items.push({
          id: `insurance-${index}`,
          category: 'insurance',
          title: 'Travel Insurance',
          description: 'Obtain required travel insurance coverage',
          urgency: 'important',
          timeline: 'Before travel (1 week)',
          status: 'pending',
          links: [
            { title: 'Insurance Options', url: '#', type: 'guide' }
          ],
          source: alert.title
        })
      }
    })

    // Add default essential items if none found
    if (items.length === 0) {
      items.push(
        {
          id: 'passport-default',
          category: 'documents',
          title: 'Valid Passport',
          description: 'Ensure passport is valid for at least 6 months',
          urgency: 'critical',
          timeline: 'Before travel',
          status: 'pending',
          links: [
            { title: 'Passport Requirements', url: '#', type: 'official' }
          ]
        },
        {
          id: 'research-default',
          category: 'preparation',
          title: 'Research Local Laws',
          description: 'Review local customs and legal requirements',
          urgency: 'important',
          timeline: 'Before travel (1 week)',
          status: 'pending',
          links: [
            { title: 'Travel Advisories', url: '#', type: 'official' }
          ]
        }
      )
    }

    // Create timeline
    const timeline = [
      {
        period: '2-8 weeks before',
        items: items.filter(item => item.timeline.includes('2-8 weeks') || item.timeline.includes('4 weeks'))
      },
      {
        period: '1-2 weeks before',
        items: items.filter(item => item.timeline.includes('1 week') || item.timeline.includes('2 weeks'))
      },
      {
        period: 'Upon arrival',
        items: items.filter(item => item.timeline.includes('arrival'))
      }
    ]

    setChecklist({
      country_code: countryCode,
      total_items: items.length,
      critical_items: items.filter(item => item.urgency === 'critical').length,
      categories: ['visa', 'health', 'documents', 'insurance', 'preparation'],
      items: items,
      timeline: timeline,
      last_updated: new Date().toISOString()
    })
  }

  const toggleItem = (itemId) => {
    const newCompleted = new Set(completedItems)
    if (newCompleted.has(itemId)) {
      newCompleted.delete(itemId)
    } else {
      newCompleted.add(itemId)
    }
    setCompletedItems(newCompleted)
  }

  const getCompletionPercentage = () => {
    if (!checklist || checklist.items.length === 0) return 0
    return Math.round((completedItems.size / checklist.items.length) * 100)
  }

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'visa': return '🛂'
      case 'health': return '🏥'
      case 'documents': return '📄'
      case 'insurance': return '🛡️'
      case 'preparation': return '📋'
      default: return '✅'
    }
  }

  const getUrgencyColor = (urgency) => {
    switch (urgency) {
      case 'critical': return '#dc2626'
      case 'important': return '#f59e0b'
      case 'moderate': return '#3b82f6'
      default: return '#6b7280'
    }
  }

  const getLinkIcon = (type) => {
    switch (type) {
      case 'official': return <ExternalLink size={12} />
      case 'form': return <FileText size={12} />
      default: return <ExternalLink size={12} />
    }
  }

  if (loading) {
    return (
      <div className={`compliance-checklist loading ${className}`}>
        <div className="loading-content">
          <h3>📋 Generating Compliance Checklist...</h3>
        </div>
      </div>
    )
  }

  if (!checklist) {
    return null
  }

  return (
    <div className={`compliance-checklist ${className}`}>
      <style jsx>{`
        .compliance-checklist {
          background: white;
          border-radius: 16px;
          border: 1px solid #e5e7eb;
          overflow: hidden;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .compliance-checklist.loading {
          padding: 40px 20px;
          text-align: center;
          background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
        }

        .checklist-header {
          background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
          color: white;
          padding: 20px;
          position: relative;
          overflow: hidden;
        }

        .checklist-header::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
          opacity: 0.3;
        }

        .header-content {
          position: relative;
          z-index: 1;
        }

        .checklist-title {
          margin: 0 0 12px 0;
          font-size: 1.25rem;
          font-weight: 700;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .progress-overview {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-bottom: 16px;
        }

        .progress-circle {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: conic-gradient(#10b981 ${getCompletionPercentage()}%, rgba(255,255,255,0.3) 0%);
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
        }

        .progress-circle::before {
          content: '';
          position: absolute;
          width: 44px;
          height: 44px;
          background: #1e40af;
          border-radius: 50%;
        }

        .progress-percentage {
          position: relative;
          z-index: 1;
          font-weight: 700;
          font-size: 0.875rem;
        }

        .progress-stats {
          flex: 1;
        }

        .stat-row {
          display: flex;
          justify-content: space-between;
          margin-bottom: 4px;
          font-size: 0.875rem;
        }

        .checklist-content {
          padding: 0;
        }

        .category-section {
          border-bottom: 1px solid #f3f4f6;
        }

        .category-header {
          background: #f8fafc;
          padding: 12px 20px;
          font-weight: 600;
          color: #374151;
          font-size: 0.875rem;
          display: flex;
          align-items: center;
          gap: 8px;
          border-bottom: 1px solid #e5e7eb;
        }

        .checklist-items {
          padding: 0;
        }

        .checklist-item {
          padding: 16px 20px;
          border-bottom: 1px solid #f3f4f6;
          transition: all 0.2s ease;
          cursor: pointer;
        }

        .checklist-item:hover {
          background: #f9fafb;
        }

        .checklist-item:last-child {
          border-bottom: none;
        }

        .item-header {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 8px;
        }

        .item-checkbox {
          margin-top: 2px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .item-checkbox:hover {
          transform: scale(1.1);
        }

        .item-content {
          flex: 1;
        }

        .item-title {
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 4px;
          font-size: 0.95rem;
        }

        .item-title.completed {
          text-decoration: line-through;
          color: #9ca3af;
        }

        .item-description {
          color: #6b7280;
          font-size: 0.875rem;
          line-height: 1.4;
          margin-bottom: 8px;
        }

        .item-meta {
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 0.75rem;
        }

        .urgency-badge {
          padding: 3px 8px;
          border-radius: 12px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          background: ${getUrgencyColor('moderate')}20;
          color: ${getUrgencyColor('moderate')};
          border: 1px solid ${getUrgencyColor('moderate')}40;
        }

        .timeline-badge {
          display: flex;
          align-items: center;
          gap: 4px;
          color: #6b7280;
        }

        .item-links {
          display: flex;
          gap: 8px;
          margin-top: 8px;
        }

        .item-link {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          background: #dbeafe;
          color: #1e40af;
          text-decoration: none;
          border-radius: 6px;
          font-size: 0.75rem;
          font-weight: 500;
          transition: all 0.2s ease;
          border: 1px solid #bfdbfe;
        }

        .item-link:hover {
          background: #bfdbfe;
          transform: translateY(-1px);
        }

        .timeline-section {
          background: #f8fafc;
          padding: 20px;
          border-top: 1px solid #e5e7eb;
        }

        .timeline-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 16px;
          font-weight: 600;
          color: #374151;
        }

        .timeline-periods {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .timeline-period {
          background: white;
          border-radius: 12px;
          padding: 16px;
          border: 1px solid #e5e7eb;
        }

        .period-header {
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 8px;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.9rem;
        }

        .period-items {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .period-item {
          font-size: 0.875rem;
          color: #6b7280;
          padding: 4px 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        @media (max-width: 768px) {
          .progress-overview {
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 12px;
          }

          .item-meta {
            flex-direction: column;
            align-items: flex-start;
            gap: 6px;
          }

          .item-links {
            flex-wrap: wrap;
          }
        }
      `}</style>

      {/* Header */}
      <div className="checklist-header">
        <div className="header-content">
          <h3 className="checklist-title">
            <CheckCircle size={20} />
            Compliance Checklist
          </h3>

          <div className="progress-overview">
            <div className="progress-circle">
              <div className="progress-percentage">
                {getCompletionPercentage()}%
              </div>
            </div>

            <div className="progress-stats">
              <div className="stat-row">
                <span>Total Requirements:</span>
                <span>{checklist.total_items}</span>
              </div>
              <div className="stat-row">
                <span>Completed:</span>
                <span>{completedItems.size}</span>
              </div>
              <div className="stat-row">
                <span>Critical Items:</span>
                <span style={{ color: '#fbbf24' }}>{checklist.critical_items}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="checklist-content">
        {/* Group items by category */}
        {checklist.categories.map(category => {
          const categoryItems = checklist.items.filter(item => item.category === category)
          if (categoryItems.length === 0) return null

          return (
            <div key={category} className="category-section">
              <div className="category-header">
                <span>{getCategoryIcon(category)}</span>
                {category.charAt(0).toUpperCase() + category.slice(1)}
                <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#9ca3af' }}>
                  {categoryItems.filter(item => completedItems.has(item.id)).length}/{categoryItems.length}
                </span>
              </div>

              <div className="checklist-items">
                {categoryItems.map(item => (
                  <div
                    key={item.id}
                    className="checklist-item"
                    onClick={() => toggleItem(item.id)}
                  >
                    <div className="item-header">
                      <div className="item-checkbox">
                        {completedItems.has(item.id) ? (
                          <CheckCircle size={20} className="text-green-600" />
                        ) : (
                          <Circle size={20} className="text-gray-400" />
                        )}
                      </div>

                      <div className="item-content">
                        <div className={`item-title ${completedItems.has(item.id) ? 'completed' : ''}`}>
                          {item.title}
                        </div>
                        <div className="item-description">
                          {item.description}
                        </div>

                        <div className="item-meta">
                          <div
                            className="urgency-badge"
                            style={{
                              background: `${getUrgencyColor(item.urgency)}20`,
                              color: getUrgencyColor(item.urgency),
                              borderColor: `${getUrgencyColor(item.urgency)}40`
                            }}
                          >
                            {item.urgency}
                          </div>

                          <div className="timeline-badge">
                            <Clock size={12} />
                            {item.timeline}
                          </div>
                        </div>

                        {item.links && item.links.length > 0 && (
                          <div className="item-links">
                            {item.links.map((link, index) => (
                              <a
                                key={index}
                                href={link.url}
                                className="item-link"
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {getLinkIcon(link.type)}
                                {link.title}
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Timeline */}
      {checklist.timeline && checklist.timeline.length > 0 && (
        <div className="timeline-section">
          <div className="timeline-header">
            <Calendar size={16} />
            Recommended Timeline
          </div>

          <div className="timeline-periods">
            {checklist.timeline.map((period, index) => (
              <div key={index} className="timeline-period">
                <div className="period-header">
                  <Clock size={14} />
                  {period.period}
                </div>
                <div className="period-items">
                  {period.items.map((item, itemIndex) => (
                    <div key={itemIndex} className="period-item">
                      <span>{getCategoryIcon(item.category)}</span>
                      {item.title}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default ComplianceChecklist