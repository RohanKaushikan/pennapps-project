# 🚀 Quick Web Testing Guide
## Travel Legal App - 5 Minute Demo Test

### **🌐 App is Live at: http://localhost:3000**

---

## **⚡ Quick Test Checklist (5 minutes)**

### **1. 🔍 Basic Functionality Test (1 min)**
- [ ] **Open the app** - Should see background monitoring screen
- [ ] **Check countries dropdown** - Should show Nepal 🇳🇵, Italy 🇮🇹, Russia 🇷🇺
- [ ] **View alerts tab** - Should show current anomalies
- [ ] **Verify anomaly detection** - Nepal should show 31x spike, Italy 2.93x spike

### **2. 🎮 Demo Mode Test (1 min)**
- [ ] **Press 'D' key 3 times quickly** - Demo panel should appear
- [ ] **Click "Travel to Nepal"** - Should trigger location change
- [ ] **Check for notifications** - Browser notification should appear
- [ ] **View location alerts** - Alert overlay should show

### **3. 🧠 ML Intelligence Test (2 min)**
- [ ] **Click "Enhanced View" button** - Should switch to ML-powered mode
- [ ] **Check intelligence overlays** - Alerts should show risk scores, urgency levels
- [ ] **Test filters** - Try "Critical Only", "Legal Requirements", "Urgent Only"
- [ ] **Open Intelligence Panel** - Click "🧠 Intelligence Panel +"
- [ ] **Check compliance checklist** - Click "✅ Compliance Checklist +"

### **4. 🎯 Advanced Features Test (1 min)**
- [ ] **Test country switching** - Change between Nepal, Italy, Russia
- [ ] **Verify performance** - All switches should be instant
- [ ] **Check fallback** - Toggle back to "Standard View"
- [ ] **Test responsiveness** - Resize browser window

---

## **🎯 Expected Results**

### **Current Live Data (as of testing):**
- **🚨 Nepal**: 31x spike factor (Gen-Z protests, travel advisories)
- **⚠️ Italy**: 2.93x spike factor (Guinea warnings, Ecuador advisories)  
- **✅ Russia**: Normal activity

### **ML Intelligence Features:**
- **Risk Scores**: 0-100 scale with color coding
- **Urgency Levels**: Immediate, Urgent, Moderate, Low
- **Legal Categories**: Mandatory, Prohibited, Recommended, Mixed
- **Document Requirements**: Auto-extracted from news content
- **Compliance Deadlines**: Time-sensitive requirements

---

## **🐛 Troubleshooting**

### **If something doesn't work:**

1. **No alerts showing?**
   ```bash
   curl http://localhost:8000/api/anomalies
   ```
   Should return JSON with 3 countries

2. **Enhanced view not loading?**
   ```bash
   curl http://localhost:8000/api/alerts/NP/enhanced
   ```
   Should return array of enhanced alerts

3. **Demo mode not working?**
   - Make sure you press 'D' exactly 3 times within 2 seconds
   - Check browser console for any JavaScript errors

4. **Backend not responding?**
   ```bash
   curl http://localhost:8000/
   ```
   Should return: `{"status":"healthy","message":"Travel News Anomaly Detection API is running!","data_points":368}`

---

## **🎬 Demo Script (30 seconds)**

### **For presentations:**

1. **"This is our Travel Legal app with ML intelligence"**
   - Show the clean interface

2. **"Let me demonstrate the core functionality"**
   - Press D-D-D to open demo panel
   - Click "Travel to Nepal"

3. **"Notice the real-time anomaly detection"**
   - Point out the 31x spike factor
   - Show real news headlines

4. **"Now let's see the ML intelligence"**
   - Click "Enhanced View"
   - Show risk scores and intelligence overlays

5. **"The system provides legal analysis and compliance insights"**
   - Open Intelligence Panel
   - Show compliance checklist

6. **"All while maintaining the original functionality"**
   - Toggle back to Standard View
   - Show seamless fallback

---

## **📊 Performance Expectations**

- **Page Load**: < 2 seconds
- **Country Switch**: < 500ms
- **Enhanced View Toggle**: < 1 second
- **Demo Mode Activation**: Instant
- **API Responses**: < 50ms (visible in Network tab)

---

## **🎉 Success Indicators**

✅ **App loads without errors**
✅ **Real data shows current anomalies** 
✅ **Demo mode works (D-D-D)**
✅ **Enhanced view shows ML intelligence**
✅ **Filters and panels work**
✅ **Performance is smooth**
✅ **Fallbacks work gracefully**

---

**🚀 Ready to demo! The app showcases both original functionality and enhanced ML intelligence seamlessly.**
