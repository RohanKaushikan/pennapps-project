import { useState } from 'react'

export default function Home() {
  const [count, setCount] = useState(0)

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
                Server-side rendering
              </li>
              <li className="flex items-center text-gray-700">
                <span className="text-green-500 mr-2">✅</span>
                Automatic code splitting
              </li>
              <li className="flex items-center text-gray-700">
                <span className="text-green-500 mr-2">✅</span>
                Built-in optimization
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
