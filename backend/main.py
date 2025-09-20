from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.datasets import make_regression
import json
from typing import List, Dict, Any
from spacy_processor import TravelContentProcessor, ScrapedContent, Alert, LocationTrigger, ChangeDetection

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

# Initialize spaCy processor
spacy_processor = TravelContentProcessor()

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

# spaCy and Travel Content Processing Endpoints

@app.post("/api/process-content")
async def process_content(content_data: Dict[str, Any]):
    """Process scraped content and generate alerts using spaCy"""
    try:
        alerts = spacy_processor.process_scraped_content(content_data)
        return {
            "message": "Content processed successfully",
            "alerts_generated": len(alerts),
            "alerts": [alert.__dict__ for alert in alerts]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content processing failed: {str(e)}")

@app.post("/api/process-location")
async def process_location(location_data: Dict[str, Any]):
    """Process location trigger and return relevant alerts"""
    try:
        alerts = spacy_processor.process_location_trigger(location_data)
        return {
            "message": "Location processed successfully",
            "alerts": [alert.__dict__ for alert in alerts]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Location processing failed: {str(e)}")

@app.post("/api/detect-changes")
async def detect_changes(request_data: Dict[str, str]):
    """Detect changes between old and new content"""
    try:
        old_content = request_data.get("old_content", "")
        new_content = request_data.get("new_content", "")
        
        change_detection = spacy_processor.detect_changes(old_content, new_content)
        
        if change_detection:
            return {
                "message": "Changes detected",
                "changes": change_detection.__dict__
            }
        else:
            return {
                "message": "No changes detected",
                "changes": None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Change detection failed: {str(e)}")

@app.get("/api/example-processing")
async def example_processing():
    """Run example processing to demonstrate spaCy capabilities"""
    try:
        # Example scraped content
        example_content = {
            "source_id": "us_state_dept",
            "country_code": "TH",
            "url": "https://travel.state.gov/thailand",
            "content": """
            <h1>Thailand Travel Advisory</h1>
            <p>Effective immediately, all travelers to Thailand must obtain a tourist visa for stays over 30 days. 
            This is a critical requirement that cannot be waived. Travelers without proper documentation will be denied entry.</p>
            <p>Additionally, proof of vaccination against COVID-19 is required for all international arrivals.</p>
            <p>Please note that the processing time for visa applications has been extended to 10-15 business days.</p>
            """,
            "content_hash": "sha256_hash_example",
            "scraped_at": "2025-01-20T10:30:00Z",
            "content_type": "travel_advisory"
        }
        
        # Process content
        alerts = spacy_processor.process_scraped_content(example_content)
        
        # Example location trigger
        location_data = {
            "user_id": "user123",
            "country_code": "TH",
            "lat": 13.7563,
            "lng": 100.5018,
            "entry_detected_at": "2025-01-20T10:30:00Z"
        }
        
        location_alerts = spacy_processor.process_location_trigger(location_data)
        
        return {
            "message": "Example processing completed",
            "content_alerts": [alert.__dict__ for alert in alerts],
            "location_alerts": [alert.__dict__ for alert in location_alerts],
            "total_alerts": len(alerts) + len(location_alerts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Example processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
