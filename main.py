import streamlit as st
from pathlib import Path


def main():
    st.title("Hello from Quick wins!")
    st.switch_page(Path("pages") / "1_Crowdstrike_CSV_Parser.py")


if __name__ == "__main__":
    main()
