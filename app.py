import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
import bcrypt
import os
import requests
from io import StringIO
from streamlit_folium import folium_static
from shapely.wkt import loads as wkt_loads
from shapely.geometry import Point
from folium.plugins import MarkerCluster, HeatMap, MeasureControl, LocateControl, Fullscreen
import time
from PIL import Image
import logging
import uuid

# إعداد التسجيل (Logging)
logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# إعداد الصفحة
st.set_page_config(page_title="🚀 تسجيل الدخول", page_icon="🔐", layout="centered")

# تحميل بيانات المستخدمين
@st.cache_resource
def load_users():
    file_path = "users.xlsx"
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip().str.lower()

        required_columns = {"username", "password", "role", "linked_name"}
        if not required_columns.issubset(df.columns):
            st.error("❌ خطأ: ملف المستخدمين غير مكتمل!")
            logging.error("ملف المستخدمين غير مكتمل")
            return {}, {}, {}

        df["username"] = df["username"].str.strip().str.lower()
        # تشفير كلمات المرور باستخدام bcrypt
        df["password"] = df["password"].apply(lambda x: bcrypt.hashpw(str(x).encode(), bcrypt.gensalt()).decode())
        df["role"] = df["role"].str.strip().str.lower()
        df["linked_name"] = df["linked_name"].str.strip().str.lower().replace(" ", "_")

        return (df.set_index("username")["password"].to_dict(),
                df.set_index("username")["role"].to_dict(),
                df.set_index("username")["linked_name"].to_dict())
    except Exception as e:
        st.error(f"⚠️ خطأ في تحميل ملف المستخدمين: {e}")
        logging.error(f"خطأ في تحميل ملف المستخدمين: {e}")
        return {}, {}, {}

USERS, USER_ROLES, USER_LINKED_NAMES = load_users()

# التحقق من تسجيل الدخول
def authenticate(username, password):
    username = username.strip().lower()
    hashed_password = USERS.get(username)
    if hashed_password:
        try:
            return bcrypt.checkpw(password.strip().encode(), hashed_password.encode())
        except Exception as e:
            logging.error(f"خطأ في التحقق من كلمة المرور: {e}")
            return False
    return False

