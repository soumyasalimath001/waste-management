import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import plotly.express as px
import plotly.graph_objects as go

# Import custom modules
from modules.data_simulator import BinDataSimulator
from modules.route_optimizer import RouteOptimizer
from modules.visualization import MapVisualizer, ChartVisualizer
from modules.ml_models import FillLevelPredictor
from config import config

# Import OSM data fetcher - CORRECTED for osm_data_fetcher.py
from utils.osm_data_fetcher import OSMDataFetcher

# Alias for compatibility with code that expects OSMWasteFetcher
OSMWasteFetcher = OSMDataFetcher

# Page configuration
st.set_page_config(
    page_title="Waste Route Optimization Agent",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2ecc71;
        text-align: center;
        margin-bottom: 1rem;
        animation: fadeIn 1.5s ease-in;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .success-text {
        color: #2ecc71;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .warning-text {
        color: #f39c12;
        font-weight: bold;
    }
    .danger-text {
        color: #e74c3c;
        font-weight: bold;
    }
    .info-box {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #2ecc71;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 5px 15px rgba(46, 204, 113, 0.3);
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'simulator' not in st.session_state:
    st.session_state.simulator = BinDataSimulator(num_bins=50)

if 'optimizer' not in st.session_state:
    st.session_state.optimizer = RouteOptimizer(use_ors_api=False)

if 'current_bins' not in st.session_state:
    st.session_state.current_bins = st.session_state.simulator.simulate_fill_levels()

if 'optimization_history' not in st.session_state:
    st.session_state.optimization_history = []

if 'osm_fetcher' not in st.session_state:
    st.session_state.osm_fetcher = OSMDataFetcher()

if 'data_source' not in st.session_state:
    st.session_state.data_source = "Simulated Data"

# Header with animation
st.markdown("<h1 class='main-header'>🚛 Waste Route Optimization Agent</h1>", 
            unsafe_allow_html=True)
st.markdown("### AI-Powered Smart Waste Collection for Sustainable Cities 🌱")

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/waste--v1.png", width=100)
    st.title("Controls")
    
    # Data Source Selection
    st.subheader("📊 Data Source")
    data_source = st.radio(
        "Choose data source:",
        ["Simulated Data", "OpenStreetMap (Real)", "Upload CSV"],
        index=0
    )
    
    if data_source == "OpenStreetMap (Real)":
        st.session_state.data_source = "OSM Real Data"
        st.info("🌍 Fetching real bin data from OpenStreetMap")
        
        # City input for OSM data
        city_name = st.text_input("Enter city name", "Paris, France")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Fetch Bins", use_container_width=True):
                with st.spinner(f"Fetching waste bins from {city_name}..."):
                    city_info = st.session_state.osm_fetcher.geocode_city(city_name)
                    
                    if city_info:
                        real_bins = st.session_state.osm_fetcher.fetch_waste_bins(city_info['bbox'])
                        
                        if len(real_bins) > 0:
                            # Simulate fill levels for real bins
                            real_bins['fill_percentage'] = np.random.uniform(20, 90, len(real_bins))
                            real_bins['needs_collection'] = real_bins['fill_percentage'] >= 80
                            real_bins['fill_level_kg'] = (real_bins['fill_percentage'] / 100) * real_bins['capacity']
                            
                            # Add required columns if missing
                            if 'zone' not in real_bins.columns:
                                real_bins['zone'] = 'Unknown'
                            if 'bin_type' not in real_bins.columns:
                                real_bins['bin_type'] = real_bins.get('amenity', 'General')
                            
                            st.session_state.current_bins = real_bins
                            st.success(f"✅ Found {len(real_bins)} real bins in {city_name}!")
                        else:
                            st.warning(f"No bins found in {city_name}. Try a different city.")
                    else:
                        st.error(f"Could not find city: {city_name}")
        
        with col2:
            st.info("Try: Paris, London, Berlin, Amsterdam")
    
    elif data_source == "Upload CSV":
        st.session_state.data_source = "Custom CSV"
        uploaded_file = st.file_uploader("Upload bin locations CSV", type=['csv'])
        if uploaded_file is not None:
            try:
                custom_bins = pd.read_csv(uploaded_file)
                required_cols = ['bin_id', 'latitude', 'longitude']
                if all(col in custom_bins.columns for col in required_cols):
                    # Add capacity if missing
                    if 'capacity' not in custom_bins.columns:
                        custom_bins['capacity'] = 100
                    
                    custom_bins['fill_percentage'] = np.random.uniform(20, 90, len(custom_bins))
                    custom_bins['needs_collection'] = custom_bins['fill_percentage'] >= 80
                    custom_bins['fill_level_kg'] = (custom_bins['fill_percentage'] / 100) * custom_bins['capacity']
                    
                    # Add zone if missing
                    if 'zone' not in custom_bins.columns:
                        custom_bins['zone'] = 'Unknown'
                    if 'bin_type' not in custom_bins.columns:
                        custom_bins['bin_type'] = 'General'
                    
                    st.session_state.current_bins = custom_bins
                    st.success(f"✅ Loaded {len(custom_bins)} bins from CSV!")
                else:
                    st.error(f"CSV must contain columns: {required_cols}")
            except Exception as e:
                st.error(f"Error loading CSV: {e}")
    
    st.markdown("---")
    
    # Simulation parameters (only show for simulated data)
    if data_source == "Simulated Data":
        st.subheader("⚙️ Simulation Settings")
        num_bins = st.slider("Number of Bins", 10, 100, 50, 10)
        
        if st.button("🔄 Regenerate Bins", use_container_width=True):
            st.session_state.simulator = BinDataSimulator(num_bins=num_bins)
            st.session_state.current_bins = st.session_state.simulator.simulate_fill_levels()
            st.success("Bins regenerated!")
    
    # Time simulation (works for all data types)
    st.subheader("⏰ Time Settings")
    current_hour = st.slider("Simulate Time of Day", 0, 23, datetime.now().hour)
    
    if st.button("🕒 Update Fill Levels", use_container_width=True):
        with st.spinner("Updating bin data..."):
            if data_source == "Simulated Data":
                st.session_state.current_bins = st.session_state.simulator.simulate_fill_levels(
                    time_of_day=current_hour
                )
            else:
                # For real data, just add some variation based on time
                df = st.session_state.current_bins.copy()
                # Add time-based variation
                time_factor = 1 + (0.2 * np.sin(current_hour * np.pi / 12))
                df['fill_percentage'] = np.clip(df['fill_percentage'] * time_factor, 0, 100)
                df['needs_collection'] = df['fill_percentage'] >= 80
                df['fill_level_kg'] = (df['fill_percentage'] / 100) * df['capacity']
                st.session_state.current_bins = df
        st.success(f"Updated for {current_hour}:00")
    
    # Route optimization settings
    st.subheader("🚚 Route Settings")
    num_trucks = st.number_input("Number of Trucks", 1, 5, 2)
    use_ml = st.checkbox("Use ML Predictions", value=False)
    
    # API configuration
    st.subheader("🔑 API Configuration")
    use_real_routing = st.checkbox("Use Real Road Networks", value=False)
    if use_real_routing:
        api_key = st.text_input("OpenRouteService API Key", type="password")
        if api_key:
            config.OPENROUTESERVICE_API_KEY = api_key
            st.session_state.optimizer = RouteOptimizer(use_ors_api=True)
            st.success("API Key configured!")
    
    st.markdown("---")
    
    # Current stats
    st.markdown("### 📊 Current Stats")
    bins_needing = st.session_state.current_bins['needs_collection'].sum()
    total_bins = len(st.session_state.current_bins)
    avg_fill = st.session_state.current_bins['fill_percentage'].mean()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Bins", total_bins)
        st.metric("Avg Fill", f"{avg_fill:.1f}%")
    with col2:
        st.metric("Need Collection", f"{bins_needing}/{total_bins}")
        st.metric("Data Source", st.session_state.data_source.split()[0])
    
    # Data source indicator
    if "OSM" in st.session_state.data_source:
        st.markdown("""
        <div style='background-color: #d4edda; padding: 10px; border-radius: 5px; text-align: center;'>
            🌍 <b>Using Real OSM Data</b><br>
            <small>© OpenStreetMap contributors</small>
        </div>
        """, unsafe_allow_html=True)

# Main content area - Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Route Optimization", 
    "📈 Analytics", 
    "🤖 ML Predictions",
    "📋 Reports",
    "🌍 OSM Data Explorer"
])

