# patara-research-platform
# Patara Scientific Data Platform (PSDP) 🐢

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)
![GUI](https://img.shields.io/badge/GUI-PyQt6-green?style=flat-square)
![GIS](https://img.shields.io/badge/GIS-Folium%20%7C%20GeoPandas-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-v1.3%20(Stable)-success?style=flat-square)

**Patara Scientific Data Platform** is a comprehensive desktop application designed for the geospatial analysis, management, and simulation of *Caretta caretta* (Loggerhead Sea Turtle) nesting data at Patara Beach.

Developed to support academic research, this platform integrates a robust **SQL database** with an interactive **GIS interface**, enabling researchers to visualize nesting patterns, simulate ecological scenarios, and generate statistical reports.

---

## 🚀 Key Features

### 🗺️ Advanced Geospatial Analysis
*   **Interactive Mapping:** Embedded Leaflet maps (via Folium) within the PyQt6 interface using `QWebChannel` for bi-directional communication.
*   **Spatial Filtering:** Draw polygons on the map to filter data dynamically based on geographic boundaries.
*   **Heatmaps:** Visualize nesting density and predation hotspots.
*   **Clustering:** Smart marker clustering for handling large datasets efficiently.

### 📊 Data Management & Analytics
*   **ETL Capabilities:** Batch import/export functionality for Excel files with automatic schema validation.
*   **Statistical Reporting:** One-click generation of PDF reports summarizing nesting success, incubation periods, and predation rates.
*   **Comparative Analysis:** Compare datasets across different years to track population trends.

### 🧪 Ecological Simulation
*   **Scenario Modeling:** Run simulations to predict the impact of environmental changes or conservation strategies (e.g., "What if predation increases by 20% in Zone A?").
*   **Impact Assessment:** Determine affected nests based on proximity to specific landmarks using geospatial buffering.

---

## 🛠 Technical Architecture

The application is built using a modular architecture:

*   **Core:** Python 3.10+
*   **GUI Framework:** PyQt6 (QtWebEngine for map rendering).
*   **Database:** SQLite (with automated backup system).
*   **GIS Engine:** Folium, GeoPandas, Shapely.
*   **Data Processing:** Pandas, NumPy.
*   **Reporting:** ReportLab (PDF), Matplotlib (Charts).

### Code Structure
*   `patara.py`: Main entry point and GUI logic.
*   `config.json`: Configuration for fixed coordinates and legends.
*   `MapCommunicator`: Custom class handling JS-to-Python communication for drawing tools.

---

## 📸 Screenshots

*(Place screenshots of the application here. Ideally show the Map View, the Statistics Dialog, and the Simulation Tool)*

---

## ⚙️ Installation & Usage

### Prerequisites
*   Python 3.10 or higher.
*   Recommended: A virtual environment.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/patara-data-platform.git
cd patara-data-platform

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Run the Application
python patara.py
