import streamlit as st
import requests
import pandas as pd

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
# TAB 1: PROFESSIONAL FINANCIAL PREDICTIVE SIMULATOR
# ------------------------------------------------------------------
with tab1:
    st.header("Financial Predictive Simulator")
    col_input1, col_input2 = st.columns(2)
    input_km = col_input1.number_input("Target KM Driven", min_value=0.0, value=3500.0)
    input_days = col_input2.slider("Days in Workshop", 0, 30, 12)

    if st.button("Run Detailed Simulation"):
        try:
            payload = {"km": input_km, "days": input_days}
            response = requests.post("http://127.0.0.1:8000/analyze-fleet", json=payload)
            
            if response.status_code == 200:
                result = response.json().get("data", {})
                a = result.get('scenario_a', {})
                b = result.get('scenario_b', {})
                total_a = a.get('total', 0)
                total_b = b.get('total', 0)
                diff = total_a - total_b

                # --- 1. FINANCIAL STRATEGY INSIGHT ---
                st.subheader("💡 Financial Strategy Insight")
                if diff > 0:
                    st.success(f"**Strategic Recommendation:** Premium Logistics (Scenario B) is more cost-efficient. Saving **{abs(diff):,.2f} ETB**.")
                else:
                    st.info(f"**Strategic Recommendation:** Standard Logistics (Scenario A) is most economical. Preserves **{abs(diff):,.2f} ETB**.")

                # --- 2. FLEET OPERATIONAL COST FORECAST ---
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

                # --- 3. MANAGEMENT BRIEFING ---
                st.subheader("💡 Management Briefing: Logistics Strategy")

                def get_briefing(scenario_name, details, is_recommended):
                    fuel = details.get('fuel_component', 0)
                    downtime = details.get('downtime_component', 0)
                    
                    if scenario_name == "B":
                        explanation = ("**Scenario B (Premium):** This is a 'Proactive' model. It invests more in maintenance "
                                       "(higher downtime penalty) to ensure the vehicles are in top condition, which "
                                       "dramatically reduces fuel consumption and operational risks.")
                    else:
                        explanation = ("**Scenario A (Standard):** This is a 'Reactive' model. It focuses on lower immediate "
                                       "maintenance costs, but this lack of proactivity leads to higher fuel consumption "
                                       "and reduced engine efficiency over time.")
                    
                    status = "✅ Recommended" if is_recommended else "⚠️ Alternative"
                    return f"**{status}**\n\n{explanation}\n\n* **Fuel Expense:** {fuel:,.2f} ETB\n* **Downtime Penalty:** {downtime:,.2f} ETB"

                is_b_recommended = diff > 0 
                col_a, col_b = st.columns(2)
                with col_a: st.markdown(get_briefing("A", a, not is_b_recommended))
                with col_b: st.markdown(get_briefing("B", b, is_b_recommended))
                st.info("🎯 **Next Steps:** Evaluate if your mission requirements justify the trade-off in fleet efficiency.")

                # --- 4. VISUALIZATION ---
                st.markdown("### Cost Composition Comparison")
                df = pd.DataFrame([a, b], index=["Standard", "Premium"])
                st.bar_chart(df[['fuel_component', 'downtime_component']])
            
            else:
                st.error("Failed to fetch simulation data.")
        except Exception as e:
            st.error(f"Simulation connection failed: {e}")
# ------------------------------------------------------------------
# TAB 2: FLEET ASSISTANT & CONTROLS
# ------------------------------------------------------------------
with tab2:
    st.header("Fleet Assistant & Controls")
    
    # Ensure session state is initialized once
    if "selected_plate" not in st.session_state:
        st.session_state.selected_plate = None

    col_read, col_write = st.columns([1, 1])

    # --- LEFT COLUMN: FLEET INQUIRIES ---
    with col_read:
        st.subheader("📋 Fleet Inquiries")
        
        # We store the dataframe in session state to survive reruns
        if "inquiry_df" not in st.session_state:
            st.session_state.inquiry_df = None

        query = st.selectbox("What would you like to know?", 
                             ["List All Vehicles", "Vehicles in Workshop", "Vehicles Needing Inspection"],
                             key="query_choice")
        
        if st.button("Ask Assistant", key="btn_ask"):
            with st.spinner("Fetching..."):
                try:
                    response = requests.post("http://127.0.0.1:8000/fleet-query", json={"query_type": query})
                    if response.status_code == 200:
                        st.session_state.inquiry_df = pd.DataFrame(response.json().get("data", []))
                except Exception as e:
                    st.error("API unreachable")

        if st.session_state.inquiry_df is not None:
            st.dataframe(st.session_state.inquiry_df, use_container_width=True, hide_index=True)

    # --- RIGHT COLUMN: WORKSHOP & CREW CONTROL ---
    with col_write:
        st.subheader("🔧 Workshop & Crew Control")
        
        # Fetch plate data only if not already in cache
        @st.cache_data(ttl=30)
        def fetch_plates():
            try:
                return requests.get("http://127.0.0.1:8000/api/fleet/plates").json().get("plates", [])
            except:
                return []

        all_plates = fetch_plates()

        if all_plates:
            # Dropdown - KEY is crucial here to stop resets
            selected_plate = st.selectbox("Select Vehicle", all_plates, key="w_plate")
            
            # Workshop Status
            status_choice = st.radio("Workshop Status:", ["Active in Fleet ✅", "Checked Into Workshop 🛠️"], key="w_status")
            
            if st.button("Commit Workshop Status", key="btn_workshop"):
                is_in = "Checked Into" in status_choice
                resp = requests.post("http://127.0.0.1:8000/api/fleet/workshop-status", 
                                     json={"plate_number": selected_plate, "is_in_workshop": is_in})
                if resp.status_code == 200:
                    st.success("Status Updated!")
                    st.rerun()

            st.markdown("---")
            
            # Driver Assignment
            # Fetch drivers directly here; since this is inside the column, 
            # it won't force a full page-level re-render if cached correctly
            try:
                d_res = requests.get("http://127.0.0.1:8000/api/drivers/available").json().get("drivers", [])
                drivers_map = {f"{d['full_name']}": d['id'] for d in d_res}
                sel_d = st.selectbox("Assign Driver", ["Unassigned"] + list(drivers_map.keys()), key="assign_driver")
                
                if st.button("Confirm Crew Assignment", key="btn_driver"):
                    driver_id = drivers_map.get(sel_d, None)
                    requests.post("http://127.0.0.1:8000/api/fleet/assign-driver", 
                                  json={"plate_number": selected_plate, "driver_id": driver_id})
                    st.success("Assignment saved!")
                    st.rerun()
            except:
                st.warning("Driver service unavailable.")
        else:
            st.error("Cannot load vehicle list.")
