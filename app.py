
import ast
import json
import pandas as pd
import streamlit as st
from google.cloud import bigquery
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components

from tmdb_dss import analyze_investment
from tmdb_dss.config import DSS_DATASET
from tmdb_dss.connection import get_bigquery_client
from tmdb_dss.data_loader import load_recommendation_movies
from tmdb_dss.recommendation.content_based import load_or_build_recommender
from tmdb_dss.recommendation.hybrid import calculate_hybrid_score


OBJECTIVES = [
    "BALANCED",
    "HIGH_ROI",
    "HIGH_PROFIT",
    "POPULARITY",
    "LOW_RISK",
]

st.set_page_config(
    page_title="TMDB Investment DSS",
    page_icon="🎬",
    layout="wide",
)

movie_selector = components.declare_component(
    "movie_selector",
    path="components",
)

# ============================================================
# DATA ACCESS
# ============================================================

def to_df(rows):
    if rows is None:
        return pd.DataFrame()

    if isinstance(rows, pd.DataFrame):
        return rows.copy()

    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner="Loading movie dataset...")
def load_movie_dataset():
    return load_recommendation_movies()


@st.cache_data(ttl=3600, show_spinner="Preparing movie dataset...")
def prepare_movie_dataset(df):
    df = df.copy()

    df["release_date"] = pd.to_datetime(
        df["release_date"],
        errors="coerce",
    )

    df["release_year"] = df["release_date"].dt.year

    def parse_genres(value):
        if isinstance(value, list):
            return [
                str(item.get("name", item))
                if isinstance(item, dict)
                else str(item)
                for item in value
            ]

        if pd.isna(value):
            return []

        try:
            parsed = ast.literal_eval(str(value))

            if isinstance(parsed, list):
                return [
                    str(item.get("name", item))
                    if isinstance(item, dict)
                    else str(item)
                    for item in parsed
                ]

        except (ValueError, SyntaxError):
            pass

        try:
            parsed = json.loads(str(value))

            if isinstance(parsed, list):
                return [
                    str(item.get("name", item))
                    if isinstance(item, dict)
                    else str(item)
                    for item in parsed
                ]

        except (ValueError, TypeError):
            pass

        return [
            item.strip()
            for item in str(value).split(",")
            if item.strip()
        ]

    df["genre_list"] = df["genres"].apply(parse_genres)

    return df


@st.cache_data(
    ttl=3600,
    show_spinner="Running investment analysis...",
)
def run_investment_analysis(
    budget,
    genres,
    objective,
    min_votes,
    top_n,
):
    return analyze_investment(
        budget=budget,
        genres=list(genres) or None,
        objective=objective,
        min_votes=min_votes,
        top_n=top_n,
    )


@st.cache_resource(show_spinner="Loading recommendation model...")
def get_content_recommender():
    return load_or_build_recommender()


