import streamlit as st
from lib import api
from lib.theme import inject_base_css, render_sidebar_brand, section_label, pipeline_diagram, status_badge

st.set_page_config(page_title="OrderOps AI - Dashboard", layout="wide")
inject_base_css()
render_sidebar_brand()

st.title("Dashboard")
st.caption("Order triage and negotiation overview")

# --- KPIs -------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

try:
    metrics = api.get_revenue_recovery()
    recovery_pct = f"{metrics['recovery_rate'] * 100:.0f}%"
    recovery_hint = f"{metrics['accepted']} of {metrics['total_negotiations']} accepted"
except api.ApiError as e:
    metrics = None
    recovery_pct = "-"
    recovery_hint = str(e)

with col1:
    st.markdown('<div class="oo-card">', unsafe_allow_html=True)
    st.metric("Revenue recovery rate", recovery_pct)
    st.caption(recovery_hint)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="oo-card">', unsafe_allow_html=True)
    st.metric("Active orders", "-")
    st.caption("Wire up a /orders list endpoint")
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown('<div class="oo-card">', unsafe_allow_html=True)
    st.metric("Pending negotiations", "-")
    st.caption("Awaiting customer response")
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown('<div class="oo-card">', unsafe_allow_html=True)
    st.metric("Avg processing time", "-")
    st.caption("Intake to fulfillment/negotiation")
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# --- Pipeline diagram ---------------------------------------------------
section_label("Agent pipeline")
st.graphviz_chart(pipeline_diagram(), use_container_width=True)

st.write("")

# --- Recent negotiation history ------------------------------------------
section_label("Recent negotiation history")
try:
    history = api.get_all_negotiations(limit=10)
except api.ApiError as e:
    st.warning(str(e))
    history = []

if not history:
    st.markdown(
        '<div class="oo-card">No negotiations yet - create an order for an '
        'out-of-stock product on the Orders page to see one here.</div>',
        unsafe_allow_html=True,
    )
else:
    for n in history:
        st.markdown('<div class="oo-card">', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**{n['customer_name']}** - {n['original_product_name']} -> {n['alternative_product_name']}")
            st.caption(f"{n['discount_pct']}% off - via {n['channel']} - order {n['order_id'][:8]}...")
        with c2:
            st.markdown(status_badge(n["customer_response"]), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

st.write("")
st.markdown(
    """
    <div class="oo-card">
    This dashboard talks to the FastAPI backend at <code>API_BASE_URL</code>
    (set in <code>.env</code>, defaults to <code>http://localhost:8000</code>).
    Use the Orders page in the sidebar to create a test order or look one up
    by ID, and watch it move through the pipeline above.
    </div>
    """,
    unsafe_allow_html=True,
)