# صفحة تسجيل الدخول
def login_page():
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f5f5f5;
        }
        .login-container {
            text-align: center;
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
            width: 400px;
            margin: auto;
        }
        .login-title {
            font-size: 24px;
            font-weight: bold;
            color: #FF4B4B;
        }
        .login-input {
            border-radius: 5px;
            padding: 10px;
            width: 100%;
            border: 1px solid #ddd;
            margin-top: 10px;
        }
        .login-button {
            background-color: #FF4B4B;
            color: white;
            padding: 10px;
            border: none;
            width: 100%;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        .login-button:hover {
            background-color: #E03B3B;
        }
        </style>
        <div class="login-container">
            <h1 class="login-title">🔑 تسجيل الدخول</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    username = st.text_input("👤 اسم المستخدم", placeholder="أدخل اسم المستخدم هنا").strip().lower()
    password = st.text_input("🔒 كلمة المرور", type="password", placeholder="أدخل كلمة المرور")

    if st.button("🚀 تسجيل الدخول", help="اضغط لتسجيل الدخول"):
        if authenticate(username, password):
            st.session_state.update({
                "authenticated": True,
                "user": username,
                "role": USER_ROLES.get(username, "unknown"),
                "linked_name": USER_LINKED_NAMES.get(username, "unknown"),
                "session_id": str(uuid.uuid4()),  # إضافة معرف جلسة فريد
                "last_activity": time.time()
            })
            st.success(f"✅ مرحباً {username}! يتم تسجيل الدخول... 🎉")
            logging.info(f"تسجيل دخول ناجح للمستخدم: {username}")
            st.rerun()
        else:
            st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة!")
            logging.warning(f"محاولة تسجيل دخول فاشلة للمستخدم: {username}")

    st.markdown("<br><br><small>🔹 إذا كنت تواجه مشكلة في تسجيل الدخول، يرجى التواصل مع فريق الدعم.</small>", unsafe_allow_html=True)

# التحقق من حالة الجلسة
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login_page()
    st.stop()
else:
    st.sidebar.button("🔓 تسجيل الخروج", on_click=lambda: st.session_state.update({"authenticated": False}))

# تحميل بيانات المناطق
@st.cache_resource
def load_zones():
    try:
        df_zones = pd.read_excel("New Asser_Boundaries.xlsx")
        df_zones.columns = df_zones.columns.str.strip().str.lower()
        
        if "wkt" in df_zones.columns:
            df_zones["geometry"] = df_zones["wkt"].apply(lambda x: wkt_loads(x) if isinstance(x, str) else None)
            df_zones = gpd.GeoDataFrame(df_zones, geometry="geometry")
        return df_zones
    except Exception as e:
        st.error(f"⚠️ خطأ في تحميل بيانات المناطق: {e}")
        logging.error(f"خطأ في تحميل بيانات المناطق: {e}")
        return gpd.GeoDataFrame()

df_zones = load_zones()

# تحميل بيانات النقاط من Google Drive مع التخزين المؤقت
@st.cache_resource
def load_points_from_drive():
    google_drive_url = "https://drive.google.com/uc?export=download&id=1gR51HKKCY7PSNmUOnHS5-A7HFCx5uWxa"
    cache_file = "points_cache.csv"
    
    # التحقق من وجود ملف التخزين المؤقت
    if os.path.exists(cache_file):
        try:
            df_points = pd.read_csv(cache_file)
            df_points.columns = df_points.columns.str.strip().str.lower()
            df_points["geometry"] = df_points.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
            return gpd.GeoDataFrame(df_points, geometry="geometry")
        except Exception as e:
            logging.warning(f"فشل تحميل ملف التخزين المؤقت: {e}")

    with st.spinner("🚀 جاري تحميل البيانات من Google Drive... الرجاء الانتظار ⏳"):
        progress_bar = st.progress(0)
        try:
            response = requests.get(google_drive_url)
            if response.status_code == 200:
                csv_data = StringIO(response.text)
                df_points = pd.read_csv(csv_data)
                df_points.columns = df_points.columns.str.strip().str.lower()
                
                df_points["geometry"] = df_points.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
                df_points = gpd.GeoDataFrame(df_points, geometry="geometry")
                
                # حفظ البيانات في ملف التخزين المؤقت
                df_points.drop(columns=["geometry"], errors="ignore").to_csv(cache_file, index=False)
                
                for i in range(1, 101):
                    time.sleep(0.01)
                    progress_bar.progress(i)
                
                st.success("✅ تم تحميل البيانات بنجاح!")
                logging.info("تم تحميل بيانات النقاط من Google Drive")
                return df_points
            else:
                st.error(f"⚠️ تعذر تحميل الملف من Google Drive. رمز الحالة: {response.status_code}")
                logging.error(f"تعذر تحميل الملف من Google Drive: {response.status_code}")
                return gpd.GeoDataFrame()
        except Exception as e:
            st.error(f"⚠️ خطأ: تعذر تحميل بيانات النقاط من Google Drive: {e}")
            logging.error(f"خطأ في تحميل بيانات النقاط: {e}")
            return gpd.GeoDataFrame()

df_points = load_points_from_drive()

if df_points is None or df_points.empty:
    st.warning("⚠️ لم يتم تحميل بيانات النقاط، يرجى التحقق من الاتصال بالإنترنت أو رابط Google Drive.")
    df_points = gpd.GeoDataFrame()

# تصفية النقاط باستخدام Spatial Index
def filter_points_in_zones(df_points, df_zones_filtered):
    if df_zones_filtered.empty or df_points.empty:
        return gpd.GeoDataFrame()
    
    sindex = df_zones_filtered.sindex
    valid_points = []
    
    for idx, point in df_points.iterrows():
        possible_matches = list(sindex.intersection(point.geometry.bounds))
        for zone_idx in possible_matches:
            if df_zones_filtered.iloc[zone_idx].geometry.contains(point.geometry):
                valid_points.append(idx)
                break
    
    return df_points.loc[valid_points]

# تصفية البيانات بناءً على المستخدم
user_role = st.session_state["role"]
linked_name = st.session_state["linked_name"]

if user_role != "admin":
    relevant_columns = [col for col in ["om_supervisor", "mv_supervisor", user_role] if col in df_zones.columns]
    if relevant_columns:
        df_zones = df_zones[df_zones[relevant_columns].astype(str).apply(lambda row: row.str.contains(linked_name, na=False, case=False)).any(axis=1)]

# اختيار المناطق
st.title("🌍 ASEER FEEDER MAP")
st.write(f"Welcome our strategic partner >> {st.session_state['user']} 👋")

selected_zones = st.multiselect("اختر المناطق", df_zones["zone"].unique())

df_zones_filtered = gpd.GeoDataFrame()
df_points_filtered = gpd.GeoDataFrame()

if selected_zones:
    df_zones_filtered = df_zones[df_zones["zone"].isin(selected_zones)].copy()
    df_zones_filtered = df_zones_filtered.explode(index_parts=True)

    if not df_zones_filtered.empty:
        df_points_filtered = filter_points_in_zones(df_points, df_zones_filtered)

    # فلتر feeder_id
    if "feeder_id" in df_points_filtered.columns:
        feeder_ids = df_points_filtered["feeder_id"].unique()
        selected_feeder_ids = st.multiselect("اختر Feeder ID", feeder_ids)
        
        if selected_feeder_ids:
            df_points_filtered = df_points_filtered[df_points_filtered["feeder_id"].isin(selected_feeder_ids)]

    # عرض البيانات
    with st.expander(f"📊 بيانات المناطق ({len(df_zones_filtered)})", expanded=True):
        st.dataframe(df_zones_filtered.drop(columns=["geometry"], errors="ignore"))

    with st.expander(f"📍 بيانات النقاط ({len(df_points_filtered)})", expanded=True):
        st.dataframe(df_points_filtered.drop(columns=["geometry"], errors="ignore"))

    # زر تصدير البيانات
    if not df_points_filtered.empty:
        csv = df_points_filtered.drop(columns=["geometry"], errors="ignore").to_csv(index=False)
        st.download_button(
            label="📥 تصدير البيانات كـ CSV",
            data=csv,
            file_name="filtered_points.csv",
            mime="text/csv"
        )

# لوحة الإحصائيات
if not df_points_filtered.empty:
    st.subheader("📊 إحصائيات البيانات")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("عدد النقاط", len(df_points_filtered))
    with col2:
        st.metric("عدد المناطق", len(df_zones_filtered))
    
    if "feeder_id" in df_points_filtered.columns:
        feeder_counts = df_points_filtered["feeder_id"].value_counts()
        st.bar_chart(feeder_counts)

# تحديد موقع المستخدم
if "user_lat" not in st.session_state or "user_lon" not in st.session_state:
    try:
        response = requests.get("https://ipinfo.io/json")
        location_data = response.json()
        lat, lon = map(float, location_data["loc"].split(","))
        st.session_state["user_lat"], st.session_state["user_lon"] = lat, lon
    except:
        st.session_state["user_lat"], st.session_state["user_lon"] = None, None

# إعداد الخريطة
st.subheader("🌍 الخريطة التفاعلية")
m = folium.Map(zoom_start=10, control_scale=True)

LocateControl(auto_start=True).add_to(m)
Fullscreen(position="topright").add_to(m)

if st.session_state["user_lat"] is not None and st.session_state["user_lon"] is not None:
    folium.Marker(
        location=[st.session_state["user_lat"], st.session_state["user_lon"]],
        popup="📍 موقعك الحالي",
        icon=folium.Icon(color="red", icon="user")
    ).add_to(m)

MeasureControl(position='bottomleft', primary_length_unit='meters', secondary_length_unit='kilometers').add_to(m)

if not df_zones_filtered.empty:
    for _, row in df_zones_filtered.iterrows():
        folium.GeoJson(
            row["geometry"].__geo_interface__,
            style_function=lambda feature: {
                "fillColor": "green",
                "color": "black",
                "weight": 2,
                "fillOpacity": 0.3
            }
        ).add_to(m)

bounds = []
if not df_points_filtered.empty:
    marker_cluster = MarkerCluster(name="نقاط البيانات").add_to(m)

    for _, row in df_points_filtered.iterrows():
        google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['latitude']},{row['longitude']}"
        popup_text = f"""
        <b>📌 الوصف:</b> {row.get('description', 'No description')}<br>
        <b>📍 الإحداثيات:</b> ({row["latitude"]}, {row["longitude"]})<br>
        <a href="{google_maps_url}" target="_blank">🗺️ اضغط هنا للذهاب إلى خرائط Google</a>
        """
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(marker_cluster)
        bounds.append([row["latitude"], row["longitude"]])

if bounds:
    m.fit_bounds(bounds)

folium_static(m)

# تسجيل الخروج التلقائي مع تنبيه
if st.session_state.get("authenticated"):
    last_activity = st.session_state.get("last_activity", time.time())
    inactivity_limit = 1800  # 30 دقيقة
    warning_time = 60  # تحذير قبل 60 ثانية
    
    time_elapsed = time.time() - last_activity
    if time_elapsed > inactivity_limit:
        st.warning("تم تسجيل الخروج تلقائياً بسبب عدم النشاط")
        logging.info(f"تسجيل خروج تلقائي للمستخدم: {st.session_state['user']}")
        st.session_state.clear()
        st.rerun()
    elif time_elapsed > (inactivity_limit - warning_time):
        remaining_time = int(inactivity_limit - time_elapsed)
        st.markdown(
            f"""
            <script>
            setTimeout(function() {{
                alert('سيتم تسجيل الخروج تلقائياً بعد {remaining_time} ثانية بسبب عدم النشاط');
            }}, 1000);
            </script>
            """,
            unsafe_allow_html=True
        )
    st.session_state.last_activity = time.time()