def load_candidate_metrics(candidate_ids):
    client = get_bigquery_client()

    query = f"""
        SELECT
            dm.tmdb_id,
            bm.weighted_rating,
            bm.roi_tier
        FROM `{DSS_DATASET}.vw_movie_business_metrics` bm
        JOIN `{DSS_DATASET}.dim_movie` dm
            USING (movie_sk)
        WHERE dm.tmdb_id IN UNNEST(@movie_ids)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "movie_ids",
                "INT64",
                candidate_ids,
            )
        ]
    )

    return client.query(
        query,
        job_config=job_config,
    ).to_dataframe()


def get_movie_recommendations(
    movie_id,
    top_n=100,
    content_weight=0.50,
    rating_weight=0.30,
    business_weight=0.20,
):
    recommender = get_content_recommender()

    similar_movies = to_df(
        recommender.recommend(
            movie_id,
            top_n=top_n,
        )
    )

    if similar_movies.empty:
        return pd.DataFrame()

    similar_movies["id"] = (
        similar_movies["id"].astype("int64")
    )

    metrics = load_candidate_metrics(
        similar_movies["id"].tolist()
    )

    if metrics.empty:
        return pd.DataFrame()

    metrics["tmdb_id"] = (
        metrics["tmdb_id"].astype("int64")
    )

    recommendations = similar_movies.merge(
        metrics,
        left_on="id",
        right_on="tmdb_id",
        how="inner",
    )

    if recommendations.empty:
        return recommendations

    return calculate_hybrid_score(
        recommendations,
        content_weight=content_weight,
        rating_weight=rating_weight,
        business_weight=business_weight,
    )


# ============================================================
# PAGE NAVIGATION
# ============================================================

st.title("🎬 TMDB Decision Support System")

st.caption(
    "Explore the TMDB movie dataset, evaluate investment opportunities, "
    "and discover similar movies."
)

page = option_menu(
    menu_title=None,
    options=[
        "Dataset Overview",
        "Investment Analysis",
        "Movie Recommendations",
    ],
    icons=[
        "bar-chart-line",
        "film",
        "stars",
    ],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {
            "padding": "5px",
            "background-color": "#f0f2f6",
            "border-radius": "12px",
        },
        "icon": {
            "color": "#555555",
            "font-size": "18px",
        },
        "nav-link": {
            "font-size": "15px",
            "text-align": "center",
            "margin": "3px",
            "padding": "12px",
            "border-radius": "8px",
        },
        "nav-link-selected": {
            "background-color": "#2563eb",
            "color": "white",
            "font-weight": "600",
        },
    },
)


# ============================================================
# LOAD DATA
# ============================================================

try:
    raw_movies = load_movie_dataset()
    movies = prepare_movie_dataset(raw_movies)

except Exception as exc:
    st.error(f"Could not load the movie dataset: {exc}")
    st.stop()


# ============================================================
# PAGE 1: DATASET OVERVIEW
# ============================================================

if page == "Dataset Overview":

    st.header("Dataset Overview")

    st.write(
        "An overview of the TMDB movie dataset used by the "
        "Decision Support System."
    )

    total_movies = len(movies)

    total_genres = len({
        genre
        for genre_list in movies["genre_list"]
        for genre in genre_list
    })

    year_min = movies["release_year"].min()
    year_max = movies["release_year"].max()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total movies", f"{total_movies:,}")
    c2.metric("Unique genres", f"{total_genres:,}")
    c3.metric(
        "Earliest release year",
        f"{int(year_min)}" if pd.notna(year_min) else "-",
    )
    c4.metric(
        "Latest release year",
        f"{int(year_max)}" if pd.notna(year_max) else "-",
    )

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Genre Distribution")

        genre_counts = (
            movies["genre_list"]
            .explode()
            .dropna()
            .value_counts()
            .head(15)
        )

        if not genre_counts.empty:
            st.bar_chart(genre_counts)

    with right:
        st.subheader("Movie Releases by Year")

        year_counts = (
            movies["release_year"]
            .dropna()
            .value_counts()
            .sort_index()
        )

        if not year_counts.empty:
            st.line_chart(year_counts)

    st.divider()

    st.subheader("Dataset Quality")

    quality = pd.DataFrame({
        "Field": [
            "Movie ID",
            "Title",
            "Overview",
            "Genres",
            "Release date",
        ],
        "Missing values": [
            movies["id"].isna().sum(),
            movies["title"].isna().sum(),
            movies["overview"].isna().sum(),
            movies["genres"].isna().sum(),
            movies["release_date"].isna().sum(),
        ],
    })

    st.dataframe(
        quality,
        hide_index=True,
        use_container_width=True,
    )

    with st.expander("Preview dataset"):
        st.dataframe(
            movies[
                [
                    "id",
                    "title",
                    "release_date",
                    "genres",
                ]
            ].head(100),
            hide_index=True,
            use_container_width=True,
        )


# ============================================================
# PAGE 2: MOVIE EXPLORER & INVESTMENT ANALYSIS
# ============================================================

elif page == "Investment Analysis":
    # --------------------------------------------------------
    # INVESTMENT ANALYSIS
    # --------------------------------------------------------

    st.divider()

    st.header("Investment Analysis")

    st.write(
        "Evaluate movie investment candidates using budget, "
        "genre, audience reception, and business performance."
    )

    available_genres = sorted({
        genre
        for genre_list in movies["genre_list"]
        for genre in genre_list
    })

    with st.form("investment_form"):

        col1, col2 = st.columns(2)

        with col1:
            budget = st.number_input(
                "Maximum budget (USD)",
                min_value=1,
                value=50_000_000,
                step=1_000_000,
            )

            objective = st.selectbox(
                "Investment objective",
                OBJECTIVES,
            )

            min_votes = st.slider(
                "Minimum votes",
                min_value=0,
                max_value=5000,
                value=100,
                step=50,
            )

        with col2:
            investment_genres = st.multiselect(
                "Investment genres",
                available_genres,
                default=["Action"] if "Action" in available_genres else [],
            )

            investment_top_n = st.slider(
                "Number of investment results",
                min_value=5,
                max_value=50,
                value=10,
            )

        analyze = st.form_submit_button(
            "Analyze Investments",
            type="primary",
            use_container_width=True,
        )

    if analyze:
        st.session_state.pop("investment_result", None)

        try:
            st.session_state["investment_result"] = (
                run_investment_analysis(
                    budget,
                    tuple(investment_genres),
                    objective,
                    min_votes,
                    investment_top_n,
                )
            )

        except Exception as exc:
            st.error(f"Investment analysis failed: {exc}")

    result = st.session_state.get("investment_result")

    if result:

        investment = result.get("investment_analysis", {})
        market = result.get("market_analysis", {})
        metadata = result.get("metadata", {})

        ranking = to_df(investment.get("ranking"))

        if metadata.get("execution_time_seconds") is not None:
            st.metric(
                "Analysis execution time",
                f"{metadata['execution_time_seconds']:.3f} seconds",
            )

        with st.expander("Execution time breakdown"):
            timings = metadata.get("stage_timings", {})

            if timings:
                for stage, duration in timings.items():
                    st.write(
                        f"**{stage.replace('_', ' ').title()}:** "
                        f"{duration:.3f}s"
                    )
            else:
                st.info("No timing information available.")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Candidates found",
            f"{investment.get('candidate_count', 0):,}",
        )

        c2.metric(
            "Investment objective",
            investment.get("ranking_method", "-"),
        )

        c3.metric(
            "Budget cap",
            f"${result.get('input', {}).get('budget', 0):,.0f}",
        )

        st.subheader("Investment Recommendations")

        if ranking.empty:
            st.warning("No movies matched the selected criteria.")

        else:
            columns = [
                "investment_rank",
                "title",
                "release_year",
                "budget",
                "revenue",
                "roi_percent",
                "roi_tier",
                "vote_average",
                "popularity",
                "decision_score",
            ]

            columns = [
                column
                for column in columns
                if column in ranking.columns
            ]

            st.dataframe(
                ranking[columns],
                hide_index=True,
                use_container_width=True,
            )

            score_components = {
                "Rating": "rating_score",
                "Popularity": "popularity_score",
                "Genre potential": "genre_potential_score",
                "ROI": "roi_score",
                "Profit": "profit_score",
                "Risk proxy": "risk_proxy_score",
            }

            if "title" in ranking.columns:
                selected_title = st.selectbox(
                    "Inspect decision score breakdown",
                    ranking["title"].tolist(),
                    key="investment_score_movie",
                )

                selected_row = ranking[
                    ranking["title"] == selected_title
                ].iloc[0]

                breakdown = pd.Series({
                    label: selected_row[column]
                    for label, column in score_components.items()
                    if column in selected_row.index
                    and pd.notna(selected_row[column])
                })

                if not breakdown.empty:
                    st.bar_chart(
                        breakdown,
                        horizontal=True,
                    )

        # ----------------------------------------------------
        # GENRE POTENTIAL
        # ----------------------------------------------------

        st.divider()
        st.subheader("Genre Potential")

        potential = to_df(
            market.get("genre_potential")
        )

        if potential.empty:
            st.info("No genre potential data available.")

        else:
            if "potential_score" in potential.columns:
                potential = potential.sort_values(
                    "potential_score",
                    ascending=False,
                )

                st.bar_chart(
                    potential.set_index("genre_name")[
                        "potential_score"
                    ]
                )

            columns = [
                "genre_name",
                "potential_score",
                "potential_category",
                "market_score",
                "market_growth_score",
                "rating_score",
                "movie_count",
            ]

            columns = [
                column
                for column in columns
                if column in potential.columns
            ]

            st.dataframe(
                potential[columns],
                hide_index=True,
                use_container_width=True,
            )

        # ----------------------------------------------------
        # GENRE TRENDS
        # ----------------------------------------------------

        st.divider()
        st.subheader("Genre Trends")

        trends = to_df(
            market.get("genre_trends")
        )

        if trends.empty:
            st.info("No genre trend data available.")

        elif "year" in trends.columns:

            trend_metrics = {
                "Market share (%)": "genre_market_share",
                "Movie count": "movie_count",
                "Average popularity": "average_popularity",
                "Average weighted rating": "average_weighted_rating",
                "Average revenue": "average_revenue",
            }

            metric_label = st.selectbox(
                "Trend metric",
                list(trend_metrics),
                key="trend_metric",
            )

            metric = trend_metrics[metric_label]

            if metric not in trends.columns:
                st.warning("The selected metric is unavailable.")

            else:
                available_trend_genres = sorted(
                    trends["genre_name"].dropna().unique()
                )

                default_genres = [
                    genre
                    for genre in ["Action", "Drama", "Comedy"]
                    if genre in available_trend_genres
                ]

                selected_trend_genres = st.multiselect(
                    "Genres to compare",
                    available_trend_genres,
                    default=default_genres,
                    key="trend_genres",
                )

                trend_view = trends[
                    trends["genre_name"].isin(
                        selected_trend_genres
                    )
                ]

                if not trend_view.empty:
                    chart_data = trend_view.pivot_table(
                        index="year",
                        columns="genre_name",
                        values=metric,
                    )

                    st.line_chart(chart_data)
                else:
                    st.info("Select at least one genre.")

                st.caption(
                    "Recent years may be incomplete, so apparent "
                    "declines should be interpreted carefully."
                )

        # ----------------------------------------------------
        # TRENDING MOVIES
        # ----------------------------------------------------

        st.divider()
        st.subheader("Trending Movies")

        trending = to_df(
            market.get("trending_movies")
        )

        if trending.empty:
            st.info("No trending movie data available.")

        else:
            columns = [
                "trending_rank",
                "title",
                "release_year",
                "genres",
                "popularity",
                "vote_average",
                "budget",
                "revenue",
            ]

            columns = [
                column
                for column in columns
                if column in trending.columns
            ]

            st.dataframe(
                trending[columns],
                hide_index=True,
                use_container_width=True,
            )

            st.caption(
                "Trending movies represent a popularity snapshot, "
                "not a historical trend."
            )

        # ----------------------------------------------------
        # LIMITATIONS
        # ----------------------------------------------------

        with st.expander("Analysis limitations and warnings"):

            warnings = result.get(
                "summary", {}
            ).get("warnings", [])

            for warning in warnings:
                st.warning(warning)

            st.markdown(
                """
                - Budget and revenue are missing for some movies.
                - ROI is calculated only from available financial data.
                - Vote count is a proxy for risk, not a direct measurement.
                - Genre potential scores are relative indicators.
                """
            )



# ============================================================
# PAGE 3: MOVIE RECOMMENDATIONS
# ============================================================

elif page == "Movie Recommendations":

    st.header("Movie Recommendations")

    st.write(
        "Select a movie to discover similar titles using "
        "content similarity, audience ratings, and business performance."
    )

    # --------------------------------------------------------
    # MOVIE SEARCH
    # --------------------------------------------------------

    movie_search = st.text_input(
        "Search for an input movie",
        placeholder="e.g. Pulp Fiction",
        key="recommendation_search",
    )

    if movie_search.strip():

        matching_movies = movies[
            movies["title"].str.contains(
                movie_search.strip(),
                case=False,
                na=False,
                regex=False,
            )
        ].drop_duplicates(
            subset=["id"]
        ).copy()

        matching_movies["popularity"] = pd.to_numeric(
            matching_movies["popularity"],
            errors="coerce",
        ).fillna(0)

        matching_movies = matching_movies.sort_values(
            by="popularity",
            ascending=False,
        ).head(20).copy()

        if matching_movies.empty:
            st.warning("No matching movies found.")

        else:
            matching_movies["id"] = (
                matching_movies["id"].astype("int64")
            )

            movie_options = {
                int(row["id"]): row["title"]
                for _, row in matching_movies.iterrows()
            }

            # Prepare movie data for the HTML component
            movie_data = []

            for _, row in matching_movies.iterrows():

                release_date = row["release_date"]

                if pd.notna(release_date):
                    release_date = release_date.strftime("%Y-%m-%d")
                else:
                    release_date = ""

                overview = row["overview"]

                if pd.isna(overview):
                    overview = ""

                movie_data.append({
                    "id": int(row["id"]),
                    "title": str(row["title"]),
                    "release_date": release_date,
                    "overview": str(overview),
                })

            st.write("**Search results**")

            # ------------------------------------------------
            # MOVIE SELECTOR
            # ------------------------------------------------

            component_selection = movie_selector(
                movies=movie_data,
                selected_id=st.session_state.get(
                    "recommendation_movie"
                ),
                is_processing=st.session_state.get(
                    "recommendation_processing",
                    False,
                ),
                default=None,
                key="movie_selector",
            )

            # ------------------------------------------------
            # HANDLE COMPONENT EVENTS
            # ------------------------------------------------

            if isinstance(component_selection, dict):

                event_id = component_selection.get("event_id")
                last_event_id = st.session_state.get(
                    "movie_selector_last_event_id"
                )

                # Prevent the same component event from being
                # processed again on unrelated Streamlit reruns.
                if event_id and event_id != last_event_id:

                    st.session_state[
                        "movie_selector_last_event_id"
                    ] = event_id

                    action = component_selection.get("action")

                    movie_id = component_selection.get("movie_id")

                    if movie_id is not None:
                        movie_id = int(movie_id)

                    # ----------------------------------------
                    # MOVIE SELECTION EVENT
                    # ----------------------------------------

                    if (
                        action == "select"
                        and movie_id in movie_options
                        and not st.session_state.get(
                            "recommendation_processing",
                            False,
                        )
                    ):
                        st.session_state[
                            "recommendation_movie"
                        ] = movie_id

                    # ----------------------------------------
                    # RECOMMENDATION REQUEST EVENT
                    # ----------------------------------------

                    elif (
                        action == "recommend"
                        and movie_id in movie_options
                        and not st.session_state.get(
                            "recommendation_processing",
                            False,
                        )
                    ):

                        # Preserve the exact movie ID submitted
                        # by JavaScript for this request.
                        st.session_state[
                            "recommendation_movie"
                        ] = movie_id

                        st.session_state[
                            "recommendation_processing"
                        ] = True

                        st.session_state[
                            "recommendation_results"
                        ] = None

                        st.session_state[
                            "recommendation_source"
                        ] = None

                        try:
                            with st.spinner(
                                "Generating and ranking recommendations..."
                            ):
                                results = get_movie_recommendations(
                                    movie_id=movie_id,
                                    top_n=100,
                                    content_weight=0.50,
                                    rating_weight=0.30,
                                    business_weight=0.20,
                                )

                            st.session_state[
                                "recommendation_results"
                            ] = results.head(10)

                            st.session_state[
                                "recommendation_source"
                            ] = movie_id

                        except Exception as exc:
                            st.error(
                                f"Recommendation failed: {exc}"
                            )

                        finally:
                            st.session_state[
                                "recommendation_processing"
                            ] = False

            # ------------------------------------------------
            # SELECTED MOVIE
            # ------------------------------------------------

            selected_movie_id = st.session_state.get(
                "recommendation_movie"
            )

            if selected_movie_id in movie_options:

                st.caption(
                    f"Selected movie: {movie_options[selected_movie_id]}"
                )

                if st.session_state.get(
                    "recommendation_processing",
                    False,
                ):
                    st.info(
                        "Recommendations are being generated. "
                        "Movie selection is temporarily disabled."
                    )

                st.divider()

                # --------------------------------------------
                # DISPLAY RESULTS
                # --------------------------------------------

                results = st.session_state.get(
                    "recommendation_results"
                )

                recommendation_source = st.session_state.get(
                    "recommendation_source"
                )

                if (
                    results is not None
                    and recommendation_source == selected_movie_id
                ):

                    st.subheader(
                        f"Top 10 Movies Similar to "
                        f"{movie_options[selected_movie_id]}"
                    )

                    if results.empty:
                        st.info(
                            "No recommendations with matching business "
                            "metrics were found."
                        )

                    else:
                        display_columns = [
                            "title",
                            "similarity_score",
                            "weighted_rating",
                            "roi_tier",
                            "final_score",
                        ]

                        display_columns = [
                            column
                            for column in display_columns
                            if column in results.columns
                        ]

                        st.dataframe(
                            results[display_columns],
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "similarity_score": st.column_config.NumberColumn(
                                    "Content similarity",
                                    format="%.3f",
                                ),
                                "weighted_rating": st.column_config.NumberColumn(
                                    "Weighted rating",
                                    format="%.2f",
                                ),
                                "final_score": st.column_config.ProgressColumn(
                                    "Hybrid score",
                                    min_value=0,
                                    max_value=100,
                                    format="%.1f",
                                ),
                            },
                        )


    else:
        st.info(
            "Enter a movie title above to start discovering recommendations."
        )