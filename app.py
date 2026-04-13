import streamlit as st
import requests
import json
import re
from datetime import datetime

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
st.set_page_config(page_title="FAST Stream Hub - All Free Movies & Live TV", page_icon="🎬", layout="wide")

st.title("🎬 FAST Stream Hub")
st.caption("Watch full movies and live TV from Plex, Tubi, Pluto, Crackle, Xumo, Popcornflix, Kanopy, Roku, Samsung TV Plus — all in one place. 100% free, no account required.")

# -------------------------------
# API SETUP
# -------------------------------
# Retrieve your API keys from Streamlit's secrets management
RAPIDAPI_KEY = st.secrets.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "streaming-availability.p.rapidapi.com"

TMDB_API_KEY = st.secrets.get("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# -------------------------------
# M3U PLAYLIST URLs (Live TV)
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
# MOVIE SOURCES (On-Demand)
# -------------------------------
MOVIE_SOURCES = {
    "Plex": "https://watch.plex.tv",
    "Tubi": "https://tubitv.com",
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
    """Fetch and parse M3U playlist to extract channel info and stream URLs"""
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
                    # Extract channel name
                    name_match = re.search(r'#EXTINF:-1.*?,(.*?)$', line)
                    if name_match:
                        current_channel['name'] = name_match.group(1).strip()
                    # Extract logo
                    logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                    if logo_match:
                        current_channel['logo'] = logo_match.group(1)
                    # Extract group
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    if group_match:
                        current_channel['group'] = group_match.group(1)
                elif line.startswith('http') and current_channel:
                    current_channel['stream_url'] = line
                    channels.append(current_channel.copy())
                    current_channel = {}
            
            # Return all channels, limit to 200 per service for performance
            return channels[:200]
        return []
    except Exception as e:
        st.error(f"Error fetching playlist: {e}")
        return []

@st.cache_data(ttl=86400)
def search_streaming_api(query):
    """Search for a movie and get its streaming availability using the Streaming Availability API."""
    if not RAPIDAPI_KEY:
        st.warning("RapidAPI key is missing. Please add it to your secrets.")
        return []
    try:
        # The API endpoint for searching by title
        url = "https://streaming-availability.p.rapidapi.com/search/title"
        querystring = {"title": query, "country": "us", "show_type": "movie"}
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # The API returns a list of results; we'll take the top one as the best match
            if data and len(data) > 0:
                return data[0]  # Return the first (best) match
            else:
                return None
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Search API error: {e}")
        return None

@st.cache_data(ttl=86400)
def search_tmdb(query):
    """Search TMDB for movies/TV shows to get rich metadata"""
    if not TMDB_API_KEY:
        return []
    try:
        params = {
            'api_key': TMDB_API_KEY,
            'query': query,
            'language': 'en-US',
            'page': 1
        }
        response = requests.get(f"{TMDB_BASE_URL}/search/multi", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])[:20]
        return []
    except Exception as e:
        st.error(f"TMDB search error: {e}")
        return []

@st.cache_data(ttl=86400)
def get_trending():
    """Get trending movies from TMDB"""
    if not TMDB_API_KEY:
        return []
    try:
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en-US',
            'page': 1
        }
        response = requests.get(f"{TMDB_BASE_URL}/trending/movie/day", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])[:12]
        return []
    except Exception as e:
        st.error(f"Error fetching trending: {e}")
        return []

def get_streaming_link(streaming_info, service_name):
    """Extract the deep link for a specific service from the streaming info."""
    if not streaming_info or 'streamingInfo' not in streaming_info:
        return None
    # The streamingInfo is organized by country (e.g., 'us')
    for country, services in streaming_info['streamingInfo'].items():
        if service_name.lower() in services:
            return services[service_name.lower()].get('link')
    return None

# -------------------------------
# MAIN UI
# -------------------------------

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📡 Live TV", "🎬 Free Movies", "🔍 Search", "ℹ️ About"])

# -------------------------------
# TAB 1: LIVE TV
# -------------------------------
with tab1:
    # ... (Keep the existing Live TV code exactly as it was)
    st.subheader("📡 Live TV Channels")
    st.caption("Watch live channels from Pluto, Plex, Tubi, Roku, Samsung, Xumo — all free, ad-supported. Click any channel to start streaming.")
    
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
        st.info(f"No channels available for {selected_service} at the moment. Playlists update daily.")

