import logging

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from streamlit_option_menu import option_menu
from yaml.loader import SafeLoader

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@st.cache_resource
def load_config():
    with open('assets/config.yaml', encoding='utf-8') as f:
        return yaml.load(f, Loader=SafeLoader)


def setup_authenticator(config):
    return stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
    )


# ---------------------------------------------------------------------------
# Navigation — add new tools here
# ---------------------------------------------------------------------------
# Each entry: (label, bootstrap-icon)
# Icons: https://icons.getbootstrap.com/
USER_TOOLS = [
    ("Home", "house"),
    ("Dashboard", "bar-chart-line"),
    # ("ATD Predictor", "bar-chart"),  ← add new tools here
]


def render_sidebar(authenticator, name, user_type):
    with st.sidebar:
        st.markdown(f"Welcome, **{name}**")
        authenticator.logout(location='sidebar')
        st.title('Navigation')

        selected = option_menu(
            menu_title=None,
            options=[t[0] for t in USER_TOOLS],
            icons=[t[1] for t in USER_TOOLS],
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "nav-link-selected": {"background-color": UBER_GREEN, "color": "#000000"},
            },
            menu_icon="list",
            default_index=0,
            key=f"{user_type}_menu",
        )

    return selected


def render_tool(selected, name):
    if selected == "Home":
        from tools.home.views.home_view import home_view
        home_view(name)

    elif selected == "Dashboard":
        from tools.dashboard.views.dashboard_view import (
            dashboard_view,
        )
        dashboard_view()

    # Add new tools below:
    # elif selected == "ATD Predictor":
    #     from tools.atd_predictor.views.atd_view import atd_view
    #     atd_view()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

UBER_GREEN = "#06C167"


def inject_css():
    st.markdown(
        f"""
        <style>
        /* Buttons */
        .stButton > button {{
            background-color: {UBER_GREEN};
            color: #000000;
            border: none;
        }}
        .stButton > button:hover {{
            background-color: #04a557;
            color: #000000;
        }}
        /* Form submit buttons */
        .stFormSubmitButton > button {{
            background-color: {UBER_GREEN};
            color: #000000;
            border: none;
        }}
        /* Active/focus outlines */
        .stTextInput > div > div > input:focus,
        .stSelectbox > div > div:focus {{
            border-color: {UBER_GREEN} !important;
            box-shadow: 0 0 0 1px {UBER_GREEN} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="Uber Eats ATD",
        page_icon="🛵",
        initial_sidebar_state="expanded",
    )
    inject_css()

    config = load_config()
    authenticator = setup_authenticator(config)

    authenticator.login(location='main')
    name = st.session_state.get('name')
    authentication_status = st.session_state.get('authentication_status')
    username = st.session_state.get('username')

    if authentication_status:
        user_type = config['credentials']['usernames'][username]['type']
        selected = render_sidebar(authenticator, name, user_type)
        render_tool(selected, name)

    elif authentication_status is False:
        st.error('Incorrect username or password.')

    else:
        st.warning('Please enter your username and password.')


if __name__ == "__main__":
    main()
