import pymysql
import streamlit as st

def get_connection():
    return pymysql.connect(
        host=st.secrets["host"],
        user="avnadmin",
        password=st.secrets["password"],  # 🔴 add password
        database="property_management",
        port=17028,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

