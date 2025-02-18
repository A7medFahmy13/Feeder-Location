import streamlit as st
import geopandas as gpd
import pandas as pd
import zipfile
import io
import os
import folium
from streamlit_folium import folium_static
from shapely.geometry import Point, Polygon
from lxml import etree
from pathlib import Path

# ✅ دالة استخراج KML من KMZ
def extract_kml_from_kmz(uploaded_file):
    """استخراج KML من KMZ حتى لو كان `doc.kml`"""
    try:
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            kml_files = [name for name in z.namelist() if name.endswith('.kml')]
            if not kml_files:
                return None, "❌ لم يتم العثور على ملف KML داخل KMZ."
            with z.open(kml_files[0]) as kml_file:
                return io.BytesIO(kml_file.read()), None
    except Exception as e:
        return None, f"❌ خطأ أثناء استخراج KML: {e}"

# ✅ دالة تحليل KML واستخراج النقاط والمضلعات والوصف مع فصل النقاط المدمجة
def parse_kml(kml_file):
    """تحليل KML لاستخراج النقاط، الأوصاف، والمضلعات"""
    try:
        tree = etree.parse(kml_file)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        points, names, descriptions, polygons = [], [], [], []
        
        for placemark in root.findall(".//kml:Placemark", ns):
            name = placemark.find("kml:name", ns)
            name = name.text.strip() if name is not None else "بدون اسم"

            description = placemark.find("kml:description", ns)
            description = description.text.strip() if description is not None else "لا يوجد وصف"

            point = placemark.find(".//kml:Point/kml:coordinates", ns)
            if point is not None:
                coords_list = point.text.strip().split()
                for coords in coords_list:
                    coord_vals = coords.split(",")
                    if len(coord_vals) >= 2:
                        points.append(Point(float(coord_vals[0]), float(coord_vals[1])))
                        names.append(name)
                        descriptions.append(description)
        
        for polygon in root.findall(".//kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", ns):
            coords = polygon.text.strip().split()
            polygon_points = [tuple(map(float, coord.split(",")[:2])) for coord in coords]
            polygons.append(Polygon(polygon_points))
        
        return {"points": points, "polygons": polygons, "names": names, "descriptions": descriptions}, None
    except Exception as e:
        return None, f"❌ خطأ أثناء تحليل KML: {e}"

# ✅ تشغيل التطبيق
def main():
    st.title("🔍 تحليل النقاط داخل منطقة محددة")
    st.markdown("📂 **قم برفع ملف النقاط وملف المنطقة (KML/KMZ)**")

    points_file = st.file_uploader("📌 رفع ملف النقاط (KML/KMZ)", type=["kml", "kmz"])
    zone_file = st.file_uploader("📌 رفع ملف المنطقة (KML/KMZ)", type=["kml", "kmz"])

    if st.button("🔄 بدء العملية"):
        if points_file and zone_file:
            with st.spinner("📊 جاري تحليل البيانات..."):
                points_kml, points_error = extract_kml_from_kmz(points_file) if points_file.name.endswith(".kmz") else (points_file, None)
                zone_kml, zone_error = extract_kml_from_kmz(zone_file) if zone_file.name.endswith(".kmz") else (zone_file, None)

                if points_error:
                    st.error(points_error)
                if zone_error:
                    st.error(zone_error)

                if not points_error and not zone_error:
                    points_data, points_parse_error = parse_kml(points_kml)
                    zone_data, zone_parse_error = parse_kml(zone_kml)

                    if points_parse_error:
                        st.error(points_parse_error)
                    if zone_parse_error:
                        st.error(zone_parse_error)

                    if not points_parse_error and not zone_parse_error:
                        points_gdf = gpd.GeoDataFrame({
                            "رقم النقطة": range(1, len(points_data["points"]) + 1),
                            "اسم النقطة": points_data["names"],
                            "الوصف": points_data["descriptions"],
                            "geometry": points_data["points"]
                        }, crs="EPSG:4326")

                        points_gdf["longitude"] = points_gdf.geometry.x
                        points_gdf["latitude"] = points_gdf.geometry.y

                        if zone_data["polygons"]:
                            zone_polygon = zone_data["polygons"][0]
                            points_inside = points_gdf[points_gdf.geometry.within(zone_polygon)]
                            center = zone_polygon.centroid
                        else:
                            st.warning("❗ لم يتم العثور على مضلع في ملف المنطقة المحددة.")
                            points_inside = points_gdf
                            center = [points_gdf["latitude"].mean(), points_gdf["longitude"].mean()]

                        st.success(f"✅ تم استخراج {len(points_inside)} نقطة داخل المنطقة بنجاح!")
                        st.dataframe(points_inside.drop(columns=["geometry"]))
                        
                        m = folium.Map(location=[center.y, center.x], zoom_start=14, tiles="https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google", subdomains=["mt0", "mt1", "mt2", "mt3"])
                        folium.GeoJson(zone_polygon, name="منطقة البحث").add_to(m)
                        for _, row in points_inside.iterrows():
                            location_url = f"https://www.google.com/maps?q={row['latitude']},{row['longitude']}"
                            folium.Marker([row["latitude"], row["longitude"]], popup=f'<a href="{location_url}" target="_blank">مشاركة الموقع</a>', icon=folium.Icon(color="blue")).add_to(m)
                        
                        folium_static(m)

if __name__ == "__main__":
    main()
