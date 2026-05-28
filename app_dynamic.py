import streamlit as st
from client_dynamic import process

st.title("🤖 Agent IA + Serveur MCP (Dynamique)")
st.caption("Les outils sont découverts automatiquement depuis le serveur")

# Afficher les outils disponibles
with st.expander("🔍 Outils disponibles"):
    from client_dynamic import discover_tools
    tools = discover_tools()
    for tool in tools:
        func = tool['function']
        st.write(f"**{func['name']}** : {func['description'][:100]}...")

user_input = st.text_input("Pose ta question")

if st.button("Envoyer"):
    with st.spinner("L'IA réfléchit..."):
        result = process(user_input)
    st.success("Réponse :")
    st.write(result)
