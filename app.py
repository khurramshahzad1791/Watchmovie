import streamlit as st
import requests
import re
from datetime import datetime

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
st.set_page_config(page_title="FAST Stream Hub - Free Movies & Live TV", page_icon="🎬", layout="wide")

st.title("🎬 FAST Stream Hub")
st.caption("Watch full movies and live TV from Tubi, Plex, Pluto, Crackle, Xumo, Popcornflix, Kanopy, Roku, Samsung — all in one place. 100% free, no account required.")

# -------------------------------
# RAPIDAPI SETUP (Streaming Availability API)
# -------------------------------
RAPIDAPI_KEY = st.secrets.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "streaming-availability.p.rapidapi.com"

if not RAPIDAPI_KEY:
    st.error("⚠️ Missing RapidAPI key. Please add it to your Streamlit secrets (RAPIDAPI_KEY).")
    st.stop()

# -------------------------------
# M3U PLAYLIST URLs (Live TV) – free, auto-updated
# -------------------------------
PLAYLISTS = {
    "Pluto TV": "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_us.m3u",
    "Samsung TV Plus": "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/samsungtvplus_us.m3u",
    "Plex": "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plex_us.m3u",
    "Tubi": "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/tubi_all.m3u",
    "Roku Channel": "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/roku_all.m3u",
    "Xumo": "https://raw.githubusercontent.com/BuddyChewChew/xumo-playlist-generator/main/xumo_us.m3u"
}

# -------------------------------
# FREE STREAMING SERVICES (On-Demand)
# -------------------------------
FREE_SERVICES = {
    "Tubi": "https://tubitv.com",
    "Plex": "https://watch.plex.tv",
    "Pluto TV": "https://pluto.tv",
    "Crackle": "https://www.crackle.com",
    "Xumo Play": "https://play.xumo.com",
    "Popcornflix": "https://popcornflix.com",
    "Kanopy": "https://www.kanopy.com",
    "Roku Channel": "https://therokuchannel.roku.com"
}

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
@st.cache_data(ttl=3600)
def fetch_m3u_playlist(url):
    """Fetch and parse M3U playlist for live TV channels"""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            content = response.text
            channels = []
            lines = content.split('\n')
            current_channel = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('#EXTINF:'):
                    name_match = re.search(r'#EXTINF:-1.*?,(.*?)$', line)
                    if name_match:
                        current_channel['name'] = name_match.group(1).strip()
                    logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                    if logo_match:
                        current_channel['logo'] = logo_match.group(1)
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    if group_match:
                        current_channel['group'] = group_match.group(1)
                elif line.startswith('http') and current_channel:
                    current_channel['stream_url'] = line
                    channels.append(current_channel.copy())
                    current_channel = {}
            
            return channels[:200]  # Limit for performance
        return []
    except Exception as e:
        st.error(f"Error fetching playlist: {e}")
        return []

