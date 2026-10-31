"""
UPI & Digital Payments Analytics Dashboard
Run with:  streamlit run app.py
Needs the folder  clean_data/  (5 CSV files from the notebook) next to this file.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(page_title="UPI & Digital Payments Dashboard", layout="wide")
DATA_DIR = Path(__file__).parent / "clean_data"

# ------------------------------------------------------------------ look & feel
INK, TEAL, SAFFRON, SLATE, BRICK = "#1F2933", "#0B6E6E", "#E08A1E", "#5B6B7A", "#B5473A"
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', system-ui, sans-serif; color: #1F2933; }
.stApp { background: #FAF8F4; }
[data-testid="stSidebar"] { background: #F1EDE4; border-right: 1px solid #E2DCCF; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 4.5rem; max-width: 1150px; }
[data-testid="stVerticalBlockBorderWrapper"] { background:#FFFFFF; border:1px solid #E8E2D6 !important; border-radius:12px; padding:6px 8px; }
.note { background:#FFF6E8; border-left:3px solid #E08A1E; border-radius:6px; padding:12px 14px; font-size:.92rem; line-height:1.45; height:100%; }
.note b { color:#0B6E6E; }
.kicker { font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; color: #E08A1E; font-weight: 600; margin-bottom: .2rem; }
.headline { font-family: 'Fraunces', Georgia, serif; font-size: 2.1rem; line-height: 1.2; font-weight: 600; margin: 0 0 .4rem 0; color: #1F2933; }
.sub { color: #5B6B7A; font-size: .98rem; margin-bottom: 1.4rem; }
.kpi { border-top: 3px solid #0B6E6E; background: #FFFFFF; border: 1px solid #E8E2D6; border-radius: 10px; padding: 16px 18px; }
.kpi .l { font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; color: #5B6B7A; }
.kpi .v { font-family: 'Fraunces', Georgia, serif; font-size: 1.9rem; font-weight: 600; margin: 2px 0; }
.kpi .d { font-size: .82rem; color: #0B6E6E; }
.brand { font-family: 'Fraunces', Georgia, serif; font-size: 1.35rem; font-weight: 600; line-height: 1.2; }
</style>
""", unsafe_allow_html=True)

pio.templates["upi"] = go.layout.Template(layout=dict(
    colorway=[TEAL, SAFFRON, SLATE, BRICK, "#7A9E7E", "#8C6BB1"],
    font=dict(family="Inter, system-ui, sans-serif", color=INK, size=13),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False, linecolor="#CBD2D9", ticks="outside"),
    yaxis=dict(gridcolor="#E8E2D6", zeroline=False),
    legend=dict(orientation="h", y=1.12, x=0, title_text=""),
    margin=dict(l=10, r=10, t=30, b=10), hoverlabel=dict(bgcolor="white")))
pio.templates.default = "upi"
CFG = {"displayModeBar": False}


def show(fig):
    with st.container(border=True):
        st.plotly_chart(fig, width="stretch", config=CFG)


def note(text, col=None):
    (col or st).markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def header(title, sub="", kicker=None):
    st.markdown(f'<div class="kicker">{kicker or page}</div><div class="headline">{title}</div>'
                f'<div class="sub">{sub}</div>', unsafe_allow_html=True)


def kpi(col, label, value, note):
    col.markdown(f'<div class="kpi"><div class="l">{label}</div><div class="v">{value}</div>'
                 f'<div class="d">{note}</div></div>', unsafe_allow_html=True)



# ------------------------------------------------------------------ data
@st.cache_data
def load_data():
    master = pd.read_csv(DATA_DIR / "upi_master_clean.csv", parse_dates=["month"])
    nfs = pd.read_csv(DATA_DIR / "nfs_aeps_bank_clean.csv", parse_dates=["month"])
    acq = pd.read_csv(DATA_DIR / "fastag_acquirer_clean.csv", parse_dates=["month"])
    iss = pd.read_csv(DATA_DIR / "fastag_issuer_clean.csv", parse_dates=["month"])
    return master, nfs, acq, iss


def weighted_avg(df, by, cols, w="volume"):
    """Average of percentage columns, weighted by volume (big banks count more)."""
    tmp = df.copy()
    for c in cols:
        tmp[c] = tmp[c] * tmp[w]
    g = tmp.groupby(by, as_index=False)[[w] + cols].sum()
    for c in cols:
        g[c] = g[c] / g[w]
    return g


