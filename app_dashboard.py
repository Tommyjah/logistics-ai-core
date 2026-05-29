import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta

# --- INITIALIZE DATABASE CONNECTION ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

if "df_pred" not in st.session_state:
    st.session_state.df_pred = None

st.set_page_config(page_title="NGO Fleet Intelligence", layout="wide")
st.title("🚛 Fleet Budgeting & Predictive Intelligence")

tab1, tab2, tab3, tab4 = st.tabs([
    "Budget Simulation", 
    "Fleet Assistant & Controls", 
    "Maintenance Forecast", 
    "Fuel Analytics"
])

# ------------------------------------------------------------------
# TAB 1: FINANCIAL PREDICTIVE SIMULATOR
# (Ported from @app.post("/analyze-fleet"))
# ------------------------------------------------------------------
with tab1:
    st.header("Financial Predictive Simulator")
    col_input1, col_input2 = st.columns(2)
    input_km = col_input1.number_input("Target KM Driven", min_value=0.0, value=3500.0)
    input_days = col_input2.slider("Days in Workshop", 0, 30, 12)

    if st.button("Run Detailed Simulation"):
        try:
            # Replicating the exact math from api_server.py
            rates = {"a": 45.0, "b": 38.0}
            penalties = {"a": 1500.0, "b": 2200.0}
            
            fuel_a = input_km * rates["a"]
            downtime_a = input_days * penalties["a"]
            total_a = fuel_a + downtime_a
            
            fuel_b = input_km * rates["b"]
            downtime_b = input_days * penalties["b"]
            total_b = fuel_b + downtime_b
            
            diff = total_a - total_b
            
            a = {"fuel_component": fuel_a, "downtime_component": downtime_a, "total": total_a}
            b = {"fuel_component": fuel_b, "downtime_component": downtime_b, "total": total_b}

            st.subheader("💡 Financial Strategy Insight")
            if diff > 0:
                st.success(f"**Strategic Recommendation:** Premium Logistics (Scenario B) is more cost-efficient. Saving **{abs(diff):,.2f} ETB**.")
            else:
                st.info(f"**Strategic Recommendation:** Standard Logistics (Scenario A) is most economical. Preserves **{abs(diff):,.2f} ETB**.")

            st.subheader("📊 Fleet Operational Cost Forecast")
            c1, c2 = st.columns(2)
            
            def render_scenario(column, title, details):
                with column:
                    total = details.get('total', 0)
                    fuel = details.get('fuel_component', 0)
                    downtime = details.get('downtime_component', 0)
                    st.metric(title, f"{total:,.2f} ETB")
                    st.caption("Cost Breakdown:")
                    progress_val = fuel / total if total > 0 else 0
                    st.progress(progress_val)
                    st.write(f"• **Active Fuel Expense:** {fuel:,} ETB")
                    st.write(f"• **Downtime Penalty:** {downtime:,} ETB")

            render_scenario(c1, "Standard Logistics (A)", a)
            render_scenario(c2, "Premium/Rapid Logistics (B)", b)

            st.markdown("### Cost Composition Comparison")
            df = pd.DataFrame([a, b], index=["Standard", "Premium"])
            st.bar_chart(df[['fuel_component', 'downtime_component']])
        
        except Exception as e:
            st.error(f"Simulation failed: {e}")