@st.cache_data(ttl=86400)
def search_movies_rapidapi(query):
    """Search for movies using Streaming Availability API (RapidAPI)"""
    try:
        url = "https://streaming-availability.p.rapidapi.com/search/title"
        querystring = {"title": query, "country": "us", "show_type": "movie"}
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # Return all results (limit to 20)
            return data if isinstance(data, list) else [data] if data else []
        else:
            st.error(f"API Error: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def get_deep_link(movie_data, service_name):
    """Extract deep link for a specific free service from the API response"""
    if not movie_data or 'streamingInfo' not in movie_data:
        return None
    
    # Map service names to API service IDs (lowercase)
    service_map = {
        "tubi": "tubi",
        "plex": "plex",
        "pluto tv": "pluto",
        "crackle": "crackle",
        "xumo play": "xumo",
        "popcornflix": "popcornflix",
        "kanopy": "kanopy",
        "roku channel": "roku"
    }
    
    service_key = service_map.get(service_name.lower())
    if not service_key:
        return None
    
    # Check US streaming info
    streaming_info = movie_data.get('streamingInfo', {})
    us_info = streaming_info.get('us', {})
    
    if service_key in us_info:
        return us_info[service_key].get('link')
    return None

# -------------------------------
# MAIN UI
# -------------------------------
tab1, tab2, tab3 = st.tabs(["📡 Live TV", "🎬 Free Movies", "🔍 Search"])

# -------------------------------
# TAB 1: LIVE TV
# -------------------------------
with tab1:
    st.subheader("📡 Live TV Channels")
    st.caption("Watch live channels from Pluto, Plex, Tubi, Roku, Samsung, Xumo — all free, ad-supported.")
    
    selected_service = st.selectbox("Select Service", list(PLAYLISTS.keys()))
    
    with st.spinner(f"Loading {selected_service} channels..."):
        channels = fetch_m3u_playlist(PLAYLISTS[selected_service])
    
    if channels:
        cols_per_row = 3
        for i in range(0, min(len(channels), 60), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx < len(channels):
                    channel = channels[idx]
                    with col:
                        if channel.get('logo'):
                            st.image(channel['logo'], width=80)
                        st.markdown(f"**{channel.get('name', 'Unknown')[:50]}**")
                        if channel.get('group'):
                            st.caption(f"📁 {channel['group']}")
                        stream_url = channel.get('stream_url', '#')
                        st.markdown(f"[▶️ Watch Now]({stream_url})", unsafe_allow_html=True)
                        st.divider()
    else:
        st.info(f"No channels available for {selected_service}. Playlists update daily.")

# -------------------------------
# TAB 2: FREE MOVIES (Direct Service Access)
# -------------------------------
with tab2:
    st.subheader("🎬 Browse Free Streaming Services")
    st.caption("Click any service to start watching thousands of free movies and shows.")
    
    # Display services as buttons in a grid
    cols = st.columns(4)
    for idx, (service, url) in enumerate(FREE_SERVICES.items()):
        with cols[idx % 4]:
            st.markdown(f"### {service}")
            st.markdown(f"[Open {service} →]({url})")
            st.caption("Free, ad-supported")
    
    st.divider()
    st.markdown("**Tip:** Use the **Search** tab to find specific movies and get direct watch links.")

# -------------------------------
# TAB 3: SEARCH (Powered by RapidAPI)
# -------------------------------
with tab3:
    st.subheader("🔍 Search Movies & TV Shows")
    st.caption("Find any movie and get direct links to watch for free on Tubi, Plex, Pluto, Crackle, and more.")
    
    search_query = st.text_input("Enter movie title", placeholder="e.g., The Matrix, Inception, Parasite...")
    
    if search_query:
        with st.spinner(f"Searching for '{search_query}'..."):
            results = search_movies_rapidapi(search_query)
        
        if results and len(results) > 0:
            st.markdown(f"### Found {len(results)} results for '{search_query}'")
            
            for movie in results[:10]:  # Limit to 10 for readability
                title = movie.get('title', 'Unknown')
                year = movie.get('year', 'N/A')
                imdb_rating = movie.get('imdbRating', 'N/A')
                overview = movie.get('overview', 'No description available.')
                poster = movie.get('posterPath', '')
                poster_url = f"https://image.tmdb.org/t/p/w500{poster}" if poster else None
                
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if poster_url:
                            st.image(poster_url, width=150)
                        else:
                            st.image("https://via.placeholder.com/150x225?text=No+Poster", width=150)
                    
                    with col2:
                        st.markdown(f"### {title} ({year})")
                        st.caption(f"⭐ IMDb: {imdb_rating}")
                        st.markdown(overview[:300] + "..." if len(overview) > 300 else overview)
                        
                        # Find which free services have this movie
                        available_services = []
                        for service_name in FREE_SERVICES.keys():
                            link = get_deep_link(movie, service_name)
                            if link:
                                available_services.append((service_name, link))
                        
                        if available_services:
                            st.markdown("**Watch for free on:**")
                            for service_name, link in available_services:
                                st.markdown(f"- [{service_name}]({link})")
                        else:
                            st.markdown("**Not available on free services.** Try checking the service homepages below.")
                            for service_name, url in FREE_SERVICES.items():
                                st.markdown(f"- [{service_name}]({url})")
                    st.divider()
        else:
            st.info("No movies found. Try a different title.")

# -------------------------------
# FOOTER / ABOUT (minimal)
# -------------------------------
st.divider()
st.caption(f"FAST Stream Hub • Aggregates free ad-supported content • Updated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
