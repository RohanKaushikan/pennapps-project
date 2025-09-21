import { useState, useEffect } from 'react'
import { Filter, ChevronDown, Calendar, Shield, AlertTriangle, Clock, FileText } from 'lucide-react'

const EnhancedFiltering = ({ alerts = [], onFilterChange, className = "" }) => {
  const [filters, setFilters] = useState({
    requirementType: 'all',
    urgency: 'all',
    legalObligation: 'all',
    timeframe: 'all'
  })
  const [isExpanded, setIsExpanded] = useState(false)
  const [filterStats, setFilterStats] = useState(null)

  useEffect(() => {
    generateFilterStats()
  }, [alerts])

  useEffect(() => {
    if (onFilterChange) {
      onFilterChange(filters)
    }
  }, [filters, onFilterChange])

  const generateFilterStats = () => {
    const stats = {
      total: alerts.length,
      requirementTypes: {
        visa: 0,
        health: 0,
        customs: 0,
        entry: 0,
        financial: 0,
        other: 0
      },
      urgency: {
        immediate: 0,
        urgent: 0,
        moderate: 0,
        low: 0
      },
      legalObligation: {
        mandatory: 0,
        recommended: 0,
        prohibited: 0
      },
      timeframe: {
        before_travel: 0,
        upon_arrival: 0,
        during_stay: 0
      }
    }

    alerts.forEach(alert => {
      const content = alert.title?.toLowerCase() || ''
      const intelligence = alert.intelligence

      // Requirement types
      if (content.includes('visa') || content.includes('permit')) {
        stats.requirementTypes.visa++
      } else if (content.includes('health') || content.includes('medical') || content.includes('vaccination')) {
        stats.requirementTypes.health++
      } else if (content.includes('customs') || content.includes('import') || content.includes('duty')) {
        stats.requirementTypes.customs++
      } else if (content.includes('entry') || content.includes('border') || content.includes('passport')) {
        stats.requirementTypes.entry++
      } else if (content.includes('financial') || content.includes('insurance') || content.includes('fund')) {
        stats.requirementTypes.financial++
      } else {
        stats.requirementTypes.other++
      }

      // Urgency (prefer intelligence, fallback to keywords)
      if (intelligence?.urgency_level) {
        stats.urgency[intelligence.urgency_level]++
      } else if (content.includes('immediate') || content.includes('urgent')) {
        stats.urgency.urgent++
      } else if (content.includes('soon') || content.includes('deadline')) {
        stats.urgency.moderate++
      } else {
        stats.urgency.low++
      }

      // Legal obligation (prefer intelligence, fallback to keywords)
      if (intelligence?.legal_category) {
        if (intelligence.legal_category === 'mandatory') {
          stats.legalObligation.mandatory++
        } else if (intelligence.legal_category === 'prohibited') {
          stats.legalObligation.prohibited++
        } else {
          stats.legalObligation.recommended++
        }
      } else if (content.includes('must') || content.includes('required') || content.includes('mandatory')) {
        stats.legalObligation.mandatory++
      } else if (content.includes('prohibited') || content.includes('forbidden') || content.includes('banned')) {
        stats.legalObligation.prohibited++
      } else {
        stats.legalObligation.recommended++
      }

      // Timeframe
      if (content.includes('before') || content.includes('advance') || content.includes('prior')) {
        stats.timeframe.before_travel++
      } else if (content.includes('arrival') || content.includes('entry') || content.includes('border')) {
        stats.timeframe.upon_arrival++
      } else if (content.includes('during') || content.includes('stay') || content.includes('visit')) {
        stats.timeframe.during_stay++
      } else {
        stats.timeframe.before_travel++
      }
    })

    setFilterStats(stats)
  }

  const updateFilter = (filterType, value) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value
    }))
  }

  const getActiveFilterCount = () => {
    return Object.values(filters).filter(value => value !== 'all').length
  }

  const resetFilters = () => {
    setFilters({
      requirementType: 'all',
      urgency: 'all',
      legalObligation: 'all',
      timeframe: 'all'
    })
  }

  const getFilterIcon = (filterType) => {
    switch (filterType) {
      case 'requirementType': return <FileText size={16} />
      case 'urgency': return <Clock size={16} />
      case 'legalObligation': return <Shield size={16} />
      case 'timeframe': return <Calendar size={16} />
      default: return <Filter size={16} />
    }
  }

  const getRequirementTypeIcon = (type) => {
    switch (type) {
      case 'visa': return '🛂'
      case 'health': return '🏥'
      case 'customs': return '📦'
      case 'entry': return '✈️'
      case 'financial': return '💰'
      default: return '📋'
    }
  }

  const getUrgencyIcon = (urgency) => {
    switch (urgency) {
      case 'immediate': return '🚨'
      case 'urgent': return '⚠️'
      case 'moderate': return '⏰'
      case 'low': return '📅'
      default: return '⏰'
    }
  }

  const getLegalIcon = (type) => {
    switch (type) {
      case 'mandatory': return '🔴'
      case 'prohibited': return '🚫'
      case 'recommended': return '🟡'
      default: return '📝'
    }
  }

  const getTimeframeIcon = (timeframe) => {
    switch (timeframe) {
      case 'before_travel': return '📅'
      case 'upon_arrival': return '🛬'
      case 'during_stay': return '🏨'
      default: return '⏰'
    }
  }

  if (!filterStats) return null

  return (
    <div className={`enhanced-filtering ${className}`}>
      <style jsx>{`
        .enhanced-filtering {
          background: white;
          border-radius: 12px;
          border: 1px solid #e5e7eb;
          margin-bottom: 16px;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .filter-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 20px;
          background: #f8fafc;
          border-bottom: 1px solid #e5e7eb;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .filter-header:hover {
          background: #f1f5f9;
        }

        .filter-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          color: #374151;
          font-size: 0.95rem;
        }

        .filter-summary {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.875rem;
          color: #6b7280;
        }

        .active-count {
          background: #3b82f6;
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 0.75rem;
          font-weight: 600;
          min-width: 20px;
          text-align: center;
        }

        .expand-icon {
          transition: transform 0.2s ease;
          transform: ${isExpanded ? 'rotate(180deg)' : 'rotate(0deg)'};
        }

        .filter-content {
          padding: 20px;
          display: ${isExpanded ? 'block' : 'none'};
          background: white;
        }

        .filter-controls {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .quick-stats {
          display: flex;
          gap: 16px;
          font-size: 0.875rem;
          color: #6b7280;
        }

        .stat-item {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .reset-button {
          background: #f3f4f6;
          border: 1px solid #d1d5db;
          color: #374151;
          padding: 6px 12px;
          border-radius: 6px;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .reset-button:hover {
          background: #e5e7eb;
        }

        .reset-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .filter-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 20px;
        }

        .filter-group {
          background: #f9fafb;
          border-radius: 12px;
          padding: 16px;
          border: 1px solid #f3f4f6;
        }

        .group-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
          font-weight: 600;
          color: #374151;
          font-size: 0.9rem;
        }

        .filter-options {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .filter-option {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 12px;
          background: white;
          border: 1px solid ${(option) => filters[option.filterType] === option.value ? '#3b82f6' : '#e5e7eb'};
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
          font-size: 0.875rem;
        }

        .filter-option:hover {
          border-color: #9ca3af;
          background: #f9fafb;
        }

        .filter-option.active {
          border-color: #3b82f6;
          background: #eff6ff;
          color: #1e40af;
        }

        .option-info {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .option-count {
          background: #e5e7eb;
          color: #6b7280;
          padding: 2px 6px;
          border-radius: 10px;
          font-size: 0.75rem;
          font-weight: 600;
          min-width: 24px;
          text-align: center;
        }

        .filter-option.active .option-count {
          background: #3b82f6;
          color: white;
        }

        @media (max-width: 768px) {
          .filter-grid {
            grid-template-columns: 1fr;
            gap: 16px;
          }

          .filter-controls {
            flex-direction: column;
            gap: 12px;
            align-items: stretch;
          }

          .quick-stats {
            justify-content: center;
            flex-wrap: wrap;
            gap: 8px;
          }
        }
      `}</style>

      {/* Header */}
      <div className="filter-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="filter-title">
          <Filter size={16} />
          Enhanced Filtering
        </div>
        <div className="filter-summary">
          {getActiveFilterCount() > 0 && (
            <div className="active-count">{getActiveFilterCount()}</div>
          )}
          <span>{filterStats.total} alerts</span>
          <ChevronDown size={16} className="expand-icon" />
        </div>
      </div>

      {/* Content */}
      <div className="filter-content">
        {/* Controls */}
        <div className="filter-controls">
          <div className="quick-stats">
            <div className="stat-item">
              <AlertTriangle size={14} />
              {filterStats.legalObligation.mandatory} mandatory
            </div>
            <div className="stat-item">
              <Clock size={14} />
              {filterStats.urgency.immediate + filterStats.urgency.urgent} urgent
            </div>
            <div className="stat-item">
              <FileText size={14} />
              {filterStats.requirementTypes.visa + filterStats.requirementTypes.health} key requirements
            </div>
          </div>
          <button
            className="reset-button"
            onClick={resetFilters}
            disabled={getActiveFilterCount() === 0}
          >
            Reset Filters
          </button>
        </div>

        {/* Filter Grid */}
        <div className="filter-grid">
          {/* Requirement Type */}
          <div className="filter-group">
            <div className="group-header">
              {getFilterIcon('requirementType')}
              Requirement Type
            </div>
            <div className="filter-options">
              <div
                className={`filter-option ${filters.requirementType === 'all' ? 'active' : ''}`}
                onClick={() => updateFilter('requirementType', 'all')}
              >
                <div className="option-info">
                  <span>📋</span>
                  All Types
                </div>
                <div className="option-count">{filterStats.total}</div>
              </div>
              {Object.entries(filterStats.requirementTypes).map(([type, count]) => (
                <div
                  key={type}
                  className={`filter-option ${filters.requirementType === type ? 'active' : ''}`}
                  onClick={() => updateFilter('requirementType', type)}
                >
                  <div className="option-info">
                    <span>{getRequirementTypeIcon(type)}</span>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </div>
                  <div className="option-count">{count}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Urgency */}
          <div className="filter-group">
            <div className="group-header">
              {getFilterIcon('urgency')}
              Urgency Level
            </div>
            <div className="filter-options">
              <div
                className={`filter-option ${filters.urgency === 'all' ? 'active' : ''}`}
                onClick={() => updateFilter('urgency', 'all')}
              >
                <div className="option-info">
                  <span>⏰</span>
                  All Levels
                </div>
                <div className="option-count">{filterStats.total}</div>
              </div>
              {Object.entries(filterStats.urgency).map(([urgency, count]) => (
                <div
                  key={urgency}
                  className={`filter-option ${filters.urgency === urgency ? 'active' : ''}`}
                  onClick={() => updateFilter('urgency', urgency)}
                >
                  <div className="option-info">
                    <span>{getUrgencyIcon(urgency)}</span>
                    {urgency.charAt(0).toUpperCase() + urgency.slice(1)}
                  </div>
                  <div className="option-count">{count}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Legal Obligation */}
          <div className="filter-group">
            <div className="group-header">
              {getFilterIcon('legalObligation')}
              Legal Obligation
            </div>
            <div className="filter-options">
              <div
                className={`filter-option ${filters.legalObligation === 'all' ? 'active' : ''}`}
                onClick={() => updateFilter('legalObligation', 'all')}
              >
                <div className="option-info">
                  <span>📝</span>
                  All Types
                </div>
                <div className="option-count">{filterStats.total}</div>
              </div>
              {Object.entries(filterStats.legalObligation).map(([type, count]) => (
                <div
                  key={type}
                  className={`filter-option ${filters.legalObligation === type ? 'active' : ''}`}
                  onClick={() => updateFilter('legalObligation', type)}
                >
                  <div className="option-info">
                    <span>{getLegalIcon(type)}</span>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </div>
                  <div className="option-count">{count}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Timeframe */}
          <div className="filter-group">
            <div className="group-header">
              {getFilterIcon('timeframe')}
              When Required
            </div>
            <div className="filter-options">
              <div
                className={`filter-option ${filters.timeframe === 'all' ? 'active' : ''}`}
                onClick={() => updateFilter('timeframe', 'all')}
              >
                <div className="option-info">
                  <span>⏰</span>
                  All Times
                </div>
                <div className="option-count">{filterStats.total}</div>
              </div>
              {Object.entries(filterStats.timeframe).map(([timeframe, count]) => (
                <div
                  key={timeframe}
                  className={`filter-option ${filters.timeframe === timeframe ? 'active' : ''}`}
                  onClick={() => updateFilter('timeframe', timeframe)}
                >
                  <div className="option-info">
                    <span>{getTimeframeIcon(timeframe)}</span>
                    {timeframe.replace('_', ' ').split(' ').map(word =>
                      word.charAt(0).toUpperCase() + word.slice(1)
                    ).join(' ')}
                  </div>
                  <div className="option-count">{count}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EnhancedFiltering