# ------------------------------------------------------------------
# TAB 2: FLEET ASSISTANT & CONTROLS
# ------------------------------------------------------------------
with tab2:
    st.header("Fleet Assistant & Controls")
    
    # 1. Persistent Toast Notification Handler (With Balloons!)
    if "tab2_success_msg" in st.session_state and st.session_state.tab2_success_msg:
        st.success(st.session_state.tab2_success_msg)
        st.balloons()
        del st.session_state.tab2_success_msg

    # 2. Reusable Pipeline: Dynamic column discovery
    def refresh_inquiry_data(query_type):
        try:
            v_res = supabase.table("fleet_vehicles").select("*").execute().data
            d_res = supabase.table("drivers").select("*").execute().data
            
            df_v = pd.DataFrame(v_res) if v_res else pd.DataFrame()
            df_d = pd.DataFrame(d_res) if d_res else pd.DataFrame()
            
            if df_v.empty: return pd.DataFrame()
                
            if not df_d.empty:
                if 'full_name' in df_d.columns:
                    df_d['driver_name_clean'] = df_d['full_name'].fillna("Unknown")
                elif 'name' in df_d.columns:
                    df_d['driver_name_clean'] = df_d['name'].fillna("Unknown")
                else:
                    text_cols = df_d.select_dtypes(include=['object']).columns
                    df_d['driver_name_clean'] = df_d[text_cols[0]].fillna("Unknown") if len(text_cols) > 0 else "Driver " + df_d['id'].astype(str)
                
                df_merged = df_v.merge(df_d[['id', 'driver_name_clean']], left_on="current_driver_id", right_on="id", how="left")
                df_merged['assigned_driver'] = df_merged['driver_name_clean'].fillna("Unassigned")
            else:
                df_merged = df_v.copy()
                df_merged['assigned_driver'] = "Unassigned"
            
            # --- PATCH: Predictive Maintenance Logic ---
            df_merged['service_delta'] = df_merged['current_odometer'] - df_merged['last_service_odometer']
            df_merged['maintenance_alert'] = df_merged.apply(
                lambda row: "Overdue 🔴" if row['service_delta'] >= row['service_interval'] 
                else ("Warning 🟡" if row['service_delta'] >= (row['service_interval'] * 0.8) 
                else "Healthy 🟢"), axis=1
            )
            
            INSPECTION_STATUSES = ["Needs Inspection", "Under Maintenance", "bad"]
            if query_type in ["Vehicles in Workshop", "Active Maintenance Queue"]:
                df_merged = df_merged[df_merged['is_in_workshop'] == True]
            elif query_type == "Vehicles Needing Inspection":
                if 'condition_status' in df_merged.columns:
                    df_merged = df_merged[df_merged['condition_status'].isin(INSPECTION_STATUSES)]
                
            return df_merged
        except Exception as e:
            st.error(f"Data synchronization breakdown: {e}")
            return pd.DataFrame()

    # ---------------------------------
    # 2.5  Custodian Score
    # ---------------------------------
    def get_driver_scorecard():
        try:
            v_res = supabase.table("fleet_vehicles").select("*").execute().data
            d_res = supabase.table("drivers").select("*").execute().data
            if not v_res or not d_res: return pd.DataFrame()
            
            df_v = pd.DataFrame(v_res)
            df_d = pd.DataFrame(d_res)
            
            # Calculate delta
            df_v['delta'] = df_v['current_odometer'] - df_v['last_service_odometer']
            
            # Merge and Group
            df_merged = df_v.merge(df_d[['id', 'full_name']], left_on='current_driver_id', right_on='id', how='left')
            
            # Score calculation
            scorecard = df_merged.groupby('full_name')['delta'].mean().reset_index()
            scorecard.columns = ['Driver', 'Avg Maintenance Drift (km)']
            return scorecard.sort_values(by='Avg Maintenance Drift (km)')
        except Exception as e:
            return pd.DataFrame()

    # 3. AI Strategic Insight Layer 
    st.subheader("💡 AI Strategic Fleet Insight")
    ai_df = refresh_inquiry_data("List All Vehicles")
    if not ai_df.empty:
        # Maintenance Alert Logic
        overdue_count = (ai_df['service_delta'] >= ai_df['service_interval']).sum()
        if overdue_count > 0:
            st.warning(f"**Alert**: {overdue_count} vehicles require immediate maintenance.")
        
        workshop_count = ai_df['is_in_workshop'].sum()
        if workshop_count > (len(ai_df) * 0.25):
            st.warning("High workshop saturation detected. Prioritize inspection queue.")
        else:
            st.success("Fleet health is within optimal parameters.")
    st.markdown("---")

    col_read, col_write = st.columns([1, 1])

    # 4. LEFT COLUMN: INQUIRIES
    with col_read:
        st.subheader("📋 Fleet Inquiries")
        query = st.selectbox("What would you like to know?", 
                             ["List All Vehicles", "Vehicles in Workshop", "Vehicles Needing Inspection"],
                             key="tab2_query_choice")
        
        with st.spinner("Syncing fleet view..."):
            inquiry_df = refresh_inquiry_data(query)

        if inquiry_df is not None and not inquiry_df.empty:
            # Updated to show the new maintenance_alert column
            display_cols = ["plate_number", "maintenance_alert", "current_odometer", "is_in_workshop", "assigned_driver"]
            existing_cols = [c for c in display_cols if c in inquiry_df.columns]
            st.dataframe(inquiry_df[existing_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No vehicles match this query selection right now.")

    # 5. RIGHT COLUMN: WORKSHOP & CREW CONTROL
    with col_write:
        st.subheader("🔧 Workshop & Crew Control")
        raw_vehicles = supabase.table("fleet_vehicles").select("*").execute().data
        vehicle_lookup = {f"{r.get('plate_number')} ({r.get('project_assignment', '')})": r.get("id") for r in raw_vehicles}
        
        if vehicle_lookup:
            selected_label = st.selectbox("Select Vehicle", list(vehicle_lookup.keys()), key="tab2_vehicle_select")
            selected_id = vehicle_lookup[selected_label]
            v_rec = supabase.table("fleet_vehicles").select("*").eq("id", selected_id).execute().data[0]

            # Workshop Status
            status_choice = st.radio("Workshop Status:", ["Active in Fleet ✅", "Checked Into Workshop 🛠️"], 
                                     index=1 if v_rec.get("is_in_workshop") else 0, key=f"tab2_status_{selected_id}")
            if st.button("Commit Workshop Status", key="tab2_btn_workshop"):
                supabase.table("fleet_vehicles").update({"is_in_workshop": "Checked Into" in status_choice}).eq("id", selected_id).execute()
                st.session_state.tab2_success_msg = "Workshop status updated!"
                st.rerun()
            
            # --- PATCH: Maintenance Record Update ---
            st.markdown("---")
            st.markdown("**Update Service Record**")
            new_last_service = st.number_input("Last Service Odometer", value=int(v_rec.get("last_service_odometer", 0)), key=f"tab2_odo_{selected_id}")
            if st.button("Commit Service Update", key="tab2_btn_service"):
                supabase.table("fleet_vehicles").update({"last_service_odometer": new_last_service}).eq("id", selected_id).execute()
                st.session_state.tab2_success_msg = "Service records updated!"
                st.rerun()

            st.markdown("---")
            
            # Crew Assignment
            d_res = supabase.table("drivers").select("*").execute().data
            drivers_map = {f"{d.get('full_name', 'Driver ' + str(d['id']))}": d['id'] for d in d_res}
            sel_d = st.selectbox("Assign Driver", ["Unassigned"] + list(drivers_map.keys()), key=f"tab2_driver_{selected_id}")
            
            if st.button("Confirm Crew Assignment", key="tab2_btn_driver"):
                target_driver_id = drivers_map.get(sel_d)
                supabase.table("fleet_vehicles").update({"current_driver_id": target_driver_id}).eq("id", selected_id).execute()
                st.session_state.tab2_success_msg = "Crew assignment confirmed!"
                st.rerun()
        else:
            st.error("No valid vehicle entries found.")

# ------------------------------------------------------------------
# TAB 3: DYNAMIC MAINTENANCE PROJECTIONS (Polished Production Edition)
# ------------------------------------------------------------------
with tab3:
    st.header("🏆 Driver Custodian Scorecard")
    scorecard_df = get_driver_scorecard()
    if not scorecard_df.empty:
        # Clean trailing decimal points from the scorecard view
        st.dataframe(
            scorecard_df.style.format({"Avg Maintenance Drift (km)": "{:,.0f}"}), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Driver": "👤 Driver Name",
                "Avg Maintenance Drift (km)": st.column_config.NumberColumn("📊 Avg Maintenance Drift (KM)")
            }
        )
        st.info("💡 Drivers with a lower 'Avg Maintenance Drift' are effectively managing their vehicle service intervals.")
    else:
        st.warning("Scorecard data currently unavailable.")
        
    st.markdown("---") # Visual separator
    st.header("🗓️ Automated Service Projections")

    # PERSISTENT ALERT: Displays the confirmation after the page resets
    if "maintenance_success" in st.session_state and st.session_state.maintenance_success:
        st.success(st.session_state.maintenance_success)
        st.balloons()
        del st.session_state.maintenance_success  # Clear it so it won't show again on next actions
    
    # ADDED 'key' TO PREVENT DUPLICATE ELEMENT ERROR
    interval = st.selectbox(
        "Select Target Service Interval (KM)", 
        [5000, 10000], 
        index=0, 
        key="maintenance_interval_select" 
    )
    
    if st.button("Generate Maintenance Timeline"):
        try:
            # 1. Fetch data
            v_data = supabase.table("fleet_vehicles").select("id, plate_number, current_odometer").execute().data
            fuel_logs = supabase.table("fleet_fuel_logs").select("vehicle_id, odometer_reading, fuel_date").execute().data
            df_fuel = pd.DataFrame(fuel_logs)
            if not df_fuel.empty:
                df_fuel['fuel_date'] = pd.to_datetime(df_fuel['fuel_date'])
            
            pred_list = []
            today = datetime.now()
            
            for v in v_data:
                # Dynamic Usage Calculation
                vehicle_history = df_fuel[df_fuel['vehicle_id'] == v['id']].sort_values('fuel_date') if not df_fuel.empty else pd.DataFrame()
                if len(vehicle_history) >= 2:
                    dist = vehicle_history['odometer_reading'].iloc[-1] - vehicle_history['odometer_reading'].iloc[0]
                    days = (vehicle_history['fuel_date'].iloc[-1] - vehicle_history['fuel_date'].iloc[0]).days
                    daily_avg = max(dist / days, 1) if days > 0 else 50
                else:
                    daily_avg = 50
                
                curr_odo = v.get("current_odometer") or 0
                remaining = interval - (curr_odo % interval)
                
                # Calculate Estimated Maintenance Date
                days_until = int(remaining / daily_avg) if remaining > 0 else 0
                est_date = (today + timedelta(days=days_until)).strftime("%Y-%m-%d")
                
                pred_list.append({
                    "plate_number": v["plate_number"],
                    "maintenance_due_date": est_date,
                    "km_remaining": remaining,
                    "daily_usage_avg": round(daily_avg, 1)
                })
            
            st.session_state.df_pred = pd.DataFrame(pred_list).sort_values('km_remaining')
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    # 2. RESTORED DISPLAY & STYLING WITH SELECTION
    if "df_pred" in st.session_state and st.session_state.df_pred is not None:
        df_display = st.session_state.df_pred
        
        # Color coding logic
        def color_urgency(val):
            if val < 500: return 'background-color: #ff4b4b; color: white'
            if val < 1500: return 'background-color: #ffa500; color: black'
            return 'background-color: #2e7d32; color: white'

        st.subheader("Upcoming Maintenance Schedule")
        st.write("📋 *Check the boxes on the left side of the table rows to select vehicles for maintenance.*")
        
        # Chained .format() onto your .map() engine to scrub trailing floats cleanly
        selection_event = st.dataframe(
            df_display.style.map(color_urgency, subset=['km_remaining'])
                            .format({
                                "km_remaining": "{:,.0f}",
                                "daily_usage_avg": "{:,.1f}"
                            }),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            column_config={
                "plate_number": "🚛 Plate Number",
                "maintenance_due_date": "📅 Est. Maintenance Date",
                "km_remaining": st.column_config.NumberColumn("⚠️ KM Until Service"),
                "daily_usage_avg": st.column_config.NumberColumn("📊 Avg Daily KM")
            }
        )
        
        st.divider()
        st.subheader("🛠️ Take Action (Send to Maintenance)")
        
        # Extracted rows matching standard selection event object mapping
        selected_row_indices = selection_event.selection.rows
        
        if selected_row_indices:
            selected_plates = df_display.iloc[selected_row_indices]['plate_number'].unique().tolist()
            
            # Confirmation Area
            st.info(f"**Selected Vehicle Queue:** {', '.join(selected_plates)}")
            
            if st.button("Confirm: Send Selected Vehicles to Maintenance Workshop"):
                try:
                    for plate in selected_plates:
                        supabase.table("fleet_vehicles").update({"is_in_workshop": True}).eq("plate_number", plate).execute()
                    
                    # STAGE CONFIRMATION MESSAGE: Stored safely in session state before rerun
                    st.session_state.maintenance_success = f"Successfully registered {len(selected_plates)} vehicle(s) to Maintenance!"
                    st.session_state.df_pred = None  # Clear cache to force clean database fetch next time
                    st.rerun() 
                except Exception as e:
                    st.error(f"Failed to update database: {e}")
        else:
            st.warning("Please check the thin checkbox row on the left side of a vehicle above to prepare it for maintenance.")
# ------------------------------------------------------------------
# TAB 4: FLEET FUEL OPTIMIZATION & INTELLIGENCE (Professional Grade)
# ------------------------------------------------------------------
with tab4:
    st.header("⛽ Fleet Fuel Optimization & Intelligence")
    
    # Date Range Filter
    col_d1, col_d2 = st.columns(2)
    start_date = col_d1.date_input("Start Date", datetime.now() - timedelta(days=30))
    end_date = col_d2.date_input("End Date", datetime.now())

    # Initialize memory keys so data stays alive when adjusting widgets
    if "fuel_matrix_loaded" not in st.session_state:
        st.session_state.fuel_matrix_loaded = False
    if "cached_df" not in st.session_state:
        st.session_state.cached_df = None
    if "cached_summary" not in st.session_state:
        st.session_state.cached_summary = None

    if st.button("Load Fuel Intelligence Matrix"):
        try:
            # 1. Fetch data (Joining vehicles to get plate_number)
            response = supabase.table("fleet_fuel_logs").select("*, fleet_vehicles(plate_number)").execute()
            df = pd.DataFrame(response.data)
            
            # Extract plate number from the nested dictionary
            df['plate_number'] = df['fleet_vehicles'].apply(lambda x: x['plate_number'] if x else "Unknown")
            
            # Apply Date Filter
            df['fuel_date'] = pd.to_datetime(df['fuel_date'])
            df = df[(df['fuel_date'].dt.date >= start_date) & (df['fuel_date'].dt.date <= end_date)]
            
            if not df.empty:
                # 2. Calculate Efficiency
                df = df.sort_values(['plate_number', 'fuel_date'])
                df['distance_driven'] = df.groupby('plate_number')['odometer_reading'].diff()
                df['km_per_liter'] = df['distance_driven'] / df['liters_fueled']
                
                # 3. Summary Aggregation
                summary = df.groupby('plate_number').agg({'cost_etb': 'sum', 'km_per_liter': 'mean'}).reset_index()

                # Commit results to app memory vault
                st.session_state.cached_df = df
                st.session_state.cached_summary = summary
                st.session_state.fuel_matrix_loaded = True
            else:
                st.session_state.fuel_matrix_loaded = False
                st.info("No data found for the selected date range.")
        except Exception as e:
             st.error(f"Error loading matrix: {e}")

    # Persistent Render Block: If data is loaded in memory, draw the UI elements here
    if st.session_state.fuel_matrix_loaded:
        # Pull records safely out of state cache
        df = st.session_state.cached_df
        summary = st.session_state.cached_summary

        # 4. Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Spend", f"{df['cost_etb'].sum():,.0f} ETB")
        m2.metric("Total Liters", f"{df['liters_fueled'].sum():,.0f} L")
        m3.metric("Fleet Avg KM/L", f"{df['km_per_liter'].mean():,.2f}")
        
        # 5. Graph
        st.subheader("Efficiency Distribution")
        st.bar_chart(summary.set_index('plate_number')['km_per_liter'])
        
        # 6. Styled Table
        st.subheader("Performance Matrix")    
        st.dataframe(
            summary.style.background_gradient(subset=['km_per_liter'], cmap='RdYlGn')
                   .format({"cost_etb": "{:,.2f} ETB", "km_per_liter": "{:,.2f}"}),
            use_container_width=True,
            hide_index=True,
            column_config={
                "plate_number": "🚛 Plate Number",
                "cost_etb": "💰 Total Cost",
                "km_per_liter": "📊 Avg KM / Liter"
            }
        ) 
       
        # 7. Legend
        st.markdown("""
        **Performance Legend:**
        * <span style="color:red">**Red**</span>: Below average efficiency (Check for engine/maintenance issues).
        * <span style="color:orange">**Yellow**</span>: Moderate efficiency.
        * <span style="color:green">**Green**</span>: Optimal fuel efficiency.
        """, unsafe_allow_html=True)

       # ------------------------------------------------------------------
        # 8. OPERATIONAL DISPATCH ROUTE CLEARANCE ENGINE (Predictive Fuel Edition)
        # ------------------------------------------------------------------
        st.markdown("---")
        st.subheader("📋 Pre-Dispatch Route Clearance Engine")
        st.markdown("Verify if a vehicle has an acceptable historical efficiency profile and sufficient fuel level to clear its next trip assignment.")

        # Layout Controls: Row 1
        col_clear1, col_clear2, col_clear3 = st.columns(3)
        
        with col_clear1:
            available_vehicles = summary['plate_number'].tolist()
            selected_vehicle = st.selectbox("Assign Vehicle to Route", available_vehicles)
            
            # Fetch targeted vehicle's historical performance footprint
            v_profile = summary[summary['plate_number'] == selected_vehicle].iloc[0]
            v_efficiency = v_profile['km_per_liter']
            
        with col_clear2:
            # Defined before the slider so math can calculate remaining percentages dynamically
            tank_size = st.number_input("Vehicle Tank Size (Liters)", min_value=40, max_value=400, value=100, step=10)
            
        with col_clear3:
            target_distance = st.number_input("Target Trip Distance (KM)", min_value=10, max_value=1500, value=250, step=50)

        # --- RECONCILIATION ENGINE: PREDICTIVE CURRENT FUEL LEVEL ---
        v_logs = df[df['plate_number'] == selected_vehicle].sort_values('fuel_date', ascending=False)
        
        predicted_gauge_default = 50  # Operational fallback baseline
        calculation_insight = "ℹ️ No prior fuel logs found to parse an automated gauge estimation for this vehicle."
        
        if not v_logs.empty:
            latest_log = v_logs.iloc[0]
            latest_fuel_date = pd.to_datetime(latest_log['fuel_date'])
            
            # Calculate days elapsed since the vehicle last visited a pump line
            current_system_time = pd.to_datetime("2026-05-29")  # Keeps processing perfectly aligned to your database scope
            days_since_refuel = (current_system_time - latest_fuel_date).days
            
            # Extract historical average daily driving baseline for this specific profile
            v_logs_sorted = v_logs.sort_values('fuel_date')
            if len(v_logs_sorted) > 1:
                total_days_active = (v_logs_sorted['fuel_date'].max() - v_logs_sorted['fuel_date'].min()).days
                total_km_logged = v_logs_sorted['distance_driven'].sum()
                avg_daily_km = total_km_logged / total_days_active if total_days_active > 0 else 120.0
            else:
                avg_daily_km = 120.0  # Fleet fallback average
                
            # Compute predictive depletion values
            est_km_driven_since = max(0, days_since_refuel * avg_daily_km)
            est_liters_burned = est_km_driven_since / v_efficiency if v_efficiency > 0 else 0
            
            # Derive estimated fuel level remaining inside the tank asset
            est_remaining_liters = max(0, tank_size - est_liters_burned)
            predicted_gauge_default = int((est_remaining_liters / tank_size) * 100)
            predicted_gauge_default = min(100, max(0, predicted_gauge_default))
            
            calculation_insight = f"""
            💡 **Predictive Fuel Estimate:** This vehicle last fueled on **{latest_fuel_date.strftime('%Y-%m-%d')}**. 
            Based on its historical usage of **{avg_daily_km:.1f} KM/day**, it has driven roughly **~{est_km_driven_since:,.0f} KM** since that log entry, 
            burning **~{est_liters_burned:.1f} Liters**.
            """

        # Display calculated insight right above the interactive element
        st.info(calculation_insight)
        
        # Interactive slider now opens pre-configured to our data-driven prediction!
        fuel_gauge = st.slider(
            "Current Fuel Gauge Status (%)", 
            min_value=0, 
            max_value=100, 
            value=predicted_gauge_default, 
            step=5
        )

        # Layout Controls: Row 2 (Status output)
        col_status = st.columns(1)[0]
        
        # Range Math Core
        current_liters = tank_size * (fuel_gauge / 100.0)
        estimated_range = current_liters * v_efficiency
        required_safe_range = target_distance * 1.15

        with col_status:
            if estimated_range >= required_safe_range:
                st.success(f"""
                🟢 **DISPATCH APPROVED** * **Est. Range:** {estimated_range:,.1f} KM ({current_liters:.1f} Liters in tank)  
                * **Target Trip:** {target_distance} KM  
                
                The vehicle meets the route profile requirements and holds a healthy reserve safety buffer.
                """)
                
            elif estimated_range >= target_distance:
                st.warning(f"""
                ⚠️ **WARNING: MARGINAL FUEL BUFFER** * **Est. Range:** {estimated_range:,.1f} KM ({current_liters:.1f} Liters in tank)  
                * **Target Trip:** {target_distance} KM  
                
                The truck can technically reach the destination, but the safety threshold is tight (< 15%). Refueling before leaving the yard is recommended to protect against en-route delays.
                """)
                
            else:
                # Calculate shortfalls and real-world fuel cost impact based on current logs
                liters_shortfall = (required_safe_range - estimated_range) / v_efficiency
                avg_historical_price = df['cost_etb'].sum() / df['liters_fueled'].sum() if df['liters_fueled'].sum() > 0 else 85.0
                refuel_cost_etb = liters_shortfall * avg_historical_price
                
                st.error(f"""
                🚨 **DISPATCH BLOCKED: INSUFFICIENT RANGE** * **Est. Range:** {estimated_range:,.1f} KM  
                * **Target Trip:** {target_distance} KM  
                
                **Required Action:** Top-up the fuel tank by at least **{liters_shortfall:.1f} Liters** (Estimated Voucher Cost: **{refuel_cost_etb:,.2f} ETB**) to clear this vehicle for the assignment.
                """)