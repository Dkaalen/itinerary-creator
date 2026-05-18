import streamlit as st

st.set_page_config(
    page_title="Itinerary Creator",
    page_icon="🧭",
    layout="wide"
)

st.title("Itinerary Creator")

st.write(
    "Paste raw Excel itinerary text below. "
    "The app will later turn it into a polished itinerary."
)

raw_text = st.text_area(
    "Raw Excel text",
    height=300,
    placeholder="Paste itinerary rows here..."
)

if st.button("Generate itinerary"):
    if raw_text.strip():
        st.success("Text received. Next we will teach the app how to understand it.")
        st.text(raw_text)
    else:
        st.warning("Please paste some itinerary text first.")