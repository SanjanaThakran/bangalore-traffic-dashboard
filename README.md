# 🚦 Bangalore Real-Time Traffic Dashboard

An interactive **Streamlit** web application designed to monitor, visualize, and analyze real-time traffic congestion, speed trends, and bottleneck corridors across major Bengaluru transit hot spots (Silk Board, Outer Ring Road, Hebbal, Whitefield, Electronic City, and more).

---

## 📌 Key Features

- 🚦 **Live Congestion Monitoring**: Real-time traffic congestion index and average speed updates across high-density Bengaluru corridors.
- 🗺️ **Interactive Geospatial Maps**: Dynamic maps displaying color-coded traffic bottlenecks (Red: Heavy Congestion, Yellow: Moderate, Green: Smooth Flow).
- 📊 **Peak Hour Analytics**: Historical & time-series analysis comparing morning vs. evening peak-hour delays.
- ⚡ **Hotspot & Bottleneck Identification**: Automated detection of severe delay zones (e.g., Silk Board Junction, Tin Factory, KR Puram, Hebbal Flyover, Marathahalli).
- ⏱️ **Dynamic Delay Estimator**: Calculate additional travel time and speed reductions compared to free-flow conditions.

---

## 🛠️ Tech Stack

| Category | Technologies |
| :--- | :--- |
| **Frontend & UI** | Streamlit |
| **Data Visualization** | Plotly Express, Folium, Pydeck |
| **Data Processing** | Python, Pandas, NumPy, GeoPandas |
| **Dependencies** | Listed in `requirements.txt` |

---

## 📂 Repository Structure

```
bangalore-traffic-dashboard/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## 🚀 How to Run

### 1. Install Dependencies
On macOS, use `pip3` or `python3 -m pip`:
```bash
pip3 install -r requirements.txt
```

### 2. Launch the Streamlit App
```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

## 👤 Author

**Sanjana Thakran**  
GitHub: [@SanjanaThakran](https://github.com/SanjanaThakran)