def fill_gaps(df, index_col, value_cols, group_col=None):
    """Insert empty rows for missing months so line charts show a GAP instead of a straight line."""
    full = pd.date_range(df[index_col].min(), df[index_col].max(), freq="MS")
    if group_col is None:
        return df.set_index(index_col).reindex(full).rename_axis(index_col).reset_index()
    parts = []
    for key, g in df.groupby(group_col):
        g = g.set_index(index_col)[value_cols].reindex(full).rename_axis(index_col).reset_index()
        g[group_col] = key
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


try:
    master, nfs, acq, iss = load_data()
except FileNotFoundError:
    st.error("clean_data folder not found. Keep the 5 CSV files in a folder called 'clean_data' next to app.py.")
    st.stop()

# ------------------------------------------------------------------ sidebar
st.sidebar.markdown('<div class="brand">UPI &amp;<br>Digital Payments</div>', unsafe_allow_html=True)
st.sidebar.write("")
page = st.sidebar.radio(
    "Pages",
    ["Overview", "UPI Trends", "Growth & Seasonality", "P2P vs P2M", "Banks Live",
     "NFS / AEPS Banks", "FASTag", "Limitations"],
)
st.sidebar.caption("Data: NPCI-based public statistics. Bank-wise pages show NFS, AEPS and FASTag, not UPI.")

# =================================================================== Overview
if page == "Overview":
    latest, prev_year = master.iloc[-1], master.iloc[-13]
    header(f"UPI now carries {latest.upi_volume_mn / 1000:.1f} billion payments a month",
           f"Up {latest.yoy_vol_pct:.0f}% on a year ago. Figures for {latest.month:%B %Y}, from cleaned NPCI-based data.")
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "Monthly volume", f"{latest.upi_volume_mn / 1000:.1f} bn", f"{latest.yoy_vol_pct:+.1f}% vs last year")
    kpi(c2, "Monthly value", f"Rs {latest.upi_value_cr / 1e5:.1f} L cr", f"{latest.yoy_val_pct:+.1f}% vs last year")
    kpi(c3, "Average payment", f"Rs {latest.avg_ticket_inr:,.0f}", f"{latest.avg_ticket_inr - prev_year.avg_ticket_inr:+,.0f} vs last year")
    kpi(c4, "Months covered", f"{len(master)}", f"{master.month.min():%b %Y} to {master.month.max():%b %Y}")
    st.write("")

    d = master[master.month >= "2016-12-01"]
    fig = px.area(d, x="month", y="upi_volume_mn", labels={"month": "", "upi_volume_mn": "Transactions (million)"},
                  title="UPI monthly transaction volume")
    fig.update_traces(line_color=TEAL, fillcolor="rgba(11,110,110,0.15)")
    fig.add_annotation(x=pd.Timestamp("2020-04-01"), y=float(master.loc[master.month == "2020-04-01", "upi_volume_mn"].iloc[0]),
                       text="COVID lockdown", showarrow=True, arrowcolor=SLATE, ax=-10, ay=-60)
    show(fig)

    g0 = master[master.month >= "2019-04-01"].iloc[0]
    pm = master.dropna(subset=["p2m_share_pct"])
    t0 = master[master.month >= "2018-04-01"].iloc[0]
    n1, n2, n3 = st.columns(3)
    note(f"<b>Growth is cooling, not stopping.</b> Year-on-year volume growth was {g0.yoy_vol_pct:.0f}% in {g0.month:%b %Y} "
         f"and is {latest.yoy_vol_pct:.0f}% now, on a much bigger base.", n1)
    note(f"<b>More shopping, less transfers.</b> Merchant (P2M) payments grew from {pm.p2m_share_pct.iloc[0]:.0f}% of volume in "
         f"{pm.month.iloc[0]:%b %Y} to {pm.p2m_share_pct.iloc[-1]:.0f}% in {pm.month.iloc[-1]:%b %Y}.", n2)
    note(f"<b>Payments are getting smaller.</b> The average payment moved from Rs {t0.avg_ticket_inr:,.0f} in {t0.month:%b %Y} "
         f"to Rs {latest.avg_ticket_inr:,.0f} now.", n3)


