import streamlit as st
from lib import api
from lib.theme import inject_base_css, render_sidebar_brand, section_label, status_badge, pipeline_diagram, STATUS_TO_NODE

st.set_page_config(page_title="OrderOps AI - Orders", layout="wide")
inject_base_css()
render_sidebar_brand()

st.title("Orders")
st.caption("Look up an existing order, or create a test order to run through the pipeline")

tab_lookup, tab_create = st.tabs(["Look up order", "Create test order"])

with tab_lookup:
    order_id = st.text_input("Order ID", key="lookup_order_id")
    if st.button("Look up", type="primary") and order_id:
        try:
            order = api.get_order(order_id)
        except api.ApiError as e:
            st.error(str(e))
        else:
            st.markdown('<div class="oo-card">', unsafe_allow_html=True)
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"**Status:** {status_badge(order['status'])}", unsafe_allow_html=True)
            with c2:
                st.caption(f"Customer: {order['customer_id']}")
                st.caption(f"Updated: {order['updated_at']}")
            st.markdown("</div>", unsafe_allow_html=True)

            st.write("")
            section_label("Pipeline position")
            active_node = STATUS_TO_NODE.get(order["status"])
            st.graphviz_chart(pipeline_diagram(active_node), use_container_width=True)

            st.write("")
            section_label("Negotiations")
            try:
                negotiations = api.get_negotiations(order_id)
            except api.ApiError as e:
                st.warning(str(e))
                negotiations = []

            if not negotiations:
                st.caption("No negotiations on this order yet.")
            for n in negotiations:
                st.markdown('<div class="oo-card">', unsafe_allow_html=True)
                cols = st.columns([3, 1])
                with cols[0]:
                    st.write(f"{n['discount_pct']}% off - via {n['channel']}")
                with cols[1]:
                    st.markdown(status_badge(n["customer_response"]), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

with tab_create:
    st.caption(
        "Creates an order and immediately runs it through the LangGraph pipeline "
        "(fraud check, then inventory validation, then negotiation if needed). "
        "Customers and products are pulled live from MySQL."
    )

    try:
        customers = api.get_customers()
        products = api.get_products()
    except api.ApiError as e:
        st.error(str(e))
        customers, products = [], []

    if not customers or not products:
        st.warning("No customers/products found. Run `python seed_data.py` first.")
    else:
        customer_labels = {f"{c['name']} ({c['email']})": c["id"] for c in customers}
        product_labels = {
            f"{p['name']} - {p['sku']} - stock: {p['stock_qty']}": p["id"] for p in products
        }

        selected_customer_label = st.selectbox("Customer", list(customer_labels.keys()))
        selected_product_label = st.selectbox("Product", list(product_labels.keys()))
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

        if st.button("Create order"):
            customer_id = customer_labels[selected_customer_label]
            product_id = product_labels[selected_product_label]
            try:
                order = api.create_order(customer_id, [{"product_id": product_id, "quantity": int(quantity)}])
            except api.ApiError as e:
                st.error(str(e))
            else:
                st.success(f"Order created: {order['id']}")
                st.markdown(status_badge(order["status"]), unsafe_allow_html=True)
                if order["status"] == "awaiting_response":
                    st.info(
                        "The selected product was out of stock - a negotiation email "
                        "was sent to the customer with Accept/Reject links."
                    )
