"""Shared styling helpers so every page looks consistent. No emojis anywhere."""

import streamlit as st
import graphviz

STATUS_COLORS = {
    "pending": "#94a3b8",
    "risk_flagged": "#fbbf24",
    "validating": "#60a5fa",
    "negotiating": "#a78bfa",
    "awaiting_response": "#a78bfa",
    "fulfilled": "#34d399",
    "refunded": "#f87171",
    "cancelled": "#f87171",
    "accepted": "#34d399",
    "rejected": "#f87171",
    "timeout": "#fbbf24",
}

PIPELINE_NODES = [
    ("check_fraud_risk", "Fraud check"),
    ("validate_inventory", "Inventory validation"),
    ("generate_alternative", "Generate alternative"),
    ("send_negotiation", "Send negotiation"),
    ("await_customer_response", "Await response"),
    ("finalize_order", "Finalize order"),
]

STATUS_TO_NODE = {
    "pending": "check_fraud_risk",
    "risk_flagged": "check_fraud_risk",
    "validating": "validate_inventory",
    "negotiating": "generate_alternative",
    "awaiting_response": "await_customer_response",
    "fulfilled": "finalize_order",
    "refunded": "finalize_order",
    "cancelled": "finalize_order",
}


def inject_base_css():
    st.markdown(
        """
        <style>
        .block-container { padding-top: 3.5rem; max-width: 1100px; }
        .oo-badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.8rem;
            border: 1px solid;
            letter-spacing: 0.02em;
        }
        .oo-card {
            background-color: #0a0f1c;
            border: 1px solid #1e293b;
            border-radius: 6px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
        }
        .oo-status-dot {
            height: 7px; width: 7px; border-radius: 50%;
            background-color: #3b82f6; display: inline-block; margin-right: 6px;
        }
        .oo-section-label {
            font-family: monospace;
            font-size: 0.78rem;
            letter-spacing: 0.06em;
            color: #64748b;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
        }
        [data-testid="stSidebarNav"] { padding-top: 0.5rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand():
    """Small brand block at the top of the sidebar - kept out of the main
    content area so it never collides with Streamlit's own top toolbar."""
    st.sidebar.markdown(
        """
        <div style="padding: 0 0 1rem 0; margin-bottom: 0.75rem;
                    border-bottom: 1px solid #1e293b;">
            <div style="font-family: monospace; font-size: 0.95rem; color: #e2e8f0;">
                <b>ORDEROPS.AI</b>
            </div>
            <div style="margin-top: 6px; font-family: monospace; font-size: 0.75rem; color: #34d399;">
                <span class="oo-status-dot" style="background-color:#34d399;"></span>agent active
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_label(text: str):
    st.markdown(f'<div class="oo-section-label">{text}</div>', unsafe_allow_html=True)


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#94a3b8")
    label = status.replace("_", " ").upper()
    return (
        f'<span class="oo-badge" style="color:{color};border-color:{color}55;'
        f'background-color:{color}1a;">{label}</span>'
    )


def pipeline_diagram(active_node: str | None = None) -> graphviz.Digraph:
    g = graphviz.Digraph()
    g.attr(bgcolor="#020617", rankdir="LR", nodesep="0.45", ranksep="0.75", pad="0.25", margin="0")
    g.attr(
        "node", shape="box", style="filled,rounded", fontname="monospace",
        fontsize="11", fontcolor="#e2e8f0", color="#334155", penwidth="1",
        margin="0.22,0.14",
    )
    g.attr("edge", color="#475569", arrowsize="0.6", penwidth="1.1")

    for node_id, label in PIPELINE_NODES:
        if node_id == active_node:
            g.node(node_id, label, fillcolor="#0e3a5f", color="#3b82f6", penwidth="2")
        else:
            g.node(node_id, label, fillcolor="#0a0f1c")

    for (a, _), (b, _) in zip(PIPELINE_NODES, PIPELINE_NODES[1:]):
        g.edge(a, b)

    return g