# Tab 1: Route Optimization
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Optimized Collection Routes")
        
        # Create map
        map_viz = MapVisualizer()
        if len(st.session_state.current_bins) > 0:
            center_lat = st.session_state.current_bins['latitude'].mean()
            center_lon = st.session_state.current_bins['longitude'].mean()
        else:
            center_lat, center_lon = 30.7333, 76.7794
            
        map_viz.create_base_map(center_lat, center_lon)
        
        # Add bin markers
        map_viz.add_bin_markers(st.session_state.current_bins)
        
        # Run optimization button
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            if st.button("🚀 Generate Optimal Routes", type="primary", use_container_width=True):
                with st.spinner("Calculating optimal routes..."):
                    results = st.session_state.optimizer.optimize_with_constraints(
                        st.session_state.current_bins,
                        num_trucks=num_trucks
                    )
                    
                    # Add routes to map
                    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c', '#f39c12']
                    for i, route in enumerate(results['routes']):
                        color = colors[i % len(colors)]
                        map_viz.add_route(route['points'], color=color, truck_id=i)
                    
                    # Store results
                    st.session_state.last_optimization = results
                    st.session_state.optimization_history.append({
                        'timestamp': datetime.now(),
                        'bins_collected': results['bins_collected'],
                        'total_distance': results['total_distance'],
                        'num_routes': len(results['routes'])
                    })
                    
                    st.success(f"✅ Optimized {len(results['routes'])} routes covering {results['bins_collected']} bins")
        
        with col_opt2:
            if st.button("🗑️ Clear Routes", use_container_width=True):
                if 'last_optimization' in st.session_state:
                    del st.session_state.last_optimization
                st.rerun()
        
        # Display map
        map_viz.render()
    
    with col2:
        st.subheader("Route Summary")
        
        if 'last_optimization' in st.session_state:
            results = st.session_state.last_optimization
            
            # Calculate savings
            if len(st.session_state.optimization_history) > 1:
                avg_distance = np.mean([h['total_distance'] for h in st.session_state.optimization_history[:-1]])
                savings = ((avg_distance - results['total_distance']) / avg_distance) * 100
            else:
                savings = 0
            
            st.markdown(f"""
            <div class='metric-card'>
                <h3>📊 Optimization Results</h3>
                <p style='font-size: 2rem; margin: 0;'>📦 {results['bins_collected']}</p>
                <p>Bins to collect</p>
                <hr style='background: rgba(255,255,255,0.2);'>
                <p>🚚 Trucks: <b>{len(results['routes'])}</b></p>
                <p>📏 Distance: <b>{results['total_distance']:.2f} km</b></p>
                <p>⏱️ Est. time: <b>{results['total_distance']/30:.1f} hours</b></p>
                <p>💰 Fuel saved: <b>{results['total_distance']*0.3:.1f} L</b></p>
                <p>🌲 CO₂ reduced: <b>{(results['total_distance']*0.3*2.68):.1f} kg</b></p>
                <hr style='background: rgba(255,255,255,0.2);'>
                <p class='success-text'>📈 {savings:.1f}% improvement vs average</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Individual route details
            st.markdown("### 🚛 Route Details")
            for i, route in enumerate(results['routes']):
                with st.expander(f"Truck {route['truck_id'] + 1} Route"):
                    st.markdown(f"""
                    - **Bins:** {route['bins_collected']}
                    - **Distance:** {route['distance_km']:.2f} km
                    - **Est. time:** {route['distance_km']/30:.1f} hours
                    """)
        else:
            st.info("👆 Click 'Generate Optimal Routes' to start optimization")
            st.markdown("""
            <div class='info-box'>
                <b>💡 Tip:</b> The optimizer will create efficient routes based on:
                <ul>
                    <li>Bin fill levels</li>
                    <li>Distance between bins</li>
                    <li>Truck capacity</li>
                    <li>Time of day</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

# Tab 2: Analytics
with tab2:
    st.subheader("Waste Collection Analytics")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    avg_fill = st.session_state.current_bins['fill_percentage'].mean()
    total_waste = st.session_state.current_bins['fill_level_kg'].sum()
    bins_over_80 = (st.session_state.current_bins['fill_percentage'] >= 80).sum()
    urgent_percent = (bins_over_80 / len(st.session_state.current_bins)) * 100
    
    with col1:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #3498db, #2980b9); padding: 1rem; border-radius: 10px; text-align: center; color: white;'>
            <h3>📊 Avg Fill</h3>
            <h2>{avg_fill:.1f}%</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #e74c3c, #c0392b); padding: 1rem; border-radius: 10px; text-align: center; color: white;'>
            <h3>🗑️ Total Waste</h3>
            <h2>{total_waste:.0f} kg</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #f39c12, #d35400); padding: 1rem; border-radius: 10px; text-align: center; color: white;'>
            <h3>⚠️ Critical Bins</h3>
            <h2>{bins_over_80}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #2ecc71, #27ae60); padding: 1rem; border-radius: 10px; text-align: center; color: white;'>
            <h3>🎯 Urgency</h3>
            <h2>{urgent_percent:.1f}%</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Fill level distribution
        fig = px.histogram(
            st.session_state.current_bins,
            x='fill_percentage',
            nbins=20,
            title='📊 Fill Level Distribution',
            labels={'fill_percentage': 'Fill %', 'count': 'Number of Bins'},
            color_discrete_sequence=['#3498db']
        )
        fig.add_vline(x=80, line_dash="dash", line_color="red", 
                     annotation_text="Collection Threshold")
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Zone analysis (if zone column exists)
        if 'zone' in st.session_state.current_bins.columns:
            zone_stats = st.session_state.current_bins.groupby('zone').agg({
                'fill_percentage': 'mean',
                'bin_id': 'count'
            }).round(1).reset_index()
            
            fig = px.bar(
                zone_stats,
                x='zone',
                y='fill_percentage',
                color='bin_id',
                title='🏘️ Average Fill Level by Zone',
                labels={'fill_percentage': 'Avg Fill %', 'zone': 'Zone', 'bin_id': 'Count'},
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Additional charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Top 10 fullest bins
        top_bins = st.session_state.current_bins.nlargest(10, 'fill_percentage')[['bin_id', 'fill_percentage']]
        fig = px.bar(
            top_bins,
            x='bin_id',
            y='fill_percentage',
            title='🔥 Top 10 Fullest Bins',
            color='fill_percentage',
            color_continuous_scale=['green', 'yellow', 'red']
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Bin type distribution (if bin_type column exists)
        if 'bin_type' in st.session_state.current_bins.columns:
            type_counts = st.session_state.current_bins['bin_type'].value_counts()
            fig = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title='🗑️ Bin Type Distribution',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Optimization history
    if st.session_state.optimization_history:
        st.subheader("📈 Optimization History")
        history_df = pd.DataFrame(st.session_state.optimization_history)
        
        fig = px.line(
            history_df,
            x='timestamp',
            y=['bins_collected', 'total_distance'],
            title='Performance Over Time',
            labels={'value': 'Value', 'timestamp': 'Time', 'variable': 'Metric'}
        )
        st.plotly_chart(fig, use_container_width=True)

# Tab 3: ML Predictions
with tab3:
    st.subheader("🤖 ML-Based Fill Level Predictions")
    
    st.markdown("""
    <div class='info-box'>
        <b>🧠 Using Random Forest with SHAP explanations</b><br>
        Predict future fill levels based on historical patterns, time of day, and bin characteristics.
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 Train Prediction Model", type="primary", use_container_width=True):
            with st.spinner("Training model... This may take a moment"):
                # Generate historical data for training
                historical_data = []
                for hour in range(24):
                    df = st.session_state.simulator.simulate_fill_levels(time_of_day=hour)
                    df['timestamp'] = pd.Timestamp.now() - pd.Timedelta(hours=24-hour)
                    historical_data.append(df)
                
                historical_df = pd.concat(historical_data, ignore_index=True)
                
                # Train model
                predictor = FillLevelPredictor()
                results = predictor.train(historical_df)
                
                st.success("✅ Model trained successfully!")
                
                # Display metrics
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("Train R² Score", f"{results['train_score']:.3f}")
                with col_m2:
                    st.metric("Test R² Score", f"{results['test_score']:.3f}")
                
                # Store predictor in session state
                st.session_state.predictor = predictor
    
    with col2:
        st.markdown("""
        ### 📊 Features Used
        - Time of day
        - Day of week
        - Zone type
        - Bin type
        - Historical fill rates
        - Weather conditions
        """)
    
    # Prediction interface
    if 'predictor' in st.session_state:
        st.markdown("---")
        st.subheader("🔮 Make Predictions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_bin = st.selectbox(
                "Select Bin ID",
                options=st.session_state.current_bins['bin_id'].tolist()
            )
        
        with col2:
            hours_ahead = st.slider("Hours Ahead", 1, 48, 24)
        
        with col3:
            if st.button("Predict", use_container_width=True):
                bin_data = st.session_state.current_bins[
                    st.session_state.current_bins['bin_id'] == selected_bin
                ].iloc[0]
                
                # Simple prediction logic (replace with actual model prediction)
                current_fill = bin_data['fill_percentage']
                hourly_rate = np.random.uniform(1, 3)  # percent per hour
                predicted_fill = min(100, current_fill + (hourly_rate * hours_ahead))
                
                # Display prediction
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #667eea, #764ba2); padding: 2rem; border-radius: 15px; text-align: center; color: white;'>
                    <h3>📊 Prediction for {selected_bin}</h3>
                    <h1 style='font-size: 3rem;'>{predicted_fill:.1f}%</h1>
                    <p>in {hours_ahead} hours</p>
                    <p>Current: {current_fill:.1f}% | Change: +{predicted_fill - current_fill:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)

# Tab 4: Reports
with tab4:
    st.subheader("📋 Reports & Data Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📥 Download Reports")
        
        # Report type selection
        report_type = st.selectbox(
            "Select Report Type",
            ["Current Bin Status", "Optimization Summary", "Historical Analysis", "Environmental Impact"]
        )
        
        # Format selection
        file_format = st.radio("File Format", ["CSV", "JSON", "Excel"])
        
        if st.button("📊 Generate Report", use_container_width=True):
            if report_type == "Current Bin Status":
                data = st.session_state.current_bins
                filename = f"bin_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            elif report_type == "Optimization Summary" and 'last_optimization' in st.session_state:
                data = pd.DataFrame([st.session_state.last_optimization])
                filename = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else:
                data = pd.DataFrame(st.session_state.optimization_history)
                filename = f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if file_format == "CSV":
                csv = data.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"{filename}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            elif file_format == "JSON":
                json_str = data.to_json(orient='records')
                st.download_button(
                    label="📥 Download JSON",
                    data=json_str,
                    file_name=f"{filename}.json",
                    mime="application/json",
                    use_container_width=True
                )
    
    with col2:
        st.markdown("### 📊 Summary Statistics")
        
        # Generate summary statistics
        total_bins = len(st.session_state.current_bins)
        avg_fill = st.session_state.current_bins['fill_percentage'].mean()
        total_waste = st.session_state.current_bins['fill_level_kg'].sum()
        
        st.markdown(f"""
        <div style='background-color: #f8f9fa; padding: 1.5rem; border-radius: 10px;'>
            <h4>📈 System Overview</h4>
            <table style='width: 100%;'>
                <tr><td>Total Bins:</td><td><b>{total_bins}</b></td></tr>
                <tr><td>Average Fill:</td><td><b>{avg_fill:.1f}%</b></td></tr>
                <tr><td>Total Waste:</td><td><b>{total_waste:.0f} kg</b></td></tr>
                <tr><td>Bins Needing Collection:</td><td><b>{(st.session_state.current_bins['needs_collection']).sum()}</b></td></tr>
                <tr><td>Data Source:</td><td><b>{st.session_state.data_source}</b></td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.optimization_history:
            st.markdown("### 🏆 Environmental Impact")
            total_distance = sum(h['total_distance'] for h in st.session_state.optimization_history)
            total_fuel_saved = total_distance * 0.3  # 0.3L per km saved
            total_co2_reduced = total_fuel_saved * 2.68  # kg CO2 per L diesel
            
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #27ae60, #2ecc71); padding: 1.5rem; border-radius: 10px; color: white;'>
                <h4>🌍 Total Impact</h4>
                <p>📏 Distance Optimized: <b>{total_distance:.0f} km</b></p>
                <p>⛽ Fuel Saved: <b>{total_fuel_saved:.0f} L</b></p>
                <p>🌲 CO₂ Reduced: <b>{total_co2_reduced:.0f} kg</b></p>
                <p>🌳 Equivalent to planting <b>{total_co2_reduced/21:.0f}</b> trees</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Current data preview
    st.markdown("---")
    st.subheader("📋 Current Data Preview")
    st.dataframe(
        st.session_state.current_bins,
        use_container_width=True,
        height=300
    )

# Tab 5: OSM Data Explorer
with tab5:
    st.subheader("🌍 OpenStreetMap Waste Bin Explorer")
    
    st.markdown("""
    <div class='info-box'>
        <b>🌐 Fetch real waste bin data from any city in the world!</b><br>
        Data sourced from OpenStreetMap contributors. Includes waste baskets, recycling containers, and public bins.
    </div>
    """, unsafe_allow_html=True)
    
    # Simple OSM Explorer without requiring render_osm_fetcher
    col1, col2 = st.columns([2, 1])
    
    with col1:
        city = st.text_input("Enter city name", "Paris, France", key="osm_city")
        
        if st.button("🔍 Find Bins", use_container_width=True):
            with st.spinner(f"Searching for bins in {city}..."):
                city_info = st.session_state.osm_fetcher.geocode_city(city)
                
                if city_info:
                    st.success(f"📍 Found: {city_info.get('display_name', city)}")
                    
                    bins_df = st.session_state.osm_fetcher.fetch_waste_bins(city_info['bbox'])
                    
                    if len(bins_df) > 0:
                        st.session_state['osm_explorer_data'] = bins_df
                        
                        # Display metrics
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Bins", len(bins_df))
                        
                        waste_count = len(bins_df[bins_df['amenity'] == 'waste_basket']) if 'amenity' in bins_df.columns else 0
                        m2.metric("Waste Baskets", waste_count)
                        
                        recycling_count = len(bins_df[bins_df['amenity'] == 'recycling']) if 'amenity' in bins_df.columns else 0
                        m3.metric("Recycling", recycling_count)
                        
                        # Show map preview
                        st.map(bins_df[['latitude', 'longitude']])
                        
                        # Show data table
                        with st.expander("View Raw Data"):
                            st.dataframe(bins_df)
                        
                        # Use this data button
                        if st.button("🚛 Use This Data for Optimization", use_container_width=True):
                            # Add simulation fields
                            bins_df['fill_percentage'] = np.random.uniform(20, 90, len(bins_df))
                            bins_df['needs_collection'] = bins_df['fill_percentage'] >= 80
                            bins_df['fill_level_kg'] = (bins_df['fill_percentage'] / 100) * bins_df['capacity']
                            bins_df['zone'] = bins_df.get('zone', 'Unknown')
                            bins_df['bin_type'] = bins_df.get('amenity', 'General')
                            
                            st.session_state.current_bins = bins_df
                            st.session_state.data_source = f"OSM: {city}"
                            st.success(f"✅ Loaded {len(bins_df)} real bins from {city}!")
                    else:
                        st.warning(f"No bins found in {city}. Try a different city.")
                else:
                    st.error(f"Could not find city: {city}")
    
    with col2:
        st.markdown("""
        ### 💡 Tips
        - Try: Paris, London, Berlin, Amsterdam
        - European cities have best coverage
        - Data updates monthly
        
        ### 📝 License
        Data © OpenStreetMap contributors
        """)
    
    # Show saved OSM data if available
    if 'osm_explorer_data' in st.session_state:
        st.markdown("---")
        st.subheader("📊 Last Fetched Data Statistics")
        bins_df = st.session_state.osm_explorer_data
        
        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            if 'amenity' in bins_df.columns:
                type_counts = bins_df['amenity'].value_counts()
                fig = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title='Bin Type Distribution'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col_s2:
            if 'material' in bins_df.columns:
                material_counts = bins_df['material'].value_counts().head(5)
                if len(material_counts) > 0:
                    fig = px.bar(
                        x=material_counts.values,
                        y=material_counts.index,
                        orientation='h',
                        title='Top Materials',
                        labels={'x': 'Count', 'y': 'Material'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>Built with 🚛 using Streamlit • AI-Powered Waste Management • OpenStreetMap Integration</p>
    <p>Project #36 — Waste Route Optimization Agent | Agentic AI / Smart Cities</p>
    <p style='font-size: 0.8rem;'>© OpenStreetMap contributors. Data available under the Open Database License.</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh for real-time simulation (optional)
if st.sidebar.checkbox("🔄 Auto-refresh (every 30s)"):
    time.sleep(30)
    st.rerun()