# =================================================================== Trends
elif page == "UPI Trends":
    header("UPI volume and value over time")
    d_all = master[master.month >= "2016-12-01"]
    lo, hi = d_all.month.min().date(), d_all.month.max().date()
    rng = st.slider("Date range", min_value=lo, max_value=hi, value=(lo, hi), format="MMM YYYY")
    d = d_all[(d_all.month.dt.date >= rng[0]) & (d_all.month.dt.date <= rng[1])]

    c1, c2, c3 = st.columns(3)
    metric = c1.radio("Metric", ["Volume (million)", "Value (Rs crore)"], horizontal=True)
    roll = c2.checkbox("Show 12-month rolling average", value=True)
    log = c3.checkbox("Log scale", value=False)

    col = "upi_volume_mn" if metric.startswith("Volume") else "upi_value_cr"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.month, y=d[col], mode="lines", name="Monthly", line=dict(width=2.5)))
    if roll and col == "upi_volume_mn":
        fig.add_trace(go.Scatter(x=d.month, y=d.vol_roll12, mode="lines", name="12-month average",
                                 line=dict(dash="dot")))
    elif roll:
        fig.add_trace(go.Scatter(x=d.month, y=d[col].rolling(12).mean(), mode="lines", name="12-month average",
                                 line=dict(dash="dot")))
    if pd.Timestamp("2020-04-01") >= d.month.min() and pd.Timestamp("2020-04-01") <= d.month.max():
        fig.add_vline(x=pd.Timestamp("2020-04-01").timestamp() * 1000, line_dash="dash", line_color=SLATE,
                      annotation_text="COVID lockdown")
    fig.update_layout(yaxis_title=metric, xaxis_title="", hovermode="x unified",
                      yaxis_type="log" if log else "linear")
    show(fig)

    st.subheader("Average payment size")
    d2 = d[d.month >= "2017-04-01"]
    fig2 = px.line(d2, x="month", y="avg_ticket_inr", labels={"month": "", "avg_ticket_inr": "Rs per transaction"})
    show(fig2)
    st.caption("Average payment = value / volume. A falling line means smaller everyday payments.")

# =================================================================== Growth
elif page == "Growth & Seasonality":
    header("Growth and seasonality")
    d = master[~master.is_ramp_up].copy()

    tab1, tab2, tab3 = st.tabs(["Growth rate", "Seasonality heatmap", "Outliers"])

    with tab1:
        kind = st.radio("Growth type", ["Year-on-year (YoY)", "Month-on-month (MoM)"], horizontal=True)
        what = st.radio("For", ["Volume", "Value"], horizontal=True)
        col = {("Year-on-year (YoY)", "Volume"): "yoy_vol_pct", ("Year-on-year (YoY)", "Value"): "yoy_val_pct",
               ("Month-on-month (MoM)", "Volume"): "mom_vol_pct", ("Month-on-month (MoM)", "Value"): "mom_val_pct"}[(kind, what)]
        start = "2019-04-01" if kind.startswith("Year") else "2017-04-01"
        dd = d[d.month >= start]
        if kind.startswith("Year"):
            fig = px.area(dd, x="month", y=col, labels={"month": "", col: "Growth (%)"})
            fig.update_traces(line_color=TEAL, fillcolor="rgba(11,110,110,0.15)")
        else:
            fig = px.bar(dd, x="month", y=col, color=dd[col] >= 0, color_discrete_map={True: TEAL, False: BRICK},
                         labels={"month": "", col: "Growth (%)"})
            fig.update_layout(showlegend=False)
        fig.add_annotation(x=dd.month.iloc[-1], y=dd[col].iloc[-1], text=f"Latest: {dd[col].iloc[-1]:.1f}%",
                           showarrow=True, arrowcolor=SLATE, ax=-50, ay=-45)
        show(fig)
        pk = dd.loc[dd[col].idxmax()]
        note(f"<b>Highest in this view:</b> {pk[col]:.0f}% in {pk.month:%b %Y}. <b>Latest:</b> {dd[col].iloc[-1]:.1f}%.")
        st.caption("YoY compares the same month a year apart, so seasonality cancels out. "
                   "The launch months (2016) are left out because tiny numbers give huge percentages.")

    with tab2:
        from_year = st.slider("Start year", 2019, int(master.year.max()) - 1, 2019)
        h = master[master.year >= from_year].pivot(index="year", columns="month_num", values="mom_vol_pct")
        h.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][: len(h.columns)]
        fig = px.imshow(h, text_auto=".1f", color_continuous_scale=[BRICK, "#F5F1E8", TEAL], color_continuous_midpoint=0,
                        aspect="auto", labels=dict(color="MoM %"))
        show(fig)
        st.caption("Look down a column: a month that is dark green (or red) in most years suggests a seasonal pattern.")

    with tab3:
        dd = d[d.mom_vol_pct.notna()]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dd.month, y=dd.mom_vol_pct, mode="lines", name="MoM growth", line=dict(color="grey")))
        o = dd[dd.is_outlier_growth]
        fig.add_trace(go.Scatter(x=o.month, y=o.mom_vol_pct, mode="markers", name="Flagged outlier",
                                 marker=dict(color="red", size=9)))
        fig.update_layout(yaxis_title="MoM volume growth (%)")
        show(fig)
        st.write("Flagged months (IQR rule):",
                 ", ".join(o.month.dt.strftime("%b %Y")) if len(o) else "none")
        st.caption("Outliers are flagged, not deleted. Apr 2020 is the COVID lockdown; early months grew fast from a small base.")

