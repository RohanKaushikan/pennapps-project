import { useState, useEffect } from 'react'
import { User, Mail, Globe, Bell, Settings, ArrowLeft, Save, RefreshCw } from 'lucide-react'

export default function ProfilePage() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [preferences, setPreferences] = useState({
    preferred_countries: [],
    risk_tolerance: 'medium',
    notification_frequency: 'daily',
    categories_of_interest: ['visa', 'legal', 'safety'],
    notification_enabled: true
  })

  const availableCountries = [
    { code: 'US', name: 'United States' },
    { code: 'CA', name: 'Canada' },
    { code: 'GB', name: 'United Kingdom' },
    { code: 'FR', name: 'France' },
    { code: 'DE', name: 'Germany' },
    { code: 'IT', name: 'Italy' },
    { code: 'ES', name: 'Spain' },
    { code: 'JP', name: 'Japan' },
    { code: 'AU', name: 'Australia' },
    { code: 'BR', name: 'Brazil' },
    { code: 'CN', name: 'China' },
    { code: 'IN', name: 'India' },
    { code: 'MX', name: 'Mexico' },
    { code: 'RU', name: 'Russia' },
    { code: 'KR', name: 'South Korea' }
  ]

  const categories = [
    { value: 'visa', label: 'Visa Requirements' },
    { value: 'health', label: 'Health & Medical' },
    { value: 'safety', label: 'Safety & Security' },
    { value: 'legal', label: 'Legal Issues' },
    { value: 'entry', label: 'Entry Requirements' },
    { value: 'transport', label: 'Transportation' },
    { value: 'customs', label: 'Customs & Immigration' }
  ]

  useEffect(() => {
    fetchUser()
  }, [])

  const fetchUser = async () => {
    setLoading(true)
    try {
      // For demo purposes, we'll use user ID 1
      // In a real app, you'd get this from authentication
      const response = await fetch('http://localhost:8001/api/v1/users/1')
      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        if (userData.travel_preferences) {
          setPreferences({
            ...preferences,
            ...userData.travel_preferences
          })
        }
      } else {
        // If user doesn't exist, create a demo user
        setUser({
          id: 1,
          email: 'demo@example.com',
          travel_preferences: preferences
        })
      }
    } catch (error) {
      console.error('Error fetching user:', error)
      // Create demo user on error
      setUser({
        id: 1,
        email: 'demo@example.com',
        travel_preferences: preferences
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage('')

    try {
      const updatedUser = {
        ...user,
        travel_preferences: preferences
      }

      const response = await fetch(`http://localhost:8001/api/v1/users/${user.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedUser)
      })

      if (response.ok) {
        setMessage('Profile updated successfully!')
        setUser(updatedUser)
      } else {
        setMessage('Error updating profile. Please try again.')
      }
    } catch (error) {
      setMessage('Connection error. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleCountryToggle = (countryCode) => {
    setPreferences(prev => ({
      ...prev,
      preferred_countries: prev.preferred_countries.includes(countryCode)
        ? prev.preferred_countries.filter(c => c !== countryCode)
        : [...prev.preferred_countries, countryCode]
    }))
  }

  const handleCategoryToggle = (categoryValue) => {
    setPreferences(prev => ({
      ...prev,
      categories_of_interest: prev.categories_of_interest.includes(categoryValue)
        ? prev.categories_of_interest.filter(c => c !== categoryValue)
        : [...prev.categories_of_interest, categoryValue]
    }))
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
          <div>Loading profile...</div>
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

  return (
    <div style={{ backgroundColor: '#f8fafc', minHeight: '100vh' }}>
      <style>{`
        .header {
          background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
          color: white;
          padding: 20px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .header-content {
          max-width: 800px;
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
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
        }
        .profile-card {
          background: white;
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          margin-bottom: 20px;
        }
        .profile-header {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-bottom: 24px;
          padding-bottom: 20px;
          border-bottom: 1px solid #e5e7eb;
        }
        .profile-avatar {
          width: 60px;
          height: 60px;
          background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 24px;
          font-weight: bold;
        }
        .profile-info h2 {
          font-size: 24px;
          font-weight: bold;
          color: #1f2937;
          margin: 0 0 4px 0;
        }
        .profile-info p {
          color: #6b7280;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .section {
          margin-bottom: 32px;
        }
        .section-title {
          font-size: 18px;
          font-weight: 600;
          color: #1f2937;
          margin: 0 0 16px 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .form-group {
          margin-bottom: 20px;
        }
        .form-label {
          display: block;
          font-weight: 500;
          color: #374151;
          margin-bottom: 8px;
          font-size: 14px;
        }
        .form-input, .form-select {
          width: 100%;
          padding: 12px 16px;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          font-size: 14px;
          transition: border-color 0.2s;
        }
        .form-input:focus, .form-select:focus {
          outline: none;
          border-color: #7c3aed;
        }
        .countries-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 8px;
          margin-top: 8px;
        }
        .country-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
          font-size: 14px;
        }
        .country-item:hover {
          background: #f8fafc;
        }
        .country-item.selected {
          background: #ede9fe;
          border-color: #7c3aed;
          color: #7c3aed;
        }
        .checkbox {
          width: 16px;
          height: 16px;
          border: 2px solid #d1d5db;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .checkbox.checked {
          background: #7c3aed;
          border-color: #7c3aed;
          color: white;
        }
        .categories-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 8px;
          margin-top: 8px;
        }
        .category-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
          font-size: 14px;
        }
        .category-item:hover {
          background: #f8fafc;
        }
        .category-item.selected {
          background: #ede9fe;
          border-color: #7c3aed;
          color: #7c3aed;
        }
        .toggle-switch {
          position: relative;
          display: inline-block;
          width: 44px;
          height: 24px;
        }
        .toggle-switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        .slider {
          position: absolute;
          cursor: pointer;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: #ccc;
          transition: .4s;
          border-radius: 24px;
        }
        .slider:before {
          position: absolute;
          content: "";
          height: 18px;
          width: 18px;
          left: 3px;
          bottom: 3px;
          background-color: white;
          transition: .4s;
          border-radius: 50%;
        }
        input:checked + .slider {
          background-color: #7c3aed;
        }
        input:checked + .slider:before {
          transform: translateX(20px);
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
          background: #7c3aed;
          color: white;
        }
        .btn-primary:hover {
          background: #6d28d9;
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
        .message {
          padding: 12px 16px;
          border-radius: 8px;
          margin-bottom: 20px;
          font-size: 14px;
        }
        .message.success {
          background: #d1fae5;
          color: #065f46;
          border: 1px solid #a7f3d0;
        }
        .message.error {
          background: #fee2e2;
          color: #991b1b;
          border: 1px solid #fecaca;
        }
        .info-text {
          color: #6b7280;
          font-size: 12px;
          margin-top: 4px;
        }
        @media (max-width: 768px) {
          .countries-grid, .categories-grid {
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
          <button className="back-btn" onClick={() => window.location.href = '/dashboard'}>
            <ArrowLeft size={16} />
            Back to Dashboard
          </button>
          <h1>Profile Settings</h1>
        </div>
      </div>

      {/* Content */}
      <div className="content">
        <div className="profile-card">
          <div className="profile-header">
            <div className="profile-avatar">
              <User size={24} />
            </div>
            <div className="profile-info">
              <h2>Travel Preferences</h2>
              <p>
                <Mail size={16} />
                {user?.email || 'demo@example.com'}
              </p>
            </div>
          </div>

          {message && (
            <div className={`message ${message.includes('successfully') ? 'success' : 'error'}`}>
              {message}
            </div>
          )}

          {/* Preferred Countries */}
          <div className="section">
            <h3 className="section-title">
              <Globe size={20} />
              Preferred Countries
            </h3>
            <p className="info-text">Select countries you're interested in for travel advisories</p>
            <div className="countries-grid">
              {availableCountries.map(country => (
                <div 
                  key={country.code}
                  className={`country-item ${preferences.preferred_countries.includes(country.code) ? 'selected' : ''}`}
                  onClick={() => handleCountryToggle(country.code)}
                >
                  <div className={`checkbox ${preferences.preferred_countries.includes(country.code) ? 'checked' : ''}`}>
                    {preferences.preferred_countries.includes(country.code) && '✓'}
                  </div>
                  <span>{country.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Tolerance */}
          <div className="section">
            <h3 className="section-title">
              <Settings size={20} />
              Risk Tolerance
            </h3>
            <div className="form-group">
              <label className="form-label">How would you rate your risk tolerance for travel?</label>
              <select
                className="form-select"
                value={preferences.risk_tolerance}
                onChange={(e) => setPreferences({...preferences, risk_tolerance: e.target.value})}
              >
                <option value="low">Low - Prefer conservative travel advisories</option>
                <option value="medium">Medium - Balanced approach to risk</option>
                <option value="high">High - Comfortable with higher risk situations</option>
              </select>
            </div>
          </div>

          {/* Notification Settings */}
          <div className="section">
            <h3 className="section-title">
              <Bell size={20} />
              Notification Settings
            </h3>
            <div className="form-group">
              <label className="form-label">Notification Frequency</label>
              <select
                className="form-select"
                value={preferences.notification_frequency}
                onChange={(e) => setPreferences({...preferences, notification_frequency: e.target.value})}
              >
                <option value="immediate">Immediate - Get alerts as soon as they're published</option>
                <option value="daily">Daily - Receive a daily summary</option>
                <option value="weekly">Weekly - Weekly digest of important alerts</option>
                <option value="never">Never - No email notifications</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span>Enable notifications</span>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={preferences.notification_enabled}
                    onChange={(e) => setPreferences({...preferences, notification_enabled: e.target.checked})}
                  />
                  <span className="slider"></span>
                </label>
              </label>
              <p className="info-text">Receive email notifications for new travel advisories</p>
            </div>
          </div>

          {/* Categories of Interest */}
          <div className="section">
            <h3 className="section-title">
              <Settings size={20} />
              Categories of Interest
            </h3>
            <p className="info-text">Select the types of travel advisories you want to receive</p>
            <div className="categories-grid">
              {categories.map(category => (
                <div 
                  key={category.value}
                  className={`category-item ${preferences.categories_of_interest.includes(category.value) ? 'selected' : ''}`}
                  onClick={() => handleCategoryToggle(category.value)}
                >
                  <div className={`checkbox ${preferences.categories_of_interest.includes(category.value) ? 'checked' : ''}`}>
                    {preferences.categories_of_interest.includes(category.value) && '✓'}
                  </div>
                  <span>{category.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="actions">
            <button 
              className="btn btn-primary"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? (
                <>
                  <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} />
                  Saving...
                </>
              ) : (
                <>
                  <Save size={16} />
                  Save Changes
                </>
              )}
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => window.location.href = '/dashboard'}
            >
              Cancel
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
