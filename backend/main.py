from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.datasets import make_regression
import json
from typing import List, Dict, Any

# Initialize FastAPI app
app = FastAPI(
    title="ML Backend API",
    description="Python backend for ML operations with React frontend",
    version="1.0.0"
)

# Configure CORS to allow requests from Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class PredictionRequest(BaseModel):
    features: List[float]
    model_type: str = "linear_regression"

class PredictionResponse(BaseModel):
    prediction: float
    confidence: float
    model_used: str

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str

# Global variable to store trained model
trained_model = None

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="ML Backend API is running!",
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return HealthResponse(
        status="healthy",
        message="Backend is ready for ML operations",
        version="1.0.0"
    )

@app.post("/api/train", response_model=Dict[str, Any])
async def train_model():
    """Train a simple linear regression model with sample data"""
    global trained_model
    
    try:
        # Generate sample training data
        X, y = make_regression(n_samples=100, n_features=1, noise=0.1, random_state=42)
        
        # Train the model
        trained_model = LinearRegression()
        trained_model.fit(X, y)
        
        # Calculate training score
        score = trained_model.score(X, y)
        
        return {
            "message": "Model trained successfully",
            "model_type": "Linear Regression",
            "training_score": round(score, 4),
            "samples_trained": len(X),
            "features": X.shape[1]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.post("/api/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Make predictions using the trained model"""
    global trained_model
    
    if trained_model is None:
        raise HTTPException(status_code=400, detail="Model not trained yet. Please train the model first.")
    
    try:
        # Convert features to numpy array and reshape for single prediction
        features_array = np.array(request.features).reshape(1, -1)
        
        # Make prediction
        prediction = trained_model.predict(features_array)[0]
        
        # Calculate confidence (simplified - in real ML you'd use proper confidence intervals)
        confidence = min(0.95, max(0.1, abs(prediction) / 100))
        
        return PredictionResponse(
            prediction=round(prediction, 4),
            confidence=round(confidence, 4),
            model_used=request.model_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.get("/api/model/info")
async def get_model_info():
    """Get information about the current model"""
    global trained_model
    
    if trained_model is None:
        return {"message": "No model trained yet", "model": None}
    
    return {
        "message": "Model is trained and ready",
        "model_type": "Linear Regression",
        "is_trained": True,
        "coefficients": trained_model.coef_.tolist() if hasattr(trained_model, 'coef_') else None,
        "intercept": trained_model.intercept_ if hasattr(trained_model, 'intercept_') else None
    }

@app.post("/api/reset")
async def reset_model():
    """Reset the trained model"""
    global trained_model
    trained_model = None
    return {"message": "Model reset successfully"}

# Travel app endpoints
@app.get("/api/country-info")
async def get_country_info():
    """Get country information for travel app"""
    # This is demo data - replace with real data source
    return {
        "name": "Japan",
        "welcome": [
            {
                "icon": "🎌",
                "title": "Welcome to Japan!",
                "message": "Konnichiwa! Your travel companion is ready to help."
            },
            {
                "icon": "🏮",
                "title": "Cultural Experience",
                "message": "Discover the rich traditions and modern innovations of Japan."
            },
            {
                "icon": "🍱",
                "title": "Culinary Adventure",
                "message": "From sushi to ramen, explore Japan's incredible food culture."
            }
        ],
        "transport": [
            "IC cards work on all trains and subways",
            "Follow blue signs for domestic, red for international",
            "Shinkansen (bullet train) requires reserved seats for long distances",
            "Taxis are expensive but very reliable and clean",
            "JR Pass available for tourists - great value for long-distance travel",
            "Download Google Maps or Hyperdia for train schedules"
        ],
        "culture": [
            "Remove shoes when entering homes and some restaurants",
            "Bowing is customary - a slight nod is perfectly acceptable",
            "Keep voices low on public transportation",
            "Cash is still king - many places don't accept cards",
            "Don't eat or drink while walking",
            "Gift-giving is important - bring small gifts from your country"
        ],
        "language": [
            {
                "native": "こんにちは (Konnichiwa)",
                "meaning": "Hello (formal greeting)"
            },
            {
                "native": "ありがとうございます (Arigatou gozaimasu)",
                "meaning": "Thank you very much"
            },
            {
                "native": "すみません (Sumimasen)",
                "meaning": "Excuse me / I'm sorry"
            },
            {
                "native": "英語を話せますか？ (Eigo wo hanasemasu ka?)",
                "meaning": "Do you speak English?"
            },
            {
                "native": "おいくらですか？ (Oikura desu ka?)",
                "meaning": "How much does it cost?"
            },
            {
                "native": "トイレはどこですか？ (Toire wa doko desu ka?)",
                "meaning": "Where is the bathroom?"
            }
        ]
    }

@app.get("/api/countries")
async def get_countries():
    """Get list of available countries"""
    return {
        "countries": [
            {"code": "JP", "name": "Japan", "flag": "🇯🇵"},
            {"code": "KR", "name": "South Korea", "flag": "🇰🇷"},
            {"code": "TH", "name": "Thailand", "flag": "🇹🇭"},
            {"code": "SG", "name": "Singapore", "flag": "🇸🇬"},
            {"code": "FR", "name": "France", "flag": "🇫🇷"},
            {"code": "IT", "name": "Italy", "flag": "🇮🇹"},
            {"code": "ES", "name": "Spain", "flag": "🇪🇸"},
            {"code": "DE", "name": "Germany", "flag": "🇩🇪"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