# =================================================================== P2P vs P2M
elif page == "P2P vs P2M":
    header("Person-to-person (P2P) vs person-to-merchant (P2M)")
    d = master[master.p2p_vol.notna()]
    st.caption(f"P2P/P2M data is available only for {d.month.min():%b %Y} to {d.month.max():%b %Y}.")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.month, y=d.p2p_vol, name="P2P", stackgroup="one"))
    fig.add_trace(go.Scatter(x=d.month, y=d.p2m_vol, name="P2M", stackgroup="one"))
    fig.update_layout(yaxis_title="Transactions (million)", hovermode="x unified")
    show(fig)

    fig2 = px.line(d, x="month", y="p2m_share_pct", labels={"month": "", "p2m_share_pct": "P2M share of volume (%)"})
    show(fig2)
    first, last = d.iloc[0], d.iloc[-1]
    st.info(f"P2M share moved from {first.p2m_share_pct:.1f}% ({first.month:%b %Y}) to "
            f"{last.p2m_share_pct:.1f}% ({last.month:%b %Y}).")

# =================================================================== Banks live
elif page == "Banks Live":
    header("Banks live on UPI vs transaction volume")
    d = master[master.banks_live.notna()]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=d.month, y=d.upi_volume_mn, name="Volume (million)"), secondary_y=False)
    fig.add_trace(go.Scatter(x=d.month, y=d.banks_live, name="Banks live"), secondary_y=True)
    fig.update_yaxes(title_text="Volume (million)", secondary_y=False)
    fig.update_yaxes(title_text="Banks live", secondary_y=True)
    fig.update_layout(hovermode="x unified")
    show(fig)
    corr = d[["upi_volume_mn", "banks_live"]].corr().iloc[0, 1]
    st.write(f"Correlation between volume and banks live: **{corr:.2f}**")
    st.warning("Banks-live data is missing from Sep 2023 to Mar 2026 (not in the provided files). "
               "Both lines rise over time, so the high correlation shows association, not cause.")

