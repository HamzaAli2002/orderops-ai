import streamlit as st
from lib import api
from lib.theme import inject_base_css, render_sidebar_brand, section_label, status_badge

st.set_page_config(page_title="OrderOps AI - Negotiations", layout="wide")
inject_base_css()
render_sidebar_brand()

st.title("Negotiations")
st.caption("Full negotiation history, and a place to respond on a customer's behalf")

# --- Full history, across every order -------------------------------------
section_label("All negotiations")

try:
    history = api.get_all_negotiations(limit=100)
except api.ApiError as e:
    st.error(str(e))
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
            st.caption(
                f"{n['discount_pct']}% off - via {n['channel']} - order {n['order_id'][:8]}... "
                f"- sent {n['message_sent_at'] or '-'}"
            )
        with c2:
            st.markdown(status_badge(n["customer_response"]), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

st.write("")
st.write("")

# --- Respond to a specific order's negotiation -----------------------------
section_label("Respond on a customer's behalf")
st.markdown(
    """
    <div class="oo-card">
    Enter an order ID to see its negotiations and simulate the customer's
    reply - this is what the <code>/customer-response</code> webhook would
    normally receive from an inbound email reply, or what clicking
    Accept/Reject in the negotiation email itself does.
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

order_id = st.text_input("Order ID")

if order_id:
    try:
        order_negotiations = api.get_negotiations(order_id)
    except api.ApiError as e:
        st.error(str(e))
        order_negotiations = []

    if not order_negotiations:
        st.caption("No negotiations found for this order.")

    for n in order_negotiations:
        st.markdown('<div class="oo-card">', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**{n['discount_pct']}% off** - via {n['channel']}")
            st.caption(f"Negotiation ID: {n['id']}")
        with c2:
            st.markdown(status_badge(n["customer_response"]), unsafe_allow_html=True)

        if n["customer_response"] == "pending":
            b1, b2 = st.columns(2)
            if b1.button("Accept", key=f"accept_{n['id']}"):
                try:
                    api.respond_to_negotiation(order_id, n["id"], "accepted")
                    st.rerun()
                except api.ApiError as e:
                    st.error(str(e))
            if b2.button("Reject", key=f"reject_{n['id']}"):
                try:
                    api.respond_to_negotiation(order_id, n["id"], "rejected")
                    st.rerun()
                except api.ApiError as e:
                    st.error(str(e))
        st.markdown("</div>", unsafe_allow_html=True)
