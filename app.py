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
    df["lat"] = df["latitude"]
    df["long"] = df["longitude"]
    points = [Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"])]
    return {
        "points": points,
        "names": df["name"].tolist(),
        "descriptions": df["description"].tolist(),
        "latitudes": df["lat"].tolist(),
        "longitudes": df["long"].tolist()
    }

# ✅ تحميل بيانات المناطق من ملف CSV
@st.cache_data
def load_stored_zones():
    csv_zones_path = "Asser_Boundaries.csv"  # اسم ملف المناطق المخزن داخل البرنامج
    df = pd.read_csv(csv_zones_path)
    df["geometry"] = df["wkt"].apply(wkt_loads)  # تحويل WKT إلى Polygon
    return {
        "polygons": df["geometry"].tolist(),
        "zone_names": df["name"].tolist(),
        "descriptions": df["description"].tolist()
    }

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
    
    if "points_data" not in st.session_state:
        st.session_state.points_data = load_stored_points()
    if "zone_data" not in st.session_state:
        st.session_state.zone_data = load_stored_zones()
    
    # تأكيد تحميل البيانات
    if st.session_state.points_data and st.session_state.zone_data:
        st.success("✅ تم تحميل البيانات بنجاح!")
    else:
        st.error("❌ حدث خطأ في تحميل البيانات.")
        return
    
    # عرض قائمة المناطق إذا كانت موجودة
    if st.session_state.zone_data["zone_names"]:
        st.markdown("### اختر المنطقة")
        selected_zone = st.selectbox("Asser_Boundry", ["اختر منطقة..."] + st.session_state.zone_data["zone_names"])
        
        if selected_zone != "اختر منطقة...":
            # عرض وصف المنطقة المحددة في جدول ديناميكي متناسق مع الصفحة
            zone_index = st.session_state.zone_data["zone_names"].index(selected_zone)
            description = st.session_state.zone_data["descriptions"][zone_index].replace("<br>", "\n")
            description_lines = [line.strip() for line in description.split("\n") if line.strip()]
            
            table_data = []
            for i in range(0, len(description_lines), 2):
                key = description_lines[i] if i < len(description_lines) else ""
                value = description_lines[i+1] if i+1 < len(description_lines) else ""
                table_data.append([key, value])
            
            table_df = pd.DataFrame(table_data, columns=["المعلومة", "التفاصيل"])
            st.table(table_df)
            
            selected_polygon = st.session_state.zone_data["polygons"][zone_index]
            points_gdf = gpd.GeoDataFrame({
                "اسم النقطة": st.session_state.points_data["names"],
                "الوصف": st.session_state.points_data["descriptions"],
                "latitude": st.session_state.points_data["latitudes"],
                "longitude": st.session_state.points_data["longitudes"],
                "geometry": st.session_state.points_data["points"]
            }, crs="EPSG:4326")

            points_inside = points_gdf[points_gdf.geometry.within(selected_polygon)]
            st.success(f"✅ تم العثور على {len(points_inside)} نقطة داخل المنطقة {selected_zone}!")
            st.dataframe(points_inside.drop(columns=["geometry"]))
            
            # إعادة الخريطة التفاعلية
            m = folium.Map(location=[selected_polygon.centroid.y, selected_polygon.centroid.x], zoom_start=10)
            folium.GeoJson(selected_polygon, name=selected_zone).add_to(m)
            for _, row in points_inside.iterrows():
                folium.Marker([row["latitude"], row["longitude"]],
                              popup=row["اسم النقطة"],
                              icon=folium.Icon(color="blue")).add_to(m)
            folium_static(m)
    else:
        st.warning("❗ لم يتم العثور على مناطق مخزنة.")

if __name__ == "__main__":
    main()
