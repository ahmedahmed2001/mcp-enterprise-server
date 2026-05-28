import streamlit as st
from client_http import process

st.title("Agent IA + MCP HTTP")

user_input = st.text_input("Pose ta question")

if st.button("Envoyer"):

    result = process(user_input)

    st.success("Réponse :")
    st.write(result)
