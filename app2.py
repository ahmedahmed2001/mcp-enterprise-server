import streamlit as st
from client2 import process

st.title("🤖 Agent IA + Serveur MCP")
st.caption("Connecté au serveur MCP sur localhost:8001")

user_input = st.text_input("Pose ta question")

if st.button("Envoyer"):
    with st.spinner("L'IA réfléchit..."):
        result = process(user_input)
    st.success("Réponse :")
    st.write(result)