# -------------------------------
# TAB 2: FREE MOVIES (Embedded)
# -------------------------------
with tab2:
    # ... (Keep the existing Free Movies code exactly as it was)
    st.subheader("🎬 Watch Full Movies for Free")
    st.caption("Click any movie to watch instantly — no account, no subscription.")
    
    st.markdown("### 🔥 Trending Today")
    trending = get_trending()
    if trending:
        cols = st.columns(4)
        for idx, movie in enumerate(trending):
            with cols[idx % 4]:
                poster_path = movie.get('poster_path')
                if poster_path:
                    st.image(f"{TMDB_IMAGE_BASE}{poster_path}", use_container_width=True)
                st.markdown(f"**{movie.get('title', 'Unknown')}**")
                st.caption(f"⭐ {movie.get('vote_average', 'N/A')} • {movie.get('release_date', 'N/A')[:4]}")
                
                with st.expander("▶️ Watch on"):
                    for service in MOVIE_SOURCES.keys():
                        st.markdown(f"- [{service}]({MOVIE_SOURCES[service]})")
                st.divider()
    
    st.markdown("### 🚀 Quick Access to Free Streaming Services")
    service_cols = st.columns(4)
    for idx, (service, url) in enumerate(MOVIE_SOURCES.items()):
        with service_cols[idx % 4]:
            st.markdown(f"#### {service}")
            st.markdown(f"[Open {service} →]({url})")
            st.caption("Thousands of free movies & shows")

# -------------------------------
# TAB 3: SEARCH (ENHANCED)
# -------------------------------
with tab3:
    st.subheader("🔍 Search Movies & TV Shows")
    st.caption("Find any movie and see where you can watch it for free.")
    
    search_query = st.text_input("Enter movie or show name", placeholder="e.g., Inception, The Office, Parasite...")
    
    if search_query:
        with st.spinner("Searching..."):
            results = search_tmdb(search_query)
            streaming_data = search_streaming_api(search_query)
        
        if results:
            st.markdown(f"### Found {len(results)} results for '{search_query}'")
            
            for result in results:
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        poster_path = result.get('poster_path')
                        if poster_path:
                            st.image(f"{TMDB_IMAGE_BASE}{poster_path}", width=120)
                        else:
                            st.image("https://via.placeholder.com/120x180?text=No+Poster", width=120)
                    
                    with col2:
                        title = result.get('title') or result.get('name', 'Unknown')
                        media_type = "Movie" if result.get('media_type') == 'movie' else "TV Show"
                        year = result.get('release_date', result.get('first_air_date', 'N/A'))[:4]
                        st.markdown(f"### {title} ({year})")
                        st.caption(f"{media_type} • ⭐ {result.get('vote_average', 'N/A')}/10")
                        st.markdown(result.get('overview', 'No description available.')[:200] + "...")
                        
                        # ENHANCED: Watch buttons using streaming API deep links
                        st.markdown("**Watch for free on:**")
                        # First, try to get links from the streaming API
                        if streaming_data and title.lower() == streaming_data.get('title', '').lower():
                            for service in MOVIE_SOURCES.keys():
                                # The API uses service IDs like 'tubi', 'plex', 'pluto' etc.
                                # Convert service name to lowercase and check
                                service_key = service.lower()
                                if service_key in streaming_data.get('streamingInfo', {}).get('us', {}):
                                    link = streaming_data['streamingInfo']['us'][service_key].get('link')
                                    if link:
                                        st.markdown(f"- [{service}]({link})")
                                    else:
                                        st.markdown(f"- [{service}]({MOVIE_SOURCES[service]})")
                                else:
                                    # Fallback to the service homepage if no direct link
                                    st.markdown(f"- [{service}]({MOVIE_SOURCES[service]})")
                        else:
                            # Fallback: Show standard service links
                            for service, url in MOVIE_SOURCES.items():
                                st.markdown(f"- [{service}]({url})")
                    st.divider()
        else:
            st.info("No results found. Try a different search term.")

# -------------------------------
# TAB 4: ABOUT
# -------------------------------
with tab4:
    # ... (Keep the existing About code exactly as it was)
    st.subheader("ℹ️ About FAST Stream Hub")
    st.markdown("""
    **What is this?**
    
    FAST Stream Hub is a free dashboard that aggregates content from all major free ad-supported streaming services. You can watch:
    
    - **Live TV channels** from Pluto, Plex, Tubi, Roku, Samsung, and Xumo
    - **Full movies** from Crackle, Popcornflix, Kanopy, and more
    - **Search across all services** to find where to watch any movie
    
    **Is this legal?**
    
    Yes! This app does not host any video files. It simply provides links and embeds to official streaming services that are legally free (ad-supported). All content is provided by the services themselves.
    
    **How is this free?**
    
    The FAST services (Free Ad-Supported Streaming TV) generate revenue through ads, just like traditional TV. You watch commercials, they pay for the content.
    
    **Services included:**
    
    | Service | Type | Content |
    |---------|------|---------|
    | Plex | Live TV + On-Demand | 50,000+ free movies & shows |
    | Tubi | On-Demand | 40,000+ movies & TV series |
    | Pluto TV | Live TV | 250+ live channels |
    | Crackle | On-Demand | Hollywood movies & originals |
    | Xumo Play | Live TV + On-Demand | 350+ live channels, 15,000+ titles |
    | Popcornflix | On-Demand | Action, comedy, horror films |
    | Kanopy | On-Demand | Curated films (requires library card) |
    | Roku Channel | Live TV + On-Demand | 80,000+ free movies & shows |
    | Samsung TV Plus | Live TV | 200+ live channels |
    
    **Last updated:** """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
