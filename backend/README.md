# Python ML Backend

This is a FastAPI backend designed to work with the Next.js frontend for ML operations.

## Features

- **FastAPI** - Modern, fast web framework for building APIs
- **CORS enabled** - Allows communication with React frontend
- **ML ready** - Includes scikit-learn for machine learning
- **Type safety** - Uses Pydantic for request/response validation
- **Auto documentation** - Interactive API docs at `/docs`

## Setup

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Run the backend:**
   ```bash
   python main.py
   ```
   
   Or with uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access the API:**
   - API: `http://localhost:8000`
   - Interactive docs: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/health`

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health check
- `POST /api/train` - Train a linear regression model
- `POST /api/predict` - Make predictions
- `GET /api/model/info` - Get model information
- `POST /api/reset` - Reset the model

## Example Usage

```python
import requests

# Train model
response = requests.post("http://localhost:8000/api/train")
print(response.json())

# Make prediction
prediction_data = {
    "features": [0.5],
    "model_type": "linear_regression"
}
response = requests.post("http://localhost:8000/api/predict", json=prediction_data)
print(response.json())
```
