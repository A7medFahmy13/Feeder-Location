import streamlit as st
import time

# إعداد الصفحة
st.set_page_config(page_title="🎬 انتهى العرض", page_icon="🌙", layout="wide")

# 🌙 إضافة صورة "رمضان كريم" في الأعلى
st.markdown(
    """
    <h1 style='text-align: center; color: gold; font-size: 50px;'>🌙 رمضان كريم 🌙</h1>
    <p style='text-align: center; font-size: 20px; color: white; background-color: darkblue; padding: 10px; border-radius: 10px;'>
    نتمنى لكم شهرًا مليئًا بالخيرات والبركات! 🌟
    </p>
    """, unsafe_allow_html=True
)

# 📽️ إضافة صورة أو GIF لعروض سينمائية
st.image("https://media.giphy.com/media/l0HlPjezGYinRx4ta/giphy.gif", use_column_width=True)

# 🎬 عنوان العرض انتهى
st.markdown(
    """
    <h1 style='text-align: center; color: blue; font-size: 40px;'>🎬 انتهى العرض</h1>
    """, unsafe_allow_html=True
)

# 🎉 شكرًا لمشاهدتك العرض
st.markdown(
    """
    <h2 style='text-align: center; color: green;'>✨ شكرًا لمشاهدتك العرض! ✨</h2>
    <p style='text-align: center; font-size: 18px;'>نتمنى أن يكون قد نال إعجابك 💖</p>
    """, unsafe_allow_html=True
)

# 🎭 إضافة تأثير متحرك (انتظرونا في العروض القادمة!)
st.markdown(
    """
    <div style="text-align: center; font-size: 22px; font-weight: bold; color: red; animation: blinker 1.5s linear infinite;">
    🎬 انتظرونا في العروض القادمة! 🚀
    </div>
    <style>
    @keyframes blinker {
        50% { opacity: 0; }
    }
    </style>
    """, unsafe_allow_html=True
)

# ⏳ تأثير العد التنازلي قبل إعادة التشغيل
if st.button("🔄 إعادة التشغيل"):
    with st.spinner("🔄 جاري إعادة التشغيل ..."):
        time.sleep(2)  # تأخير بسيط ليشعر المستخدم بواقعية إعادة التشغيل
    st.rerun()

# 🌟 خلفية جذابة للصفحة
st.markdown(
    """
    <style>
    body {
        background-color: #f4f4f4;
    }
    </style>
    """, unsafe_allow_html=True
)
