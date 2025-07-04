# streamlit_app.py

import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="YouTube Video Scraper", layout="wide")
st.title("🎬 YouTube Video Detail & Komentar Scraper")

# --- Fitur Search Video ---
st.subheader("Cari Video di YouTube")
query = st.text_input("Kata kunci pencarian video")

# State untuk hasil pencarian dan video yang dipilih
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = []
if 'selected_video_id' not in st.session_state:
    st.session_state['selected_video_id'] = None

if st.button("Cari Video"):
    if not query:
        st.warning("Masukkan kata kunci pencarian!")
    else:
        with st.spinner("Mencari video..."):
            try:
                resp = requests.post(
                    "http://localhost:5000/search_videos",
                    json={"query": query},
                    timeout=60
                )
                if resp.status_code == 200:
                    st.session_state['search_results'] = resp.json()
                    if not st.session_state['search_results']:
                        st.info("Tidak ada hasil ditemukan.")
                else:
                    st.error("Gagal mencari video.")
            except Exception as e:
                st.error(f"Terjadi error: {e}")

search_results = st.session_state['search_results']

if search_results:
    st.markdown("### Pilih Video")
    n_cols = 3  # jumlah kolom grid
    rows = [search_results[i:i+n_cols] for i in range(0, len(search_results), n_cols)]
    for row in rows:
        cols = st.columns(n_cols)
        for idx, vid in enumerate(row):
            with cols[idx]:
                st.image(vid['thumbnail'], width=220)
                st.markdown(f"**{vid['title']}**")
                st.markdown(f"Channel: {vid['channel_title']}")
                st.markdown(f"Tanggal: {vid['published_at'][:10]}")
                if st.button("Lihat Detail & Komentar", key=vid['video_id']):
                    st.session_state['selected_video_id'] = vid['video_id']

# Render detail & komentar di luar grid agar spinner selalu muncul
selected_video_id = st.session_state.get('selected_video_id')
if selected_video_id:
    video_url = f"https://www.youtube.com/watch?v={selected_video_id}"
    with st.spinner("Mengambil detail & komentar..."):
        try:
            response = requests.post(
                "http://localhost:5000/scrape_comments",
                json={"video_url": video_url},
                timeout=120
            )
            if response.status_code == 200:
                data = response.json()
                video_details = data.get("video_details", {})
                comments = data.get("comments", [])

                st.markdown("---")
                st.subheader("🎥 Detail Video")
                if video_details:
                    cols = st.columns([1, 3])
                    thumbnails = video_details.get('thumbnails', {})
                    thumb_url = thumbnails.get('high', {}).get('url') or thumbnails.get('default', {}).get('url')
                    if thumb_url:
                        cols[0].image(thumb_url, width=220)
                    else:
                        cols[0].write("")
                    with cols[1]:
                        st.markdown(f"### {video_details.get('title', '-')}")
                        st.markdown(f"**Channel:** {video_details.get('channel_title', '-')}")
                        st.markdown(f"**Tanggal Upload:** {video_details.get('published_at', '-')}")
                        st.markdown(f"**Views:** {video_details.get('view_count', '-')}")
                        st.markdown(f"**Likes:** {video_details.get('like_count', '-')}")
                        st.markdown(f"**Jumlah Komentar:** {video_details.get('comment_count', '-')}")
                        st.markdown(f"**Status:** {video_details.get('privacy_status', '-')}")
                        st.markdown(f"**Tags:** {', '.join(video_details.get('tags', [])) or '-'}")
                    st.markdown("**Deskripsi:**")
                    st.info(video_details.get('description', '-'), icon="📝")
                else:
                    st.info("Detail video tidak ditemukan.")

                st.markdown("---")
                st.subheader(f"💬 Komentar ({len(comments)})")
                if comments:
                    df = pd.DataFrame(comments)
                    st.dataframe(df[["Username", "Comment", "Cleaned", "Timestamp"]], use_container_width=True)
                else:
                    st.info("Tidak ada komentar ditemukan.")
            else:
                st.error(f"Error: {response.json().get('error', 'Gagal mengambil data')}")
        except Exception as e:
            st.error(f"Terjadi error: {e}")