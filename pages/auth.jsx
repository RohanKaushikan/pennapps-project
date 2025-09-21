import { useState } from 'react'
import { User, Mail, LogIn } from 'lucide-react'

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      if (isLogin) {
        // For demo, we'll just redirect to dashboard
        // In a real app, you'd authenticate here
        setMessage('Login successful! Redirecting...')
        setTimeout(() => {
          window.location.href = '/dashboard'
        }, 1000)
      } else {
        // Create user
        const response = await fetch('http://localhost:8001/api/v1/users/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email })
        })

        if (response.ok) {
          setMessage('Account created successfully! Redirecting...')
          setTimeout(() => {
            window.location.href = '/dashboard'
          }, 1000)
        } else {
          const error = await response.json()
          setMessage(error.detail || 'Error creating account')
        }
      }
    } catch (error) {
      setMessage('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <style>{`
        .auth-container {
          background: white;
          border-radius: 20px;
          padding: 40px;
          box-shadow: 0 20px 40px rgba(0,0,0,0.1);
          width: 100%;
          max-width: 400px;
        }
        .auth-header {
          text-align: center;
          margin-bottom: 30px;
        }
        .auth-header h1 {
          font-size: 28px;
          font-weight: bold;
          color: #1f2937;
          margin: 0 0 8px 0;
        }
        .auth-header p {
          color: #6b7280;
          margin: 0;
        }
        .form-group {
          margin-bottom: 20px;
        }
        .form-label {
          display: block;
          font-weight: 500;
          color: #374151;
          margin-bottom: 8px;
        }
        .form-input {
          width: 100%;
          padding: 12px 16px;
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          font-size: 16px;
          transition: border-color 0.2s;
          box-sizing: border-box;
        }
        .form-input:focus {
          outline: none;
          border-color: #3b82f6;
        }
        .submit-btn {
          width: 100%;
          padding: 14px;
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          color: white;
          border: none;
          border-radius: 12px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: transform 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        .submit-btn:hover {
          transform: translateY(-1px);
        }
        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }
        .toggle-btn {
          background: none;
          border: none;
          color: #3b82f6;
          cursor: pointer;
          font-weight: 500;
          margin-top: 20px;
          text-align: center;
          width: 100%;
          padding: 10px;
        }
        .message {
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 20px;
          text-align: center;
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
        .demo-note {
          background: #f3f4f6;
          border-radius: 8px;
          padding: 16px;
          margin-top: 20px;
          text-align: center;
          font-size: 14px;
          color: #6b7280;
        }
      `}</style>

      <div className="auth-container">
        <div className="auth-header">
          <User size={48} color="#3b82f6" />
          <h1>Travel Alerts</h1>
          <p>{isLogin ? 'Welcome back!' : 'Create your account'}</p>
        </div>

        {message && (
          <div className={`message ${message.includes('successful') ? 'success' : 'error'}`}>
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">
              <Mail size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
              Email Address
            </label>
            <input
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
            />
          </div>

          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? (
              <>
                <div style={{
                  width: '20px',
                  height: '20px',
                  border: '2px solid transparent',
                  borderTop: '2px solid white',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
                {isLogin ? 'Signing in...' : 'Creating account...'}
              </>
            ) : (
              <>
                <LogIn size={20} />
                {isLogin ? 'Sign In' : 'Create Account'}
              </>
            )}
          </button>
        </form>

        <button 
          className="toggle-btn"
          onClick={() => setIsLogin(!isLogin)}
        >
          {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
        </button>

        <div className="demo-note">
          <strong>Demo Mode:</strong> Use any valid email address to create an account or sign in.
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
