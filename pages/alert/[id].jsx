import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { ArrowLeft, AlertTriangle, Globe, Calendar, ExternalLink, CheckCircle, Clock } from 'lucide-react'

export default function AlertDetail() {
  const router = useRouter()
  const { id } = router.query
  const [alert, setAlert] = useState(null)
  const [loading, setLoading] = useState(true)
  const [markingRead, setMarkingRead] = useState(false)

  useEffect(() => {
    if (id) {
      fetchAlert()
    }
  }, [id])

  const fetchAlert = async () => {
    setLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/v1/alerts/${id}?user_id=1`)
      if (response.ok) {
        const data = await response.json()
        setAlert(data)
      } else {
        console.error('Failed to fetch alert')
      }
    } catch (error) {
      console.error('Error fetching alert:', error)
    } finally {
      setLoading(false)
    }
  }

  const markAsRead = async () => {
    setMarkingRead(true)
    try {
      const response = await fetch(`http://localhost:8000/api/v1/alerts/${id}/mark-read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 1, action: 'mark_read' })
      })
      if (response.ok) {
        setAlert({...alert, user_status: {...alert.user_status, is_read: true}})
      }
    } catch (error) {
      console.error('Error marking alert as read:', error)
    } finally {
      setMarkingRead(false)
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
      1: 'Low Risk',
      2: 'Moderate Risk',
      3: 'High Risk',
      4: 'Very High Risk',
      5: 'Critical Risk'
    }
    return labels[level] || 'Unknown Risk'
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Not specified'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const formatDateTime = (dateString) => {
    if (!dateString) return 'Not specified'
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        backgroundColor: '#f8fafc',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid #e5e7eb',
            borderTop: '4px solid #3b82f6',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }} />
          <div>Loading alert details...</div>
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

  if (!alert) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        backgroundColor: '#f8fafc',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{ textAlign: 'center' }}>
          <AlertTriangle size={48} style={{ color: '#6b7280', marginBottom: '16px' }} />
          <h2>Alert Not Found</h2>
          <p style={{ color: '#6b7280', marginBottom: '20px' }}>
            The alert you're looking for doesn't exist or has been removed.
          </p>
          <button 
            onClick={() => router.push('/dashboard')}
            style={{
              padding: '12px 24px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer'
            }}
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
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
          max-width: 800px;
          margin: 0 auto;
          display: flex;
          align-items: center;
          gap: 16px;
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
        .header h1 {
          font-size: 24px;
          font-weight: bold;
          margin: 0;
          flex: 1;
        }
        .content {
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
        }
        .alert-card {
          background: white;
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          margin-bottom: 20px;
        }
        .alert-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 20px;
        }
        .alert-title {
          font-size: 28px;
          font-weight: bold;
          color: #1f2937;
          margin: 0;
          line-height: 1.3;
        }
        .risk-badge {
          padding: 8px 16px;
          border-radius: 12px;
          font-size: 14px;
          font-weight: 600;
          color: white;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .alert-meta {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
          padding: 20px;
          background: #f8fafc;
          border-radius: 12px;
        }
        .meta-item {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #4b5563;
        }
        .meta-item strong {
          color: #1f2937;
          font-weight: 600;
        }
        .alert-description {
          font-size: 16px;
          line-height: 1.6;
          color: #374151;
          margin-bottom: 24px;
          white-space: pre-wrap;
        }
        .categories {
          margin-bottom: 24px;
        }
        .categories h3 {
          font-size: 16px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 12px 0;
        }
        .category-tags {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
        .category-tag {
          background: #e0e7ff;
          color: #3730a3;
          padding: 6px 12px;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
        }
        .source-info {
          background: #f0f9ff;
          border: 1px solid #bae6fd;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 24px;
        }
        .source-info h3 {
          font-size: 16px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 8px 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .source-link {
          color: #3b82f6;
          text-decoration: none;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
        }
        .source-link:hover {
          text-decoration: underline;
        }
        .actions {
          display: flex;
          gap: 12px;
          padding-top: 20px;
          border-top: 1px solid #e5e7eb;
        }
        .btn {
          padding: 12px 24px;
          border-radius: 8px;
          border: none;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          gap: 8px;
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
          border: 1px solid #d1d5db;
        }
        .btn-secondary:hover {
          background: #e5e7eb;
        }
        .btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .read-status {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
        }
        .read-status.read {
          background: #d1fae5;
          color: #065f46;
        }
        .read-status.unread {
          background: #dbeafe;
          color: #1e40af;
        }
        @media (max-width: 768px) {
          .alert-header {
            flex-direction: column;
            gap: 16px;
          }
          .alert-meta {
            grid-template-columns: 1fr;
          }
          .actions {
            flex-direction: column;
          }
        }
      `}</style>

      {/* Header */}
      <div className="header">
        <div className="header-content">
          <button className="back-btn" onClick={() => router.push('/dashboard')}>
            <ArrowLeft size={16} />
            Back
          </button>
          <h1>Alert Details</h1>
        </div>
      </div>

      {/* Content */}
      <div className="content">
        <div className="alert-card">
          <div className="alert-header">
            <h1 className="alert-title">{alert.title}</h1>
            <div 
              className="risk-badge"
              style={{ backgroundColor: getRiskColor(alert.risk_level) }}
            >
              <AlertTriangle size={16} />
              {getRiskLabel(alert.risk_level)}
            </div>
          </div>

          <div className="alert-meta">
            <div className="meta-item">
              <Globe size={16} />
              <span><strong>Country:</strong> {alert.country?.name || 'Unknown'}</span>
            </div>
            <div className="meta-item">
              <Calendar size={16} />
              <span><strong>Created:</strong> {formatDateTime(alert.created_at)}</span>
            </div>
            {alert.expires_at && (
              <div className="meta-item">
                <Clock size={16} />
                <span><strong>Expires:</strong> {formatDate(alert.expires_at)}</span>
              </div>
            )}
            <div className="meta-item">
              {alert.user_status?.is_read ? (
                <div className="read-status read">
                  <CheckCircle size={16} />
                  Read
                </div>
              ) : (
                <div className="read-status unread">
                  <Clock size={16} />
                  Unread
                </div>
              )}
            </div>
          </div>

          <div className="alert-description">
            {alert.full_text || alert.description}
          </div>

          {alert.categories && alert.categories.length > 0 && (
            <div className="categories">
              <h3>Categories</h3>
              <div className="category-tags">
                {alert.categories.map((category, idx) => (
                  <span key={idx} className="category-tag">{category}</span>
                ))}
              </div>
            </div>
          )}

          {alert.source && (
            <div className="source-info">
              <h3>
                <ExternalLink size={16} />
                Source Information
              </h3>
              <p style={{ margin: '0 0 8px 0', color: '#4b5563' }}>
                <strong>Source:</strong> {alert.source.name}
              </p>
              <p style={{ margin: '0 0 8px 0', color: '#4b5563' }}>
                <strong>Type:</strong> {alert.source.source_type}
              </p>
              {alert.source.url && (
                <a 
                  href={alert.source.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="source-link"
                >
                  <ExternalLink size={14} />
                  View Original Source
                </a>
              )}
            </div>
          )}

          <div className="actions">
            {!alert.user_status?.is_read && (
              <button 
                className="btn btn-primary"
                onClick={markAsRead}
                disabled={markingRead}
              >
                {markingRead ? (
                  <>
                    <div style={{
                      width: '16px',
                      height: '16px',
                      border: '2px solid transparent',
                      borderTop: '2px solid currentColor',
                      borderRadius: '50%',
                      animation: 'spin 1s linear infinite'
                    }} />
                    Marking as Read...
                  </>
                ) : (
                  <>
                    <CheckCircle size={16} />
                    Mark as Read
                  </>
                )}
              </button>
            )}
            <button 
              className="btn btn-secondary"
              onClick={() => router.push('/dashboard')}
            >
              Back to Dashboard
            </button>
          </div>
        </div>
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
