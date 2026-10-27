from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "tmdb_parts"
EXPECTED_FILES = [DATA_DIR / f"tmdb_part_{i}.csv" for i in range(1, 10)]

st.set_page_config(
    page_title="TMDB Data Explorer",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 TMDB Data Explorer")
st.caption("Local CSV preview — no Google Cloud connection required.")

available_files = [path for path in EXPECTED_FILES if path.exists()]
missing_files = [path.name for path in EXPECTED_FILES if not path.exists()]

if not available_files:
    st.error(
        f"No TMDB part files were found in:\n\n`{DATA_DIR}`\n\n"
        "Put the `tmdb_parts` folder beside `app.py`, or update `DATA_DIR` in this script."
    )
    st.stop()

if missing_files:
    st.warning("Some expected files are missing: " + ", ".join(missing_files))

st.sidebar.header("Data source")
st.sidebar.write(f"Found **{len(available_files)}** of 9 expected CSV files.")
file_options = [path.name for path in available_files]

# Default to the first part so the initial load stays relatively lightweight.
selected_names = st.sidebar.multiselect(
    "CSV files to load",
    options=file_options,
    default=[file_options[0]],
    help="Start with one part for a quick test. Select all nine to explore the combined dataset.",
)

@st.cache_data(show_spinner="Reading selected CSV file(s)...")
def load_csvs(paths: tuple[str, ...]) -> pd.DataFrame:
    frames = []
    for path_string in paths:
        frame = pd.read_csv(path_string, low_memory=False)
        frame["_source_file"] = Path(path_string).name
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)

if not selected_names:
    st.info("Select at least one CSV file in the sidebar to begin.")
    st.stop()

selected_paths = tuple(str(DATA_DIR / name) for name in selected_names)

try:
    df = load_csvs(selected_paths)
except Exception as exc:
    st.error(f"Could not read the selected CSV file(s): {exc}")
    st.stop()

if df.empty:
    st.warning("The selected file(s) contain no rows.")
    st.stop()

# Summary metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Rows loaded", f"{len(df):,}")
m2.metric("Columns", f"{len(df.columns):,}")
m3.metric("CSV files", len(selected_names))
m4.metric("Cells missing", f"{int(df.isna().sum().sum()):,}")

st.subheader("Data preview")
st.write("Showing a limited preview to keep the page responsive.")
st.dataframe(df.head(100), use_container_width=True, height=380)

with st.expander("Column information and missing values"):
    info_df = pd.DataFrame({
        "column": df.columns,
        "data_type": [str(dtype) for dtype in df.dtypes],
        "missing_values": [int(df[col].isna().sum()) for col in df.columns],
        "missing_percent": [
            round(float(df[col].isna().mean() * 100), 2) for col in df.columns
        ],
    }).sort_values("missing_percent", ascending=False)
    st.dataframe(info_df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Search and filter")

# Search across likely title/name columns, when present.
text_columns = [
    col for col in df.select_dtypes(include=["object", "string"]).columns
    if col != "_source_file"
]
preferred_search = next(
    (col for col in ["title", "original_title", "name"] if col in text_columns),
    text_columns[0] if text_columns else None,
)

filtered = df
left, right = st.columns(2)

with left:
    if preferred_search:
        search_text = st.text_input(
            f"Search in `{preferred_search}`",
            placeholder="Enter text...",
        )
        if search_text.strip():
            filtered = filtered[
                filtered[preferred_search]
                .astype("string")
                .str.contains(search_text.strip(), case=False, na=False, regex=False)
            ]
    else:
        st.caption("No text column is available for text search.")

with right:
    numeric_columns = list(df.select_dtypes(include="number").columns)
    if numeric_columns:
        numeric_filter = st.selectbox(
            "Optional numeric filter",
            options=["None"] + numeric_columns,
        )
        if numeric_filter != "None":
            valid_values = pd.to_numeric(df[numeric_filter], errors="coerce").dropna()
            if not valid_values.empty:
                min_value = float(valid_values.min())
                max_value = float(valid_values.max())
                if min_value < max_value:
                    lower, upper = st.slider(
                        f"Range for `{numeric_filter}`",
                        min_value=min_value,
                        max_value=max_value,
                        value=(min_value, max_value),
                    )
                    values = pd.to_numeric(filtered[numeric_filter], errors="coerce")
                    filtered = filtered[values.between(lower, upper) | values.isna()]
                else:
                    st.caption(f"`{numeric_filter}` has no range to filter.")
    else:
        st.caption("No numeric columns were detected.")

st.write(f"**Matching rows:** {len(filtered):,}")
st.dataframe(filtered.head(500), use_container_width=True, height=420)


st.divider()
st.subheader("Movie analytics")

# Offer charts based on columns that actually exist in the CSV.
chart_options = ["Rating distribution"]

if "release_date" in filtered.columns:
    chart_options.append("Movies released by year")
if "genres" in filtered.columns:
    chart_options.append("Movies by genre")
if {"budget", "revenue"}.issubset(filtered.columns):
    chart_options.append("Budget vs revenue")
if {"popularity", "vote_average"}.issubset(filtered.columns):
    chart_options.append("Popularity vs rating")

chart_type = st.selectbox("Choose an analysis", chart_options)

if chart_type == "Rating distribution":
    if "vote_average" not in filtered.columns:
        st.info("The vote_average column is unavailable.")
    else:
        ratings = pd.to_numeric(
            filtered["vote_average"], errors="coerce"
        ).dropna()
        ratings = ratings[ratings.between(0, 10)]

        if ratings.empty:
            st.info("No valid ratings found.")
        else:
            # Use readable, fixed one-point rating intervals.
            labels = [f"{i}–{i + 1}" for i in range(10)]
            bands = pd.cut(
                ratings,
                bins=list(range(11)),
                labels=labels,
                right=False,
            )
            counts = bands.value_counts(sort=False).reindex(
                labels, fill_value=0
            )

            chart_df = pd.DataFrame({
                "Rating range": labels,
                "Number of movies": counts.to_numpy(),
            })

            fig = px.bar(
                chart_df,
                x="Rating range",
                y="Number of movies",
                title="Movie Rating Distribution",
            )

            fig.update_layout(dragmode=False)
            fig.update_xaxes(fixedrange=True)
            fig.update_yaxes(fixedrange=True)

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "staticPlot": True,
                    "scrollZoom": False,
                    "displayModeBar": False,
                },
            )
            st.caption(
                "Each bar counts movies in a one-point average-rating range."
            )

