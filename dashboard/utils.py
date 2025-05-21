import streamlit as st
import os

def display_logo():
    """Display the logo in the top right corner"""
    # Criar um container para a logo no canto direito
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 0.2])
        with col3:
            # Obter caminho da logo
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(current_dir, "logo.png")
            # Exibir logo
            st.image(logo_path, width=80)
