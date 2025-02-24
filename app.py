import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
import hashlib
from streamlit_folium import folium_static
from shapely.wkt import loads as wkt_loads
from shapely.geometry import Point

# ✅ تحميل بيانات المستخدمين مع تشفير كلمات المرور
@st.cache_data
def load_users():
    file_path = "users.xlsx"
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip().str.lower()
    
    required_columns = {"username", "password", "role", "linked_name"}
    if not required_columns.issubset(df.columns):
        st.error("❌ خطأ: ملف المستخدمين غير مكتمل. تأكد من صحة البيانات!")
        return {}, {}, {}
    
    df["username"] = df["username"].str.strip().str.lower()
    df["password"] = df["password"].apply(lambda x: hashlib.sha256(str(x).encode()).hexdigest())
    df["role"] = df["role"].str.strip().str.lower()
    df["linked_name"] = df["linked_name"].str.strip().str.lower().replace(" ", "_")
    
    users_dict = df.set_index("username")["password"].to_dict()
    user_roles_dict = df.set_index("username")["role"].to_dict()
    user_linked_names_dict = df.set_index("username")["linked_name"].to_dict()
    
    return users_dict, user_roles_dict, user_linked_names_dict

USERS, USER_ROLES, USER_LINKED_NAMES = load_users()

# ✅ التحقق من تسجيل الدخول
def authenticate(username, password):
    username, password = username.strip().lower(), hashlib.sha256(password.strip().encode()).hexdigest()
    return USERS.get(username) == password

# ✅ واجهة تسجيل الدخول
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

# ✅ تحميل البيانات من ملف Excel بدلاً من GeoJSON
@st.cache_data
def load_stored_data():
    try:
        df_zones = pd.read_excel("New Asser_Boundaries.xlsx")
        df_zones.columns = df_zones.columns.str.strip().str.lower()
        
        if "wkt" in df_zones.columns:
            df_zones["geometry"] = df_zones["wkt"].apply(lambda x: wkt_loads(x) if isinstance(x, str) else None)
            df_zones = gpd.GeoDataFrame(df_zones, geometry="geometry")
        else:
            st.error("❌ خطأ: ملف `New Asser_Boundaries.xlsx` لا يحتوي على عمود `WKT`.")
    except Exception as e:
        st.error(f"⚠️ خطأ في تحميل ملف `New Asser_Boundaries.xlsx`: {e}")
        df_zones = gpd.GeoDataFrame()
    
    try:
        df_points = pd.read_csv("split_Coordinates_Data.csv")
        df_points.columns = df_points.columns.str.strip().str.lower()
        df_points["geometry"] = df_points.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
        df_points = gpd.GeoDataFrame(df_points, geometry="geometry")
    except Exception as e:
        st.error(f"⚠️ خطأ: تعذر تحميل ملف `split_Coordinates_Data.csv`: {e}")
        df_points = gpd.GeoDataFrame()
    
    return df_zones, df_points

# تحميل البيانات
df_zones, df_points = load_stored_data()

# ✅ تصفية البيانات بناءً على دور المستخدم
user_role = st.session_state["role"]
linked_name = st.session_state["linked_name"]
if user_role != "admin":
    filter_columns = ["om_supervisor", "mv_supervisor", user_role]
    relevant_columns = [col for col in filter_columns if col in df_zones.columns]
    if relevant_columns:
        filter_condition = df_zones[relevant_columns].apply(lambda row: any(row.astype(str).str.contains(linked_name, na=False, case=False)), axis=1)
        df_zones = df_zones[filter_condition]

# ✅ فلتر لاختيار المناطق المتاحة للمستخدم فقط
available_zones = df_zones["zone"].unique()
selected_zones = st.multiselect("اختر المناطق", available_zones)

if selected_zones:
    df_zones = df_zones[df_zones["zone"].isin(selected_zones)]
    df_points = df_points[df_points.geometry.within(df_zones.unary_union)]
    feeder_ids = df_points["feeder-id"].dropna().unique()
    selected_feeder = st.multiselect("اختر Feeder ID", feeder_ids)
    if selected_feeder:
        df_points = df_points[df_points["feeder-id"].isin(selected_feeder)]

    st.subheader(f"📊 بيانات المنطقة (عدد: {len(df_zones)})")
    st.dataframe(df_zones.drop(columns=["geometry"], errors='ignore'))

    st.subheader(f"📍 بيانات النقاط (عدد: {len(df_points)})")
    st.dataframe(df_points.drop(columns=["geometry"], errors='ignore'))

    # ✅ إنشاء الخريطة التفاعلية مع الاتجاهات
    st.subheader("🌍 الخريطة التفاعلية")
    m = folium.Map(location=[18.2, 42.5], zoom_start=8)

    for _, row in df_zones.iterrows():
        if row["geometry"] and row["geometry"].geom_type == "Polygon":
            folium.GeoJson(row["geometry"], name=row.get("zone", "Unknown Zone")).add_to(m)

    for _, row in df_points.iterrows():
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=row.get("description", "No description"),
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    folium_static(m)
