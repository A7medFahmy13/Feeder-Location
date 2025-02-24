import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
import hashlib
import os
from streamlit_folium import folium_static
from shapely.wkt import loads as wkt_loads
from shapely.geometry import Point

# ✅ تحميل بيانات المستخدمين
@st.cache_resource
def load_users():
    file_path = "users.xlsx"
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip().str.lower()
        
        required_columns = {"username", "password", "role", "linked_name"}
        if not required_columns.issubset(df.columns):
            st.error("❌ خطأ: ملف المستخدمين غير مكتمل!")
            return {}, {}, {}
        
        df["username"] = df["username"].str.strip().str.lower()
        df["password"] = df["password"].apply(lambda x: hashlib.sha256(str(x).encode()).hexdigest())
        df["role"] = df["role"].str.strip().str.lower()
        df["linked_name"] = df["linked_name"].str.strip().str.lower().replace(" ", "_")
        
        return df.set_index("username")["password"].to_dict(), df.set_index("username")["role"].to_dict(), df.set_index("username")["linked_name"].to_dict()
    except Exception as e:
        st.error(f"⚠️ خطأ: {e}")
        return {}, {}, {}

USERS, USER_ROLES, USER_LINKED_NAMES = load_users()

# ✅ التحقق من تسجيل الدخول
def authenticate(username, password):
    username, password = username.strip().lower(), hashlib.sha256(password.strip().encode()).hexdigest()
    return USERS.get(username) == password

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔑 تسجيل الدخول")
    username = st.text_input("اسم المستخدم").strip().lower()
    password = st.text_input("كلمة المرور", type="password").strip()
    if st.button("تسجيل الدخول"):
        if authenticate(username, password):
            st.session_state.update({
                "authenticated": True,
                "user": username,
                "role": USER_ROLES.get(username, "unknown"),
                "linked_name": USER_LINKED_NAMES.get(username, "unknown")
            })
            st.rerun()
        else:
            st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة!")
    st.stop()
else:
    st.sidebar.button("🔓 تسجيل الخروج", on_click=lambda: st.session_state.update({"authenticated": False}))
    st.title("🌍 Aseer Monitoring Map")
    st.write(f"مرحبًا، {st.session_state['user']} 👋")

# ✅ طباعة المسار الحالي في Streamlit Cloud لمعرفة مكان تشغيل التطبيق
st.write("📂 المسار الحالي:", os.getcwd())

# ✅ تحميل بيانات المناطق فقط (دون ملف النقاط)
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
        return gpd.GeoDataFrame()

df_zones = load_zones()

# ✅ التحقق مما إذا كان ملف النقاط موجودًا
file_path = os.path.join(os.getcwd(), "split_Coordinates_Data.csv")
df_points = gpd.GeoDataFrame()

if os.path.exists(file_path):
    try:
        df_points = pd.read_csv(file_path, encoding="utf-8")
        df_points.columns = df_points.columns.str.strip().str.lower()
        df_points["geometry"] = df_points.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
        df_points = gpd.GeoDataFrame(df_points, geometry="geometry")
    except Exception as e:
        st.error(f"⚠️ خطأ: تعذر تحميل بيانات النقاط: {e}")
else:
    st.warning("⚠️ لم يتم العثور على ملف 'split_Coordinates_Data.csv'. يرجى رفعه يدويًا.")
    uploaded_file = st.file_uploader("📂 قم برفع ملف البيانات", type=["csv"])
    if uploaded_file:
        df_points = pd.read_csv(uploaded_file, encoding="utf-8")
        df_points.columns = df_points.columns.str.strip().str.lower()
        df_points["geometry"] = df_points.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
        df_points = gpd.GeoDataFrame(df_points, geometry="geometry")

# ✅ تصفية البيانات بناءً على المستخدم
user_role = st.session_state["role"]
linked_name = st.session_state["linked_name"]

if user_role != "admin":
    relevant_columns = [col for col in ["om_supervisor", "mv_supervisor", user_role] if col in df_zones.columns]
    if relevant_columns:
        df_zones = df_zones[df_zones[relevant_columns].astype(str).apply(lambda row: row.str.contains(linked_name, na=False, case=False)).any(axis=1)]

# ✅ اختيار المناطق
selected_zones = st.multiselect("اختر المناطق", df_zones["zone"].unique())

df_zones_filtered = gpd.GeoDataFrame()
df_points_filtered = gpd.GeoDataFrame()

if selected_zones:
    df_zones_filtered = df_zones[df_zones["zone"].isin(selected_zones)].copy()
    df_zones_filtered = df_zones_filtered.explode(index_parts=True)

    if not df_zones_filtered.empty:
        df_points_filtered = df_points[df_points.geometry.within(df_zones_filtered.unary_union)]

    with st.expander(f"📊 بيانات المناطق ({len(df_zones_filtered)})", expanded=True):
        st.dataframe(df_zones_filtered.drop(columns=["geometry"], errors="ignore"))

    with st.expander(f"📍 بيانات النقاط ({len(df_points_filtered)})", expanded=True):
        st.dataframe(df_points_filtered.drop(columns=["geometry"], errors="ignore"))

# ✅ إعداد وعرض الخريطة
st.subheader("🌍 الخريطة التفاعلية")
m = folium.Map(location=[18.2, 42.5], zoom_start=8)

if not df_zones_filtered.empty:
    for _, row in df_zones_filtered.iterrows():
        folium.GeoJson(row["geometry"].__geo_interface__).add_to(m)

    bounds = df_zones_filtered.total_bounds
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

for _, row in df_points_filtered.iterrows():
    folium.Marker(
        location=[row["latitude"], row["longitude"]],
        popup=f"📍 {row.get('description', 'No description')}",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

folium_static(m)
