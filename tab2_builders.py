"""
Tab 2 - Builders and Locations
Loaded by app.py, which calls render() inside the second tab.
Question: Is AI data centre capacity concentrated in a few organisations or countries?
Owner: Erkebai (Eric) Bakhavadinov
Data: Epoch AI, 'AI data centers' (data/raw/data_centers.csv). Transformations: src/tab2_prep.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import tab2_prep as prep  # noqa: E402


# Colours: one hue for the highlighted groups, recessive gray for the rest.
HIGHLIGHT = "#2a78d6"
REST = "#c9c7c1"
UNDISCLOSED = "#e4e2dd"
MUTED_INK = "#6b6a66"
TOP_BARS = 12  # bars drawn before folding the tail into "All other"


@st.cache_data
def get_data() -> pd.DataFrame:
    return prep.clean(prep.load())


def render() -> None:
    """Draw Tab 2. Called by app.py inside st.tabs."""
    df = get_data()
    operational = df[df["operational"]]

    # ---------- Header ----------
    st.caption("Tab 2 of 4 · Supply side")
    st.header("Builders and Locations")
    st.markdown(
        "**Is AI data centre capacity concentrated in a few organisations or countries?**  \n"
        "For **Dana**, concentration matters: "
        "if a handful of companies hold most of the power, each grid connection request is a bet "
        "on one company's plans, and a single cancellation can strand new capacity."
    )

    # ---------- Controls (one row, above the chart) ----------
    c1, c2 = st.columns([1, 2])
    with c1:
        view = st.radio("Group by", ["Owner", "Country"], horizontal=True, key="tab2_view")
    with c2:
        default_n = 5 if view == "Owner" else 1
        top_n = st.slider(
            f"Highlight the top N {'owners' if view == 'Owner' else 'countries'}",
            min_value=1, max_value=10, value=default_n, key=f"tab2_n_{view}",
        )

    table = prep.share_table(df, by=view)
    headline = prep.top_n_share(table, top_n, by=view)
    total_mw = df[prep.COL_POWER].sum()

    # ---------- Headline metrics ----------
    m1, m2, m3 = st.columns(3)
    label = "owner" if view == "Owner" else "country"
    m1.metric(
        f"Share of operational power held by the top {top_n} {label}{'s' if top_n > 1 else ''}",
        f"{headline:.0f}%",
    )
    m2.metric("Operational AI data centre power tracked", f"{total_mw:,.0f} MW")
    m3.metric(
        "Sites announced but not yet drawing power",
        f"{(~df['operational']).sum()} of {len(df)}",
    )

    # ---------- Main chart: ranked horizontal bars ----------
    shown = table.head(TOP_BARS).copy()
    tail = table.iloc[TOP_BARS:]
    if len(tail):
        shown = pd.concat([shown, pd.DataFrame([{
            view: f"All other ({len(tail)})",
            "power_mw": tail["power_mw"].sum(),
            "sites": tail["sites"].sum(),
            "share_pct": tail["share_pct"].sum(),
        }])], ignore_index=True)

    named_rank = (
        shown[view].ne(prep.UNATTRIBUTED) & ~shown[view].str.startswith("All other")
    ).cumsum()
    is_top = shown[view].ne(prep.UNATTRIBUTED) & (named_rank <= top_n)
    is_undisclosed = shown[view].eq(prep.UNATTRIBUTED)

    colors = [UNDISCLOSED if u else (HIGHLIGHT if t else REST) for t, u in zip(is_top, is_undisclosed)]
    patterns = ["/" if u else "" for u in is_undisclosed]

    fig = go.Figure(go.Bar(
        x=shown["share_pct"],
        y=shown[view],
        orientation="h",
        marker=dict(color=colors, pattern=dict(shape=patterns, fgcolor="#9a9893", size=6),
                    cornerradius=4, line=dict(width=0)),
        text=[f"{s:.1f}%" for s in shown["share_pct"]],
        textposition="outside",
        textfont=dict(color=MUTED_INK, size=12),
        cliponaxis=False,
        customdata=shown[["power_mw", "sites"]],
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% of operational power"
                      "<br>%{customdata[0]:,.0f} MW across %{customdata[1]} sites<extra></extra>",
    ))
    fig.update_layout(
        height=34 * len(shown) + 90,
        margin=dict(l=10, r=60, t=40, b=30),
        bargap=0.3,
        title=dict(text=f"Share of current AI data centre IT power (MW), by {label}",
                   font=dict(size=15), x=0, xanchor="left"),
        xaxis=dict(title=None, ticksuffix="%", showgrid=True, gridcolor="rgba(137,135,129,0.2)",
                   zeroline=False, range=[0, shown["share_pct"].max() * 1.15]),
        yaxis=dict(title=None, autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"Blue = top {top_n} named {label}{'s' if top_n > 1 else ''}. "
        + ("Hatched = sites where Epoch could not identify the hardware owner; they are not one "
           "company, so they never count toward the top N. " if view == "Owner" else "")
        + "Owner means the owner of the AI chips, which can differ from the building's owner. "
        "Sites at 0 MW are announced or under construction and add nothing to these shares yet."
    )

    # ---------- Reading for Dana ----------
    pipeline = df[~df["operational"]]
    leaders = table[table[view] != prep.UNATTRIBUTED].head(top_n)[view].tolist()
    in_leaders = pipeline[view].isin(leaders).sum()
    next_owner = pipeline[prep.COL_OWNER].value_counts()
    pipeline_line = (
        f"- **The pipeline is where the challenge is.** Of the {len(pipeline)} sites not yet drawing power, "
        f"{in_leaders} belong to today's top {top_n} {label}{'s' if top_n > 1 else ''}. "
        + (f"The largest pipeline owner is **{next_owner.index[0]}** ({next_owner.iloc[0]} sites). "
           if view == "Owner" and len(next_owner) else "")
        + "If those sites come online, the ranking can shift, but each one is still a single large request."
    )
    st.subheader("What this means for Dana")
    us_share = table.loc[table[view] == "United States", "share_pct"] if view == "Country" else None
    st.markdown(
        f"- **Concentrated by builder.** The top {top_n} {label}{'s' if top_n > 1 else ''} hold "
        f"**{headline:.0f}%** of the operational power Epoch tracks."
        + (f" The United States alone holds **{us_share.iloc[0]:.0f}%**." if us_share is not None and len(us_share) else "")
        + "\n" + pipeline_line + "\n"
        "- **Limit.** Epoch tracks major frontier AI sites, not every data centre, so this shows "
        "concentration at the frontier, not in the whole industry. Tab 1 covers total construction."
    )

    # ---------- Pipeline table ----------
    with st.expander(f"Sites announced but not yet drawing power ({(~df['operational']).sum()})"):
        pipe = df.loc[~df["operational"], [prep.COL_NAME, prep.COL_OWNER, prep.COL_COUNTRY]]
        st.dataframe(pipe.sort_values(prep.COL_OWNER), hide_index=True, width="stretch")

    # ---------- Accessible table view ----------
    with st.expander("Data table for this chart"):
        st.dataframe(
            table.rename(columns={"power_mw": "Power (MW)", "sites": "Sites",
                                  "share_pct": "Share (%)", "cumulative_pct": "Cumulative (%)"})
            .round(1),
            hide_index=True, width="stretch",
        )

    # ---------- Source and method (traceability) ----------
    with st.expander("Source and method"):
        st.markdown(
            f"""
    **File:** `data/raw/data_centers.csv`, downloaded unedited from
    [epoch.ai/data/data_centers/data_centers.csv]({prep.RAW_URL}) (Epoch AI, *AI data centers*, CC BY).
    {len(df)} rows, one per site.

    **Columns used:** `Name`, `Owner`, `Country`, `Current power (MW)` (latest IT power, which excludes cooling).

    **Steps** (all in `src/tab2_prep.py`):
    1. Read the CSV and keep the five columns above.
    2. Strip Epoch's confidence tags from `Owner` (`Meta #confident` → `Meta`); blank owners become *Owner not disclosed*.
    3. Group by {view}, sum `Current power (MW)`, divide each group by the total × 100.
    4. Headline = sum of the top {top_n} named groups' MW ÷ total MW × 100.

    **Owner confidence in the file:** {", ".join(f"{k}: {v}" for k, v in df["owner_confidence"].value_counts().items())}.
    """
        )
        st.markdown("**Trace the headline:** the rows behind it, straight from the file.")
        named = table[table[view] != prep.UNATTRIBUTED].head(top_n)[view].tolist()
        rows = df[df[view].isin(named) & df["operational"]]
        st.dataframe(
            rows[[prep.COL_NAME, prep.COL_OWNER, prep.COL_COUNTRY, prep.COL_POWER]]
            .sort_values(prep.COL_POWER, ascending=False),
            hide_index=True, width="stretch",
        )
        st.code(
            f"{rows[prep.COL_POWER].sum():,.1f} MW ÷ {total_mw:,.1f} MW × 100 = {headline:.1f}%",
            language=None,
        )
