// In-memory storage for simulation
let currentLocation = null;
let previousLocation = null;

// Function to fetch real anomaly data from backend
const fetchRealAnomalyData = async (countryCode) => {
  try {
    const response = await fetch(`http://localhost:8000/api/anomalies/${countryCode}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch anomaly data: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching real anomaly data:', error);
    return null;
  }
};

// Function to convert real anomaly data to alert format
const convertAnomalyToAlerts = (anomalyData) => {
  if (!anomalyData) return null;

  const alerts = [];
  
  // Add anomaly alert if there's unusual activity
  if (anomalyData.is_anomaly) {
    alerts.push({
      id: "news-anomaly",
      title: "Unusual News Activity Detected",
      level: "critical",
      message: `${anomalyData.spike_factor}x more travel news than normal (${anomalyData.current_count} articles)`,
      details: `Baseline: ${anomalyData.baseline} articles/hour. Current spike indicates significant travel-related developments.`,
      spike_factor: anomalyData.spike_factor,
      current_count: anomalyData.current_count
    });
  } else {
    alerts.push({
      id: "normal-activity",
      title: "Normal News Activity",
      level: "info",
      message: "No unusual travel news activity detected",
      details: `Current activity: ${anomalyData.current_count} articles (baseline: ${anomalyData.baseline}/hour)`,
      spike_factor: anomalyData.spike_factor,
      current_count: anomalyData.current_count
    });
  }

  // Add headlines as additional alerts
  if (anomalyData.top_headlines && anomalyData.top_headlines.length > 0) {
    anomalyData.top_headlines.forEach((headline, index) => {
      alerts.push({
        id: `headline-${index}`,
        title: "Recent News",
        level: "warning",
        message: headline.title,
        details: `Source: ${headline.source}`,
        url: headline.url
      });
    });
  }

  return {
    country: anomalyData.country_name,
    flag: anomalyData.flag,
    alerts: alerts,
    anomaly_data: anomalyData
  };
};

export default async function handler(req, res) {
  if (req.method === 'POST') {
    const { countryCode, action } = req.body;
    
    if (action === 'setLocation') {
      previousLocation = currentLocation;
      currentLocation = countryCode;
      
      // Check if location changed
      const locationChanged = previousLocation !== currentLocation;
      
      let alerts = null;
      if (locationChanged) {
        // Fetch real anomaly data from backend
        const anomalyData = await fetchRealAnomalyData(countryCode);
        alerts = convertAnomalyToAlerts(anomalyData);
      }
      
      res.status(200).json({
        success: true,
        currentLocation,
        previousLocation,
        locationChanged,
        alerts,
        message: locationChanged 
          ? `Location changed from ${previousLocation || 'unknown'} to ${countryCode}`
          : `Location set to ${countryCode}`
      });
    } else if (action === 'getLocation') {
      res.status(200).json({
        success: true,
        currentLocation,
        previousLocation
      });
    } else if (action === 'getAlerts') {
      let alerts = null;
      if (currentLocation) {
        const anomalyData = await fetchRealAnomalyData(currentLocation);
        alerts = convertAnomalyToAlerts(anomalyData);
      }
      res.status(200).json({
        success: true,
        alerts,
        currentLocation
      });
    } else {
      res.status(400).json({ success: false, message: 'Invalid action' });
    }
  } else if (req.method === 'GET') {
    res.status(200).json({
      success: true,
      currentLocation,
      previousLocation,
      availableCountries: ['NP', 'IT', 'RU'] // These are the countries monitored by the backend
    });
  } else {
    res.status(405).json({ success: false, message: 'Method not allowed' });
  }
}
