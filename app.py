import streamlit as st
import asyncio
from client import process

st.title("🤖 Agent IA + MCP")

user_input = st.text_area("Pose ta question")

if st.button("Envoyer"):

    if user_input.strip() == "":
        st.warning("Entre une question")
    else:
        result = asyncio.run(process(user_input))
        st.success("Réponse :")
        st.write(result)