elif chart_type == "Movies released by year":
    dates = pd.to_datetime(filtered["release_date"], errors="coerce")
    years = dates.dropna().dt.year
    years = years[(years >= 1880) & (years <= pd.Timestamp.today().year + 5)]

    if years.empty:
        st.info("No valid release dates found.")
    else:
        counts = years.value_counts().sort_index()
        chart_df = pd.DataFrame({
            "Release year": counts.index,
            "Number of movies": counts.values,
        })
        fig = px.bar(
            chart_df,
            x="Release year",
            y="Number of movies",
            title="Movies Released by Year",
        )

        fig.update_layout(dragmode=False)
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "staticPlot": True,
                "scrollZoom": False,
                "displayModeBar": False,
            },
        )

elif chart_type == "Movies by genre":
    genres = (
        filtered["genres"]
        .dropna()
        .astype(str)
        .str.split(",")
        .explode()
        .str.strip()
    )
    genres = genres[genres.ne("") & genres.str.lower().ne("nan")]

    if genres.empty:
        st.info("No genre values found.")
    else:
        counts = genres.value_counts().head(20).sort_values()
        chart_df = pd.DataFrame({
            "Genre": counts.index,
            "Number of movies": counts.values,
        })
        fig = px.bar(
            chart_df,
            x="Genre",
            y="Number of movies",
            title="Movies by Genre",
        )

        fig.update_layout(
            dragmode=False,
            xaxis_tickangle=-45,
        )
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "staticPlot": True,
                "scrollZoom": False,
                "displayModeBar": False,
            },
        )
        st.caption(
            "Movies may belong to multiple genres, so genre counts overlap."
        )

elif chart_type == "Budget vs revenue":
    financial = filtered[["budget", "revenue"]].copy()
    financial["budget"] = pd.to_numeric(
        financial["budget"], errors="coerce"
    )
    financial["revenue"] = pd.to_numeric(
        financial["revenue"], errors="coerce"
    )
    financial = financial.dropna()
    financial = financial[
        (financial["budget"] > 0) & (financial["revenue"] > 0)
    ]

    if financial.empty:
        st.info("No movies with positive budget and revenue found.")
    else:
        if len(financial) > 5000:
            financial = financial.sample(5000, random_state=42)

        st.scatter_chart(
            financial,
            x="budget",
            y="revenue",
            use_container_width=True,
        )
        st.caption(
            "Each point represents a movie. Revenue minus budget is not net profit."
        )

elif chart_type == "Popularity vs rating":
    comparison = filtered[["popularity", "vote_average"]].copy()
    comparison["popularity"] = pd.to_numeric(
        comparison["popularity"], errors="coerce"
    )
    comparison["vote_average"] = pd.to_numeric(
        comparison["vote_average"], errors="coerce"
    )
    comparison = comparison.dropna()
    comparison = comparison[
        (comparison["popularity"] >= 0)
        & comparison["vote_average"].between(0, 10)
    ]

    if comparison.empty:
        st.info("No valid popularity and rating values found.")
    else:
        if len(comparison) > 5000:
            comparison = comparison.sample(5000, random_state=42)

        st.scatter_chart(
            comparison,
            x="popularity",
            y="vote_average",
            use_container_width=True,
        )

st.download_button(
    "Download filtered rows as CSV",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="tmdb_filtered_preview.csv",
    mime="text/csv",
)