# ------------------------------------------------------------------
# TAB 3: AUTOMATED SERVICE PROJECTIONS
# ------------------------------------------------------------------
with tab3:
    st.header("🗓️ Automated Service Projections")
    interval = st.selectbox("Select Target Service Interval (KM)", [5000, 10000], index=0)
    
    if st.button("Generate Maintenance Timeline"):
        response = requests.get(f"http://127.0.0.1:8000/api/maintenance/predictions?interval={interval}")
        if response.status_code == 200:
            st.session_state.df_pred = pd.DataFrame(response.json())
        else:
            st.error("Failed to fetch maintenance data.")

    # Only show the table if we have data in session_state
    if st.session_state.df_pred is not None:
        df_pred = st.session_state.df_pred
        
        st.subheader("Upcoming Maintenance Schedule")
        
        def highlight_urgent(row):
            if row['km_remaining'] < 500:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)

        st.dataframe(
            df_pred.style.apply(highlight_urgent, axis=1),
            use_container_width=True,
            column_config={
                "plate_number": st.column_config.TextColumn("🚛 Plate Number"),
                "predicted_maintenance_date": st.column_config.DateColumn("📅 Estimated Service Date"),
                "km_remaining": st.column_config.NumberColumn("⚠️ KM Until Service")
            }
        )
        
        st.divider()
        st.subheader("🛠️ Take Action on Urgent Fleet")

        selected_plate = st.selectbox("Select a vehicle to send to Maintenance", df_pred['plate_number'].unique())

        if st.button(f"Send {selected_plate} to Maintenance"):
            # Fixed URL and JSON payload to match backend expectations
            response = requests.post(
                "http://127.0.0.1:8000/api/fleet/workshop-status",
                json={"plate_number": selected_plate, "is_in_workshop": True}
            )
            
            if response.status_code == 200:
                st.success(f"Vehicle {selected_plate} moved to Maintenance!")
                st.balloons()
                st.rerun() 
            else:
                st.error(f"Failed to update status. Code: {response.status_code}")
                    
        st.info("💡 **Pro-Tip:** Cross-reference this schedule with the 'Performance Matrix' in the Fuel Analytics tab.")
# ------------------------------------------------------------------
# TAB 4: FLEET FUEL OPTIMIZATION & INTELLIGENCE
# ------------------------------------------------------------------
with tab4:
    st.header("⛽ Fleet Fuel Optimization & Intelligence")
    
    if st.button("Load Fuel Intelligence Matrix"):
        response = requests.get("http://127.0.0.1:8000/api/analytics/fuel")
        
        if response.status_code == 200:
            data = response.json().get("data", [])
            df_fuel = pd.DataFrame(data)
            
            # KPI Metrics
            m1, m2 = st.columns(2)
            m1.metric("Total Fleet Spend", f"{df_fuel['total_cost_etb'].sum():,.2f} ETB")
            m2.metric("Fleet Average KM/L", f"{df_fuel['km_per_liter'].mean():,.2f}")
            
            # --- INTELLIGENCE MATRIX ---
            st.subheader("Performance Matrix")
            st.markdown("Vehicles with low KM/L ratios are candidates for 'Premium' maintenance.")
            
            # Visualizing performance
            st.bar_chart(df_fuel.set_index("plate_number")["km_per_liter"])
            
            # Data Table with conditional highlighting
            st.dataframe(
                df_fuel.style.background_gradient(subset=["km_per_liter"], cmap="RdYlGn"),
                use_container_width=True
            )
            
            # Proactive Recommendation
            poor_performers = df_fuel[df_fuel['km_per_liter'] < df_fuel['km_per_liter'].mean()]
            if not poor_performers.empty:
                st.warning(f"**Optimization Alert:** {len(poor_performers)} vehicles are performing below average. Consider moving these to 'Premium' logistics to address engine inefficiencies.")