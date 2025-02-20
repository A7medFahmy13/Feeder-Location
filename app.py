import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
import random
from streamlit_folium import folium_static
from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads

# ✅ تحميل بيانات النقاط مع تنظيف الأسماء
@st.cache_data
def load_stored_points():
    csv_file_path = "Split_Coordinates_Data.csv"
    df = pd.read_csv(csv_file_path)

    # 📌 تنظيف أسماء الأعمدة
    df.columns = df.columns.str.strip().str.upper().str.replace("-", "_")

    # ✅ التأكد من وجود LATITUDE و LONGITUDE
    if "LONGITUDE" in df.columns:
        df["LONGITUDE"] = df["LONGITUDE"]
    elif "LONG" in df.columns:
        df["LONGITUDE"] = df["LONG"]
    elif "X" in df.columns:
        df["LONGITUDE"] = df["X"]
    else:
        st.error("⚠️ لم يتم العثور على `LONGITUDE` في البيانات!")
        return pd.DataFrame()

    if "LATITUDE" in df.columns:
        df["LATITUDE"] = df["LATITUDE"]
    elif "LAT" in df.columns:
        df["LATITUDE"] = df["LAT"]
    elif "Y" in df.columns:
        df["LATITUDE"] = df["Y"]
    else:
        st.error("⚠️ لم يتم العثور على `LATITUDE` في البيانات!")
        return pd.DataFrame()

    # تحويل الإحداثيات إلى Point
    df["geometry"] = [Point(lon, lat) for lon, lat in zip(df["LONGITUDE"].fillna(0), df["LATITUDE"].fillna(0))]
    return df

# ✅ تحميل بيانات المناطق
@st.cache_data
def load_stored_zones():
    excel_zones_path = "New Asser_Boundaries.xlsx"
    df = pd.read_excel(excel_zones_path)
    df.columns = df.columns.str.strip().str.lower()
    if "wkt" in df.columns:
        df["geometry"] = df["wkt"].apply(lambda x: wkt_loads(x) if isinstance(x, str) and pd.notnull(x) else None)
    return gpd.GeoDataFrame(df, geometry=df["geometry"])

# ✅ توليد ألوان عشوائية لكل منطقة
def get_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

# ✅ تشغيل التطبيق
def main():
    st.markdown("<div style='text-align: center; font-size: 24px;'>🌟 **لا تنسَ ذكر الله** 🌟</div>", unsafe_allow_html=True)
    st.title("🌍 Aseer Monitoring Map")

    # تحميل البيانات
    df_zones = load_stored_zones()
    df_points = load_stored_points()

    if df_points.empty:
        st.warning("⚠️ لم يتم تحميل بيانات النقاط بسبب خطأ في الإحداثيات!")
        return

    # 🔍 **الفلتر الرئيسي**
    filter_options = {
        "office": "المكتب",
        "contractor": "المقاول",
        "consultant": "الاستشاري",
        "om_supervisor": "مشرف التشغيل والصيانة",
        "mv_supervisor": "مشرف الصيانة المتوسطة"
    }

    selected_filter = st.selectbox("🛠️ اختر نوع الفلترة", ["بدون فلترة"] + list(filter_options.keys()))

    if selected_filter != "بدون فلترة":
        filter_list = sorted(df_zones[selected_filter].dropna().astype(str).unique().tolist())
        selected_value = st.selectbox(f"🔍 اختر {filter_options[selected_filter]}", ["بدون تحديد"] + filter_list)

        if selected_value != "بدون تحديد":
            filtered_df = df_zones[df_zones[selected_filter].astype(str) == selected_value]

            # 🔍 اختيار المناطق
            selected_zones = st.multiselect("📌 اختر المناطق", filtered_df["zone"].dropna().astype(str).unique().tolist())

            if selected_zones:
                df_zones_filtered = gpd.GeoDataFrame(filtered_df[filtered_df["zone"].isin(selected_zones)], geometry=filtered_df["geometry"])

                if df_zones_filtered.empty:
                    st.warning("⚠️ لم يتم العثور على أي مناطق متاحة للخريطة!")
                    return

                df_points_inside = df_points[df_points["geometry"].apply(lambda point: any(zone.contains(point) for zone in df_zones_filtered["geometry"] if zone))]

                # 🔍 **إضافة تصفية `FEEDER_ID`**
                if "FEEDER_ID" in df_points_inside.columns:
                    feeder_ids = sorted(df_points_inside["FEEDER_ID"].dropna().astype(str).unique().tolist())
                    selected_feeder = st.multiselect("🔌 اختر `FEEDER ID`", feeder_ids)
                    if selected_feeder:
                        df_points_inside = df_points_inside[df_points_inside["FEEDER_ID"].astype(str).isin(selected_feeder)]
                else:
                    st.warning("⚠️ لم يتم العثور على `FEEDER ID` في ملف النقاط!")

                # 📊 عرض **جدول المناطق مع الوصف**
                st.subheader("📊 تفاصيل المناطق المحددة")
                st.dataframe(df_zones_filtered.drop(columns=["geometry", "wkt"], errors='ignore'))

                # 📍 عرض **جدول النقاط قبل الخريطة**
                st.subheader(f"📍 النقاط داخل المناطق المختارة ({len(df_points_inside)})")
                st.dataframe(df_points_inside.drop(columns=["geometry"], errors='ignore'))

                # 🌍 إعداد الخريطة مع Zoom Extent
                if not df_zones_filtered.empty and df_zones_filtered["geometry"].notnull().any():
                    minx, miny, maxx, maxy = df_zones_filtered.total_bounds
                    m = folium.Map(zoom_start=12)
                    m.fit_bounds([[miny, minx], [maxy, maxx]])
                else:
                    m = folium.Map(location=[18.3, 42.5], zoom_start=10)  # إحداثيات افتراضية

                # 📌 إضافة المناطق بألوان مختلفة
                colors = {zone: get_random_color() for zone in df_zones_filtered["zone"].unique()}
                for _, row in df_zones_filtered.iterrows():
                    folium.GeoJson(row["geometry"], name=row["zone"],
                                   style_function=lambda feature, color=colors[row["zone"]]: {"fillColor": color, "color": "black", "weight": 2, "fillOpacity": 0.5}
                                  ).add_to(m)

                # 📍 إضافة النقاط للخريطة
                for _, row in df_points_inside.iterrows():
                    location_url = f"https://www.google.com/maps?q={row['LATITUDE']},{row['LONGITUDE']}"
                    popup_content = f"""
                    <b>FEEDER ID:</b> {row.get('FEEDER_ID', 'غير متوفر')}<br>
                    <b>الاسم:</b> {row.get('NAME', 'غير متوفر')}<br>
                    <b>الوصف:</b> {row.get('DESCRIPTION', 'غير متوفر')}<br>
                    <a href='{location_url}' target='_blank'>🔗 الذهاب إلى الموقع</a>
                    """
                    folium.Marker(
                        location=[row["LATITUDE"], row["LONGITUDE"]],
                        popup=folium.Popup(popup_content, max_width=300),
                        icon=folium.Icon(color="blue")
                    ).add_to(m)

                # 🗺️ عرض **الخريطة بعد النقاط**
                st.subheader("🗺️ الخريطة الجغرافية")
                folium_static(m)

if __name__ == "__main__":
    main()


