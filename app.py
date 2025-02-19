import streamlit as st
import geopandas as gpd
import pandas as pd
import zipfile
import io
import folium
from streamlit_folium import folium_static
from shapely.geometry import Point, Polygon
from shapely.wkt import loads as wkt_loads
from lxml import etree

# ✅ تحميل بيانات النقاط من ملف CSV
@st.cache_data
def load_stored_points():
    csv_file_path = "Split_Coordinates_Data.csv"  # اسم ملف النقاط المخزن داخل البرنامج
    df = pd.read_csv(csv_file_path)
    df["lat"] = df.get("latitude", pd.Series())
    df["long"] = df.get("longitude", pd.Series())
    df["geometry"] = [Point(lon, lat) for lon, lat in zip(df["longitude"].fillna(0), df["latitude"].fillna(0))]
    return df

# ✅ تحميل بيانات المناطق من ملف Excel الجديد
@st.cache_data
def load_stored_zones():
    excel_zones_path = "New Asser_Boundaries.xlsx"  # اسم ملف المناطق المخزن داخل البرنامج
    df = pd.read_excel(excel_zones_path)
    df.columns = df.columns.str.strip().str.lower()  # تنظيف أسماء الأعمدة
    
    # تحويل WKT إلى Polygon
    if "wkt" in df.columns:
        df["geometry"] = df["wkt"].apply(lambda x: wkt_loads(x) if pd.notnull(x) else None)
    
    return df  # إرجاع DataFrame بالكامل

# ✅ تشغيل التطبيق
def main():
    st.markdown("""
        <div style='text-align: center; font-size: 24px;'>
            🌟 **لا تنسَ ذكر الله** 🌟
        </div>
    """, unsafe_allow_html=True)
    
    if "start_app" not in st.session_state:
        st.session_state.start_app = False
    
    if not st.session_state.start_app:
        st.markdown("""
            <div style='text-align: center; font-size: 20px; margin-top: 20px;'>
                🗺️ **مرحبًا بك في Aseer Monitoring Map** 🗺️
            </div>
            <div style='text-align: center; font-size: 16px; margin-top: 10px;'>
                هذا التطبيق يتيح لك تحليل ومراقبة المواقع الجغرافية داخل منطقة عسير باستخدام البيانات الجغرافية.
            </div>
            <div style='text-align: center; font-size: 18px; color: gray;'>
                🎗️ **إهداء إلى الأخ العزيز المهندس موسى السعيد** 🎗️
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("دخول البرنامج", use_container_width=True):
            st.session_state.start_app = True
            st.rerun()
        
        return
    
    st.title("🗺️ Aseer Monitoring Map")
    
    if "zone_data" not in st.session_state:
        st.session_state.zone_data = load_stored_zones()
    df_zones = st.session_state.zone_data
    
    if "point_data" not in st.session_state:
        st.session_state.point_data = load_stored_points()
    df_points = st.session_state.point_data
    
    if df_zones is None:
        return
    
    # تعريف الفلاتر وشجرة الفلترة
    filter_options = {
        "office": ["zone"],
        "contractor": ["zone"],
        "consultant": ["zone"],
        "om_supervisor": ["zone"],
        "mv_supervisor": ["zone"]
    }
    
    selected_filter = st.selectbox("🔍 اختر الفلتر الأساسي", ["اختر..."] + list(filter_options.keys()))
    
    if selected_filter != "اختر...":
        filter_list = sorted(df_zones[selected_filter].dropna().astype(str).unique().tolist())
        selected_value = st.selectbox(f"🔍 اختر {selected_filter}", ["اختر..."] + filter_list)
        
        if selected_value != "اختر...":
            df_zones = df_zones[df_zones[selected_filter].astype(str) == selected_value]
            
            # التعامل مع الفلتر التالي وفقًا لشجرة الفلترة
            if "zone" in df_zones.columns:
                zone_list = sorted(df_zones["zone"].dropna().astype(str).unique().tolist())
                selected_zone = st.selectbox("🔍 اختر zone", ["اختر..."] + zone_list)
                
                if selected_zone != "اختر...":
                    df_zones = df_zones[df_zones["zone"].astype(str) == selected_zone]
                    
                    st.subheader("📊 تفاصيل المنطقة")
                    st.dataframe(df_zones.drop(columns=["geometry", "wkt"], errors='ignore'))
                    
                    selected_polygon = df_zones.iloc[0]["geometry"]
                    df_points_inside = df_points[df_points["geometry"].apply(lambda point: selected_polygon.contains(point))]
                    
                    if not df_points_inside.empty:
                        st.subheader(f"📍 النقاط داخل المنطقة ({len(df_points_inside)})")
                        st.dataframe(df_points_inside)
                        
                        # عرض الخريطة التفاعلية
                        m = folium.Map(location=[selected_polygon.centroid.y, selected_polygon.centroid.x], zoom_start=12)
                        folium.GeoJson(selected_polygon, name="المنطقة المحددة").add_to(m)
                        
                        for _, row in df_points_inside.iterrows():
                            location_url = f"https://www.google.com/maps?q={row['lat']},{row['long']}"
                            popup_content = f"""
                            <b>الاسم:</b> {row['name']}<br>
                            <b>الوصف:</b> {row['description']}<br>
                            <a href='{location_url}' target='_blank'>🔗 الذهاب إلى الموقع</a>
                            """
                            folium.Marker(
                                location=[row["lat"], row["long"]],
                                popup=folium.Popup(popup_content, max_width=300)
                            ).add_to(m)
                        
                        folium_static(m)
    
if __name__ == "__main__":
    main()
