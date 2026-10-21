"""Tab 3: Electricity Demand.

Question for Dana: what share of electricity demand do data centres take,
and how fast is that share rising in the United States compared with the
rest of the world?

Data: IEA "Energy and AI" (data centre electricity use) divided by Ember
total electricity demand, processed and published by Our World in Data.
The CSV in data/ is kept exactly as downloaded; every cleaning step is below.
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA_FILE = Path(__file__).parent / "data" / "data-centers-share-electricity-demand.csv"
SOURCE_URL = "https://ourworldindata.org/grapher/data-centers-share-electricity-demand"
SOURCE_TEXT = (
    "International Energy Agency (2025, 2026); Ember (2026), "
    "with major processing by Our World in Data"
)

FOCUS = "United States"
# Regions shown by default. North America is left out because it mostly
# repeats the United States line.
DEFAULT_REGIONS = [
    "United States",
    "World",
    "Europe (IEA)",
    "China",
    "World excl. United States and China",
]
HIGHLIGHT = "#C46A10"  # warm amber: the one line Dana should read (matches the app theme)
CONTEXT = "#A79E97"    # soft warm grey: comparison regions


@st.cache_data
def load_data(path: Path = DATA_FILE) -> tuple[pd.DataFrame, str]:
    """Read the raw OWID file and return (tidy table, name of the value column).

    OWID files come with either short or long column names depending on the
    download option, so columns are matched by lower-cased name rather than
    by one exact spelling.
    """
    raw = pd.read_csv(path)
    cols = {c.lower(): c for c in raw.columns}
    entity, year = cols["entity"], cols["year"]
    value_col = [c for c in raw.columns if c.lower() not in ("entity", "code", "year")][0]
    df = raw.rename(columns={entity: "region", year: "year", value_col: "share"})
    df = df[["region", "year", "share"]].dropna(subset=["share"])
    df["year"] = df["year"].astype(int)
    return df.sort_values(["region", "year"]).reset_index(drop=True), value_col


def segments(df: pd.DataFrame) -> pd.DataFrame:
    """Split each region's line into segments between consecutive measured years.

    A segment is marked as a gap when it jumps over years with no data
    (2020 to 2023), so the chart can draw it dashed instead of solid.
    """
    rows = []
    for region, g in df.groupby("region"):
        g = g.sort_values("year").reset_index(drop=True)
        for i in range(len(g) - 1):
            y0, y1 = g.loc[i, "year"], g.loc[i + 1, "year"]
            for j in (i, i + 1):
                rows.append({
                    "region": region, "year": g.loc[j, "year"], "share": g.loc[j, "share"],
                    "seg": f"{region}|{y0}", "gap": (y1 - y0) > 1,
                })
    return pd.DataFrame(rows)


def role(d: pd.DataFrame) -> pd.Series:
    return d["region"].eq(FOCUS).map({True: "focus", False: "context"})


def build_chart(df: pd.DataFrame) -> alt.LayerChart:
    df = df.assign(role=role)
    seg = segments(df).assign(role=role)
    years = sorted(df["year"].unique())
    regions = sorted(df["region"].unique(), key=lambda r: (r != FOCUS, r))

    x = alt.X(
        "year:Q", title=None,
        scale=alt.Scale(domain=[min(years) - 0.2, max(years) + 2.4]),
        axis=alt.Axis(values=list(range(min(years), max(years) + 1)), format="d",
                      labelFontSize=14, grid=False),
    )
    y = alt.Y(
        "share:Q", title="Share of electricity demand (%)",
        scale=alt.Scale(domain=[0, max(6.0, float(df["share"].max()) * 1.15)]),
        axis=alt.Axis(labelFontSize=14, titleFontSize=14, format="d", tickMinStep=1),
    )
    color = alt.Color("role:N", scale=alt.Scale(domain=["focus", "context"],
                                                range=[HIGHLIGHT, CONTEXT]), legend=None)
    width = alt.Size("role:N", scale=alt.Scale(domain=["focus", "context"], range=[4, 2]),
                     legend=None)

    # Hover anywhere on the chart: the nearest measured year is selected.
    hover = alt.selection_point(nearest=True, on="pointerover", fields=["year"], empty=False)

    base_seg = alt.Chart(seg).encode(x=x, y=y, color=color, size=width, detail="seg:N")
    measured = base_seg.transform_filter("!datum.gap").mark_line(strokeCap="round")
    # Soft neon halo under the US line only, so Dana's eye goes there first.
    halo = (base_seg.transform_filter("datum.role == 'focus' && !datum.gap")
            .mark_line(strokeCap="round", opacity=0.22)
            .encode(size=alt.value(14), color=alt.value(HIGHLIGHT)))
    missing = base_seg.transform_filter("datum.gap").mark_line(strokeDash=[5, 5], opacity=0.8)

    dots = alt.Chart(df).mark_point(filled=True, opacity=1).encode(
        x=x, y=y, color=color,
        size=alt.condition(hover, alt.value(220), alt.value(90)),
    )

    # Vertical guide line with every region's value for the hovered year.
    # One row per year, one column per region. Columns get simple names (r0, r1, ...)
    # because region names like "World excl." contain characters the chart library
    # misreads; the real names are kept as the tooltip titles.
    safe = {r: f"r{i}" for i, r in enumerate(regions)}
    wide = (df.pivot(index="year", columns="region", values="share")
            .rename(columns=safe).reset_index())
    guide = (
        alt.Chart(wide)
        .mark_rule(color=CONTEXT, strokeWidth=1.5)
        .encode(
            x=x,
            opacity=alt.condition(hover, alt.value(0.7), alt.value(0)),
            tooltip=[alt.Tooltip("year:Q", title="Year", format="d")]
            + [alt.Tooltip(f"{safe[r]}:Q", title=f"{r} (%)", format=".2f") for r in regions],
        )
        .add_params(hover)
    )

    last = df[df["year"] == df["year"].max()]
    end_labels = (
        alt.Chart(last).mark_text(align="left", dx=12, fontSize=13, fontWeight="bold")
        .encode(x=x, y=y, color=color, text="endlabel:N")
        .transform_calculate(endlabel="datum.region + ' ' + format(datum.share, '.1f') + '%'")
    )

    gap_note = alt.Chart(pd.DataFrame({"year": [2021.5], "txt": ["no data 2021–22"]})).mark_text(
        fontSize=12, fontStyle="italic", color=CONTEXT, dy=-8,
    ).encode(x="year:Q", y=alt.value(12), text="txt:N")

    return (
        alt.layer(halo, missing, measured, guide, dots, end_labels, gap_note)
        .properties(height=440)
        .configure_view(strokeWidth=0)
        .configure(background="transparent")
    )


NEON_CSS = """
<style>
[data-testid="stMetric"] { transition: box-shadow .25s ease, transform .25s ease, border-color .25s ease; }
[data-testid="stMetric"]:hover { transform: translateY(-3px); border-color: #5CF2FF !important;
  box-shadow: 0 0 0 1px #5CF2FF, 0 0 16px rgba(92,242,255,.5), 0 0 30px rgba(255,92,214,.2); }
[data-testid="stMetricValue"] { color: #C46A10; }
</style>
"""


def render() -> None:
    st.html(NEON_CSS)
    st.header("⚡ Electricity Demand")
    st.markdown(
        "**What share of electricity demand do data centres take, and how fast is that "
        "share rising in the United States compared with the rest of the world?**"
    )

    if not DATA_FILE.exists():
        st.error(f"Missing source file: `data/{DATA_FILE.name}`. Download it from {SOURCE_URL}.")
        return

    df, value_col = load_data()
    years = sorted(int(y) for y in df["year"].unique())
    first, latest = years[0], years[-1]

    def val(region: str, year: int) -> float:
        return float(df.loc[(df["region"] == region) & (df["year"] == year), "share"].iloc[0])

    # --- Year picker for the cards -----------------------------------------
    year = st.segmented_control(
        "Show the summary cards for", years[1:], default=latest, key="tab3_year",
    ) or latest
    prev = years[years.index(year) - 1]  # previous *measured* year (2023's is 2020)

    us_now, us_prev, us_first = val(FOCUS, year), val(FOCUS, prev), val(FOCUS, first)
    world_now = val("World", year)

    # --- Summary cards -------------------------------------------------------
    c1, c2, c3 = st.columns(3)
    c1.metric(f"US data centre share, {year}", f"{us_now:.1f}%",
              f"{us_now - us_prev:+.1f} points since {prev}", delta_color="off", border=True)
    c2.metric(f"Change since {first}", f"{us_now - us_first:+.1f} points",
              f"{us_now / us_first:.1f}× the {first} share", delta_color="off", border=True)
    c3.metric(f"US vs world, {year}", f"{us_now / world_now:.1f}× higher",
              f"World: {world_now:.1f}%", delta_color="off", border=True)

    # --- Main chart ----------------------------------------------------------
    with st.container(border=True):
        options = sorted(df["region"].unique(), key=lambda r: (r != FOCUS, r))
        chosen = st.multiselect(
            "Regions to compare (the United States is always highlighted)",
            options, default=[r for r in DEFAULT_REGIONS if r in options], key="tab3_regions",
        )
        if FOCUS not in chosen:
            chosen = [FOCUS] + chosen
        st.altair_chart(build_chart(df[df["region"].isin(chosen)]), width="stretch")
        st.caption(
            "Hover over the chart to see every region's value for that year. "
            "Dots are measured years. Dashed segments cross 2021 and 2022, where the source "
            "has no values, so the line does not invent numbers for those years."
        )

    us_latest, us_before = val(FOCUS, latest), val(FOCUS, years[-2])
    world_latest = val("World", latest)
    st.info(
        f"**What this means for Dana:** in {latest}, data centres used about "
        f"{us_latest:.1f}% of US electricity, {us_latest / world_latest:.1f} times the world "
        f"average, and that share rose by {us_latest - us_before:.1f} points in the last year "
        f"alone. This is a rising load concentrated in the US grid. It covers **all** data "
        f"centres, not only AI ones, so it is an upper bound on AI-driven demand.",
        icon="💡",
    )

    # --- Trace: the first card's number back to the raw file -----------------
    with st.expander(f"🔍 Trace the headline number ({us_now:.1f}%) to the source file"):
        # Read as text so the table shows every digit exactly as stored in the file.
        raw = pd.read_csv(DATA_FILE, dtype=str, keep_default_na=False)
        ent = [c for c in raw.columns if c.lower() == "entity"][0]
        yr = [c for c in raw.columns if c.lower() == "year"][0]
        row = raw[(raw[ent] == FOCUS) & (raw[yr] == str(year))]
        prev_row = raw[(raw[ent] == FOCUS) & (raw[yr] == str(prev))]
        raw_value, prev_value = row[value_col].iloc[0], prev_row[value_col].iloc[0]
        diff = float(raw_value) - float(prev_value)
        st.markdown(f"1. File: `data/{DATA_FILE.name}` (unchanged OWID download)")
        st.markdown(f"2. Filter rows where *{ent}* = `{FOCUS}` and *{yr}* = `{year}`:")
        st.dataframe(row, hide_index=True, width="stretch")
        st.markdown(
            f"3. Column *{value_col}* holds `{raw_value}`. The unit is already percent, "
            f"so no conversion is needed."
        )
        st.markdown(f"4. Round to one decimal place: `{raw_value}` → **{float(raw_value):.1f}%**, "
                    f"the figure on the first summary card.")
        st.markdown(
            f"5. The card's change figure uses the {prev} row: `{raw_value}` − `{prev_value}` = "
            f"`{diff:.4f}` → **{diff:+.1f} points**."
        )

        # The other two cards, from the same file.
        def cell(region: str, yr_: int) -> str:
            return raw[(raw[ent] == region) & (raw[yr] == str(yr_))][value_col].iloc[0]

        first_value, world_value = cell(FOCUS, first), cell("World", year)
        st.markdown(
            f"6. Second card uses the United States {first} row (`{first_value}`): "
            f"`{raw_value}` − `{first_value}` = **{float(raw_value) - float(first_value):+.1f} points**, "
            f"and `{raw_value}` ÷ `{first_value}` = **{float(raw_value) / float(first_value):.1f}×**."
        )
        st.markdown(
            f"7. Third card uses the World {year} row (`{world_value}`): "
            f"`{raw_value}` ÷ `{world_value}` = **{float(raw_value) / float(world_value):.1f}× higher**, "
            f"and the world value rounds to **{float(world_value):.1f}%**."
        )

    with st.expander("📋 All data used in this tab"):
        wide = df.pivot(index="region", columns="year", values="share").round(2)
        st.dataframe(wide, width="stretch")

    st.caption(
        f"Source: {SOURCE_TEXT}. [{SOURCE_URL}]({SOURCE_URL}). "
        "Share = data centre electricity use (IEA) ÷ total electricity demand (Ember). "
        "Includes general-purpose and AI data centres; the source does not separate AI."
    )


if __name__ == "__main__":
    # Lets you preview the tab on its own: streamlit run tab3_electricity.py
    st.set_page_config(page_title="Electricity Demand", page_icon="⚡", layout="wide")
    render()