# =================================================================== NFS / AEPS
elif page == "NFS / AEPS Banks":
    header("NFS and AEPS: approval and decline rates by bank")
    st.warning("This page is NFS (ATM network) and AEPS (Aadhaar payments), NOT UPI.")

    c1, c2, c3 = st.columns(3)
    product = c1.selectbox("Product", ["NFS", "AEPS"])
    metric_name = c2.selectbox("Rate", ["Technical decline %", "Business decline %", "Approved %"])
    hide_bad = c3.checkbox("Hide rows where the 3 percentages are incomplete", value=False)
    col = {"Technical decline %": "technical_decline_pct", "Business decline %": "business_decline_pct",
           "Approved %": "approved_pct"}[metric_name]

    d = nfs[nfs["product"] == product]
    if hide_bad:
        d = d[~d.pct_sum_issue]

    tab1, tab2 = st.tabs(["Trend by bank", "Top banks compared"])
    with tab1:
        by_vol = d.groupby("bank").volume.sum().sort_values(ascending=False)
        chosen = st.multiselect("Banks", by_vol.index.tolist(), default=by_vol.index[:5].tolist())
        sub = d[d.bank.isin(chosen)]
        if sub.empty:
            st.info("Choose at least one bank.")
        else:
            gap = fill_gaps(sub, "month", [col], group_col="bank")
            fig = px.line(gap, x="month", y=col, color="bank", markers=True,
                          labels={"month": "", col: metric_name})
            show(fig)
            st.caption("A break in a line means that month is missing from the source data (e.g. Jun 2023).")

    with tab2:
        n = st.slider("Number of banks (largest by volume)", 5, 20, 10)
        avg = weighted_avg(d, ["bank"], ["approved_pct", "business_decline_pct", "technical_decline_pct"])
        top = avg.nlargest(n, "volume").sort_values(col)
        fig = px.bar(top, x=col, y="bank", orientation="h", labels={col: metric_name, "bank": ""}, hover_data={"volume": ":,.0f"})
        show(fig)
        st.caption("Rates are averaged over all months, weighted by volume so a big bank counts more than a tiny one.")

    st.subheader("Product trend (all banks, volume-weighted)")
    monthly = weighted_avg(nfs, ["product", "month"], ["approved_pct", "business_decline_pct", "technical_decline_pct"])
    gap = fill_gaps(monthly, "month", ["business_decline_pct", "technical_decline_pct"], group_col="product")
    fig = px.line(gap, x="month", y=col if col != "approved_pct" else "business_decline_pct", color="product",
                  markers=True, labels={"month": ""})
    if col == "approved_pct":
        st.caption("(Approved % is shown per bank above; this chart shows business decline % for the product.)")
    show(fig)
    st.caption("AEPS Dec 2022: the three percentages cover only part of the transactions, so rates for that month are less reliable.")

# =================================================================== FASTag
elif page == "FASTag":
    header("FASTag: acquirer and issuer banks")
    st.warning("FASTag data covers only 10 months (Sep 2021 - Jun 2022). Treat it as a snapshot, not a long trend.")

    tab1, tab2 = st.tabs(["Acquirer banks (toll collectors)", "Issuer banks (tag providers)"])
    with tab1:
        a = acq.dropna(subset=["approved_pct"])
        avg = weighted_avg(a, ["bank"], ["approved_pct", "business_decline_pct", "technical_decline_pct"]).sort_values("approved_pct")
        fig = px.bar(avg, x="approved_pct", y="bank", orientation="h", labels={"approved_pct": "Average approval (%)", "bank": ""})
        fig.update_xaxes(range=[max(avg.approved_pct.min() - 3, 0), 100])
        show(fig)
        st.caption("The axis starts near 75%, not 0%, so small gaps look bigger than they are.")
    with tab2:
        n = st.slider("Top N banks by deemed-approved share", 5, 20, 10)
        avg = weighted_avg(iss, ["bank"], ["approved_pct", "deemed_approved_pct"]).nlargest(n, "deemed_approved_pct")
        fig = px.bar(avg.sort_values("deemed_approved_pct"), x="deemed_approved_pct", y="bank", orientation="h",
                     labels={"deemed_approved_pct": "Deemed-approved (%)", "bank": ""})
        show(fig)
        st.caption("Deemed approved = approved automatically when the issuer bank did not respond in time. "
                   "The data shows the share, not the reason.")

# =================================================================== Limitations
else:
    header("Limitations and notes")
    st.markdown(
        """
- Bank-wise decline data is for **NFS, AEPS and FASTag**, not UPI. It lists only the top banks for each month.
- NFS/AEPS covers Aug 2021 - Jul 2023. Jun 2023 is missing, and AEPS Dec 2022 has incomplete percentages.
- FASTag covers only 10 months (Sep 2021 - Jun 2022).
- P2P/P2M data covers only Apr 2020 - Aug 2023.
- Banks-live data is missing from Sep 2023 to Mar 2026.
- Aggregate data cannot identify fraud or prove why a transaction was declined.
- Some bank renames and mergers in the name mapping should be verified before relying on them.
- Missing values were not filled with made-up numbers. Outliers were flagged, not deleted.
        """
    )
    st.subheader("Cleaning steps in short")
    st.markdown(
        """
1. Fixed dates stored as YYYY-DD-MM and one wrongly labelled month.
2. Converted text numbers to numbers and checked them against the master table.
3. Standardised bank names and merged resulting duplicates with a volume-weighted average.
4. Created growth, average payment size, P2M share and rolling averages.
5. Flagged outliers with the IQR rule and kept them.
        """
    )