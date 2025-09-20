# PennApps Project - React + Python ML

A modern full-stack web application with a clean React frontend and powerful Python ML backend.

## 🚀 Features

### Frontend (Next.js + React)
- **Next.js 14** with App Router
- **React 18** with modern hooks
- **Tailwind CSS** for beautiful styling
- **Real-time ML integration** with Python backend
- **Responsive design** that works on all devices

### Backend (Python + FastAPI)
- **FastAPI** for high-performance API
- **scikit-learn** for machine learning
- **CORS enabled** for frontend communication
- **Auto-generated API docs** at `/docs`
- **Type safety** with Pydantic models

## 🛠️ Quick Start

### Option 1: Run Everything at Once
```bash
# Install all dependencies
npm run setup

# Start both frontend and backend
npm run dev:full
```

### Option 2: Run Separately

#### Frontend (Terminal 1)
```bash
# Install frontend dependencies
npm install

# Start Next.js development server
npm run dev
```

#### Backend (Terminal 2)
```bash
# Install Python dependencies
npm run backend:install

# Start Python backend
npm run backend
```

## 🌐 Access Your App

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🤖 ML Features

The app includes a complete ML demo:

1. **Train Model** - Train a linear regression model with sample data
2. **Make Predictions** - Input values and get ML predictions
3. **View Results** - See predictions with confidence scores
4. **Reset Model** - Clear the trained model

## 📁 Project Structure

```
pennapps-project/
├── pages/                 # Next.js pages
│   ├── _app.jsx          # App wrapper
│   └── index.jsx         # Main page with ML interface
├── src/
│   └── index.css         # Tailwind CSS imports
├── backend/              # Python backend
│   ├── main.py          # FastAPI application
│   ├── requirements.txt # Python dependencies
│   └── README.md        # Backend documentation
├── package.json         # Node.js dependencies
├── next.config.js       # Next.js configuration
├── tailwind.config.js   # Tailwind configuration
└── postcss.config.js    # PostCSS configuration
```

## 🔧 Development

### Frontend Development
- Hot reload enabled
- Tailwind CSS with IntelliSense
- ESLint for code quality

### Backend Development
- Auto-reload on file changes
- Interactive API documentation
- Type-safe request/response models

## 🚀 Deployment

### Frontend (Vercel/Netlify)
```bash
npm run build
```

### Backend (Railway/Heroku/Docker)
```bash
cd backend
pip install -r requirements.txt
python main.py
```

## 📚 API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health check
- `POST /api/train` - Train ML model
- `POST /api/predict` - Make predictions
- `GET /api/model/info` - Get model information
- `POST /api/reset` - Reset model

## 🎯 Perfect for ML Projects

This setup is ideal for:
- **Data Science demos**
- **ML model showcases**
- **Real-time predictions**
- **Interactive ML interfaces**
- **Rapid prototyping**

The clean separation between frontend and backend allows you to focus on your ML algorithms while maintaining a beautiful user interface!