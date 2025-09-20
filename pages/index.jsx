import { useState, useEffect } from 'react'

export default function Home() {
  const [count, setCount] = useState(0)
  const [mlData, setMlData] = useState({
    isTrained: false,
    prediction: null,
    confidence: null,
    loading: false,
    error: null
  })
  const [inputValue, setInputValue] = useState('0.5')

  // API functions
  const trainModel = async () => {
    setMlData(prev => ({ ...prev, loading: true, error: null }))
    try {
      const response = await fetch('http://localhost:8000/api/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()
      if (response.ok) {
        setMlData(prev => ({ ...prev, isTrained: true, loading: false }))
      } else {
        throw new Error(data.detail || 'Training failed')
      }
    } catch (error) {
      setMlData(prev => ({ ...prev, error: error.message, loading: false }))
    }
  }

  const makePrediction = async () => {
    if (!mlData.isTrained) {
      setMlData(prev => ({ ...prev, error: 'Please train the model first' }))
      return
    }
    
    setMlData(prev => ({ ...prev, loading: true, error: null }))
    try {
      const response = await fetch('http://localhost:8000/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          features: [parseFloat(inputValue)],
          model_type: 'linear_regression'
        })
      })
      const data = await response.json()
      if (response.ok) {
        setMlData(prev => ({
          ...prev,
          prediction: data.prediction,
          confidence: data.confidence,
          loading: false
        }))
      } else {
        throw new Error(data.detail || 'Prediction failed')
      }
    } catch (error) {
      setMlData(prev => ({ ...prev, error: error.message, loading: false }))
    }
  }

  const resetModel = async () => {
    setMlData(prev => ({ ...prev, loading: true, error: null }))
    try {
      const response = await fetch('http://localhost:8000/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      if (response.ok) {
        setMlData({
          isTrained: false,
          prediction: null,
          confidence: null,
          loading: false,
          error: null
        })
      }
    } catch (error) {
      setMlData(prev => ({ ...prev, error: error.message, loading: false }))
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl p-8 max-w-2xl w-full mx-4">
        <header className="text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-800 mb-4">
            Welcome to Next.js!
          </h1>
          <p className="text-lg text-gray-600 mb-8 leading-relaxed">
            This is a basic Next.js webapp created for you.
          </p>
          
          <div className="bg-gray-50 rounded-2xl p-6 mb-8 border-2 border-gray-200">
            <p className="text-xl font-semibold text-gray-700 mb-4">
              You clicked the button {count} times
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button 
                className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white px-8 py-3 rounded-full font-semibold hover:from-indigo-600 hover:to-purple-700 transform hover:-translate-y-1 transition-all duration-300 shadow-lg hover:shadow-xl"
                onClick={() => setCount(count + 1)}
              >
                Click me!
              </button>
              <button 
                className="bg-gradient-to-r from-red-500 to-pink-600 text-white px-8 py-3 rounded-full font-semibold hover:from-red-600 hover:to-pink-700 transform hover:-translate-y-1 transition-all duration-300 shadow-lg hover:shadow-xl"
                onClick={() => setCount(0)}
              >
                Reset
              </button>
            </div>
          </div>
          
          {/* ML Section */}
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl p-6 mb-8 border-2 border-blue-200">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">🤖 Machine Learning Demo</h2>
            
            {/* Model Status */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Model Status:</span>
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  mlData.isTrained 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {mlData.isTrained ? '✅ Trained' : '⏳ Not Trained'}
                </span>
              </div>
            </div>

            {/* Training Section */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-700 mb-3">Train Model</h3>
              <button 
                className="bg-gradient-to-r from-green-500 to-emerald-600 text-white px-6 py-2 rounded-full font-semibold hover:from-green-600 hover:to-emerald-700 transform hover:-translate-y-1 transition-all duration-300 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={trainModel}
                disabled={mlData.loading}
              >
                {mlData.loading ? '⏳ Training...' : '🚀 Train Model'}
              </button>
            </div>

            {/* Prediction Section */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-700 mb-3">Make Prediction</h3>
              <div className="flex flex-col sm:flex-row gap-3 mb-3">
                <input
                  type="number"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Enter a number (e.g., 0.5)"
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  step="0.1"
                />
                <button 
                  className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-2 rounded-full font-semibold hover:from-blue-600 hover:to-indigo-700 transform hover:-translate-y-1 transition-all duration-300 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={makePrediction}
                  disabled={mlData.loading || !mlData.isTrained}
                >
                  {mlData.loading ? '⏳ Predicting...' : '🔮 Predict'}
                </button>
              </div>
              
              {/* Prediction Results */}
              {mlData.prediction !== null && (
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <span className="text-sm font-medium text-gray-600">Prediction:</span>
                      <p className="text-xl font-bold text-blue-600">{mlData.prediction.toFixed(4)}</p>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-gray-600">Confidence:</span>
                      <p className="text-xl font-bold text-green-600">{(mlData.confidence * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Reset Section */}
            <div className="flex justify-between items-center">
              <button 
                className="bg-gradient-to-r from-red-500 to-pink-600 text-white px-4 py-2 rounded-full font-semibold hover:from-red-600 hover:to-pink-700 transform hover:-translate-y-1 transition-all duration-300 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={resetModel}
                disabled={mlData.loading}
              >
                🔄 Reset Model
              </button>
              
              {mlData.error && (
                <div className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg border border-red-200">
                  ⚠️ {mlData.error}
                </div>
              )}
            </div>
          </div>

          <div className="bg-gray-50 rounded-2xl p-6 border-2 border-gray-200">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Features included:</h2>
            <ul className="space-y-2 text-left">
              <li className="flex items-center text-gray-700">
                <span className="text-green-500 mr-2">✅</span>
                Next.js 14 with App Router
              </li>
              <li className="flex items-center text-gray-700">
                <span className="text-green-500 mr-2">✅</span>
                React 18 with hooks
              </li>
              <li className="flex items-center text-gray-700">
                <span className="text-green-500 mr-2">✅</span>
                Tailwind CSS styling
              </li>
              <li className="flex items-center text-gray-700">
                <span className="text-green-500 mr-2">✅</span>
                Python FastAPI backend
              </li>
              <li className="flex items-center text-gray-700">
                <span className="text-green-500 mr-2">✅</span>
                Machine Learning integration
              </li>
              <li className="flex items-center text-gray-700">
                <span className="text-green-500 mr-2">✅</span>
                Real-time API communication
              </li>
              <li className="flex items-center text-gray-700">
                <span className="text-green-500 mr-2">✅</span>
                No HTML file needed!
              </li>
            </ul>
          </div>
        </header>
      </div>
    </div>
  )
}
