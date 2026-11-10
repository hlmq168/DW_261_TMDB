import { useEffect, useMemo, useRef, useState } from "react";
import "./Dashboard.css";

const API_URL =
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

const COLOR_COUNT = 19; // number of .chart-color-N classes in Dashboard.css
const DEFAULT_SELECTED_GENRES = 5;

const colorClass = (index) => `chart-color-${index % COLOR_COUNT}`;

function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || value === "") return "N/A";

  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";

  return number.toLocaleString("en-US", {
    maximumFractionDigits: digits,
  });
}

function formatPercent(value) {
  return value === null || value === undefined
    ? "N/A"
    : `${formatNumber(value, 2)}%`;
}

function formatHeader(column) {
  return column
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatCell(value) {
  if (value === null || value === undefined || value === "") return "N/A";
  if (typeof value === "number") return formatNumber(value, 2);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function getRows(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function splitGenres(genres) {
  if (!genres) return [];

  return String(genres)
    .split(",")
    .map((genre) => genre.trim())
    .filter(Boolean);
}

function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const [yearRange, setYearRange] = useState("10");
  const [selectedGenres, setSelectedGenres] = useState([]);
  const selectionInitialized = useRef(false);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchDashboard() {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(`${API_URL}/dashboard/`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Dashboard request failed: ${response.status}`);
        }

        const data = await response.json();
        setDashboardData(data);
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message || "Unable to load dashboard data.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    fetchDashboard();

    return () => controller.abort();
  }, [reloadKey]);

  const overview = dashboardData?.overview || {};

  const distribution = getRows(dashboardData?.genre_distribution);
  const trends = getRows(dashboardData?.genre_trends);
  const potential = getRows(dashboardData?.genre_potential);
  const trendingMovies = getRows(dashboardData?.trending_movies);

  const trendingTopN = dashboardData?.meta?.trending_top_n ?? 10;
  const trendingMinVotes = dashboardData?.meta?.trending_min_votes ?? 100;

  // Order genres by their latest market share.
  const sortedDistribution = useMemo(
    () =>
      [...distribution].sort(
        (a, b) =>
          (b.analysis_market_share || 0) -
          (a.analysis_market_share || 0)
      ),
    [distribution]
  );

  // Genres from the latest distribution first, then any genres that
  // only appear in the historical data.
  const allGenres = useMemo(() => {
    const latest = sortedDistribution.map((genre) => genre.genre_name);
    const known = new Set(latest);

    const historicalOnly = [
      ...new Set(trends.map((item) => item.genre_name)),
    ]
      .filter((name) => name && !known.has(name))
      .sort();

    return [...latest, ...historicalOnly];
  }, [sortedDistribution, trends]);

  // Stable color index per genre (shared by the chart and distribution bars).
  const genreColorIndex = useMemo(
    () => new Map(allGenres.map((name, index) => [name, index])),
    [allGenres]
  );

  // Select the top genres once, when data first arrives.
  useEffect(() => {
    if (selectionInitialized.current || allGenres.length === 0) return;

    selectionInitialized.current = true;
    setSelectedGenres(allGenres.slice(0, DEFAULT_SELECTED_GENRES));
  }, [allGenres]);

  // Get available years from the historical trend data.
  const availableYears = useMemo(
    () =>
      [
        ...new Set(
          trends
            .map((item) => Number(item.year))
            .filter(Number.isFinite)
        ),
      ].sort((a, b) => a - b),
    [trends]
  );

  const displayedYears = useMemo(() => {
    if (yearRange === "all") return availableYears;

    return availableYears.slice(-Number(yearRange));
  }, [availableYears, yearRange]);

  // Fast lookup of market share by "year|genre".
  const trendLookup = useMemo(() => {
    const lookup = new Map();

    trends.forEach((item) => {
      lookup.set(
        `${Number(item.year)}|${item.genre_name}`,
        item.analysis_market_share
      );
    });

    return lookup;
  }, [trends]);

  // Build one series for each genre.
  const trendChart = useMemo(
    () => ({
      series: allGenres.map((name) => ({
        name,
        values: displayedYears.map(
          (year) => trendLookup.get(`${year}|${name}`) ?? null
        ),
      })),
    }),
    [allGenres, displayedYears, trendLookup]
  );

  // Keep the original series index so colors do not change
  // when genres are selected or deselected.
  const visibleSeries = trendChart.series
    .map((series, index) => ({
      ...series,
      originalIndex: index,
    }))
    .filter((series) => selectedGenres.includes(series.name));

  // Calculate the Y-axis scale using only selected genres.
  const chartValues = visibleSeries
    .flatMap((series) => series.values)
    .filter(
      (value) => value !== null && Number.isFinite(Number(value))
    );

  // Market share is never negative. A max that is a multiple of 4 gives
  // whole-number ticks across the 4 grid steps (e.g. 0, 4, 8, 12, 16).
  const yMinimum = 0;
  const yMaximum = Math.max(
    4,
    Math.ceil(Math.max(0, ...chartValues.map(Number)) / 4) * 4
  );

  // X position for a year index.
  const getX = (index) =>
    displayedYears.length === 1
      ? 420
      : 55 + (index / (displayedYears.length - 1)) * 730;

  // Thin out x-axis labels so "All years" doesn't overlap.
  const labelStep = Math.max(1, Math.ceil(displayedYears.length / 12));

  function toggleGenre(genreName) {
    setSelectedGenres((current) =>
      current.includes(genreName)
        ? current.filter((name) => name !== genreName)
        : [...current, genreName]
    );
  }

  function selectAllGenres() {
    setSelectedGenres(allGenres);
  }

  function clearAllGenres() {
    setSelectedGenres([]);
  }

  if (loading) {
    return (
      <div className="dashboard-loading">
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <h2>Unable to load dashboard</h2>
        <p>{error}</p>
        <button onClick={() => setReloadKey((key) => key + 1)}>
          Retry
        </button>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="dashboard-empty">
        No dashboard data available.
      </div>
    );
  }

  const maxPopularity = Math.max(
    0,
    ...trendingMovies.map((movie) => Number(movie.popularity) || 0)
  );

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>TMDB Analytics Dashboard</h1>
          <p>
            An overview of the movie dataset, genre trends, and
            currently trending movies.
          </p>
        </div>
      </div>

      {/* Overview */}
      <section className="dashboard-section">
        <h2>Overview</h2>

        <div className="overview-grid">
          <div className="overview-card">
            <p>Total Movies</p>
            <h3>{formatNumber(overview.total_movies, 0)}</h3>
          </div>

          <div className="overview-card">
            <p>Latest Analysis Year</p>
            <h3>{overview.latest_year ?? "N/A"}</h3>
          </div>

          <div className="overview-card">
            <p>Number of Genres</p>
            <h3>{formatNumber(overview.genre_count, 0)}</h3>
          </div>

          <div className="overview-card">
            <p>Leading Genre</p>
            <h3>{overview.leading_genre || "N/A"}</h3>
            <span>
              {formatPercent(overview.leading_genre_market_share)}
            </span>
          </div>
        </div>
      </section>

      {/* Genre Distribution */}
      <section className="dashboard-section">
        <h2>Genre Distribution</h2>
        <p className="section-description">
          Market-share distribution across genres in the latest
          analysis year.
        </p>

        <div className="genre-distribution-list">
          {sortedDistribution.map((genre) => (
            <div
              className="genre-distribution-item"
              key={genre.genre_name}
            >
              <div className="genre-distribution-info">
                <span>{genre.genre_name}</span>
                <span>
                  {formatPercent(genre.analysis_market_share)}
                </span>
              </div>

              <div className="genre-distribution-bar">
                <div
                  className={`genre-distribution-fill ${colorClass(
                    genreColorIndex.get(genre.genre_name) ?? 0
                  )}`}
                  style={{
                    width: `${Math.max(
                      0,
                      Math.min(100, Number(genre.analysis_market_share) || 0)
                    )}%`,
                  }}
                />
              </div>

              <div className="genre-distribution-meta">
                <span>
                  {formatNumber(genre.movie_count, 0)} movies
                </span>
                <span>
                  Average rating:{" "}
                  {formatNumber(genre.average_weighted_rating, 2)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Genre Trends */}
      <section className="dashboard-section">
        <div className="section-heading-row">
          <div>
            <h2>Genre Market-Share Trends</h2>
            <p className="section-description">
              Historical market-share movement across movie genres.
            </p>
          </div>

          <select
            aria-label="Year range"
            value={yearRange}
            onChange={(event) => setYearRange(event.target.value)}
          >
            <option value="5">Last 5 years</option>
            <option value="10">Last 10 years</option>
            <option value="20">Last 20 years</option>
            <option value="all">All years</option>
          </select>
        </div>

        <div className="genre-legend-controls">
          <div className="genre-legend">
            {trendChart.series.map((series, index) => (
              <button
                type="button"
                key={series.name}
                className={`genre-legend-item ${
                  selectedGenres.includes(series.name) ? "selected" : ""
                }`}
                onClick={() => toggleGenre(series.name)}
                aria-pressed={selectedGenres.includes(series.name)}
              >
                <span className={`legend-dot ${colorClass(index)}`} />
                <span>{series.name}</span>
              </button>
            ))}
          </div>

          <div className="genre-legend-actions">
            <button type="button" onClick={selectAllGenres}>
              Select all
            </button>
            <button type="button" onClick={clearAllGenres}>
              Clear all
            </button>
          </div>
        </div>

        {visibleSeries.length === 0 ? (
          <div className="chart-empty">
            Select one or more genres above to display their
            historical market-share trends.
          </div>
        ) : (
          <div className="trend-chart-container">
            <svg
              className="trend-chart"
              viewBox="0 0 820 300"
              role="img"
              aria-label="Historical genre market-share trends"
            >
              {/* Y-axis grid and labels */}
              {[0, 1, 2, 3, 4].map((step) => {
                const y = 235 - step * 50;
                const value =
                  yMinimum +
                  ((yMaximum - yMinimum) * step) / 4;

                return (
                  <g key={step}>
                    <line
                      x1="55"
                      y1={y}
                      x2="785"
                      y2={y}
                      className="chart-grid-line"
                    />

                    <text
                      x="45"
                      y={y + 4}
                      textAnchor="end"
                      className="chart-axis-label"
                    >
                      {value.toFixed(0)}%
                    </text>
                  </g>
                );
              })}

              {/* X-axis labels (thinned when there are many years) */}
              {displayedYears.map((year, index) =>
                index % labelStep === 0 ? (
                  <text
                    key={year}
                    x={getX(index)}
                    y="260"
                    textAnchor="middle"
                    className="chart-axis-label"
                  >
                    {year}
                  </text>
                ) : null
              )}

              {/* Selected genre lines and points */}
              {visibleSeries.map((series) => {
                // Split into segments so a missing year leaves a gap
                // instead of drawing a misleading line across it.
                const segments = [];
                let current = [];

                series.values.forEach((value, index) => {
                  if (value === null || !Number.isFinite(Number(value))) {
                    if (current.length) segments.push(current);
                    current = [];
                    return;
                  }

                  current.push({
                    x: getX(index),
                    y:
                      235 -
                      ((Number(value) - yMinimum) /
                        (yMaximum - yMinimum)) *
                        200,
                    value,
                    year: displayedYears[index],
                  });
                });

                if (current.length) segments.push(current);

                const color = colorClass(series.originalIndex);

                return (
                  <g key={series.name}>
                    {segments.map(
                      (segment, segmentIndex) =>
                        segment.length > 1 && (
                          <polyline
                            key={segmentIndex}
                            points={segment
                              .map((point) => `${point.x},${point.y}`)
                              .join(" ")}
                            className={`trend-line ${color}`}
                          />
                        )
                    )}

                    {segments.flat().map((point) => (
                      <circle
                        key={point.year}
                        cx={point.x}
                        cy={point.y}
                        r="3.5"
                        className={`trend-point ${color}`}
                      >
                        <title>
                          {series.name} - {point.year}:{" "}
                          {formatPercent(point.value)}
                        </title>
                      </circle>
                    ))}
                  </g>
                );
              })}
            </svg>
          </div>
        )}

        <p className="chart-note">
          Select genres above to compare their historical market-share
          trends. The vertical axis adjusts to the selected genres.
        </p>
      </section>

      {/* Genre Potential */}
      <section className="dashboard-section">
        <h2>Genre Potential</h2>
        <p className="section-description">
          Predicted genre opportunities for{" "}
          {potential[0]?.year ?? "the latest year"}, ranked by
          potential score.
        </p>

        <div className="table-container">
          <table className="dashboard-table">
            <thead>
              <tr>
                <th>Genre</th>
                <th>Potential</th>
                <th>Potential Score</th>
                <th>Market Score</th>
                <th>Growth Score</th>
                <th>Rating Score</th>
              </tr>
            </thead>

            <tbody>
              {potential.map((row) => (
                <tr key={row.genre_name}>
                  <td>
                    <strong>{row.genre_name}</strong>
                  </td>
                  <td>
                    <span
                      className={`potential-badge potential-${String(
                        row.potential_category ?? ""
                      ).toLowerCase()}`}
                    >
                      {row.potential_category ?? "N/A"}
                    </span>
                  </td>
                  <td>
                    <strong>{formatNumber(row.potential_score, 2)}</strong>
                  </td>
                  <td>{formatNumber(row.market_score, 1)}</td>
                  <td>{formatNumber(row.market_growth_score, 1)}</td>
                  <td>{formatNumber(row.rating_score, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {potential.length === 0 && (
            <p className="table-empty">No genre potential data available.</p>
          )}
        </div>
      </section>

      {/* Trending Movies */}
      <section className="dashboard-section">
        <h2>Trending Movies</h2>
        <p className="section-description">
          Top {trendingTopN} movies ranked by popularity, filtered by a
          minimum vote count of {trendingMinVotes}.
        </p>

        {trendingMovies.length === 0 ? (
          <p className="table-empty">No trending movies available.</p>
        ) : (
          <ol className="trending-list">
            {trendingMovies.map((movie) => {
              const genres = splitGenres(movie.genres);
              const popularity = Number(movie.popularity) || 0;
              const rating = Number(movie.weighted_rating);

              const ratingTier = !Number.isFinite(rating)
                ? "none"
                : rating >= 7.5
                ? "great"
                : rating >= 6.5
                ? "good"
                : "fair";

              return (
                <li
                  className="trending-item"
                  key={`${movie.trending_rank}-${movie.title}`}
                >
                  <span
                    className={`trending-rank ${
                      Number(movie.trending_rank) === 1
                        ? "rank-1"
                        : Number(movie.trending_rank) === 2
                        ? "rank-2"
                        : Number(movie.trending_rank) === 3
                        ? "rank-3"
                        : ""
                    }`}
                  >
                    {movie.trending_rank}
                  </span>

                  <div className="trending-main">
                    <div className="trending-title-row">
                      <h3 title={movie.title}>{movie.title}</h3>
                      <span className="trending-year">
                        {movie.release_year ?? "N/A"}
                      </span>
                    </div>

                    <div className="trending-genres">
                      {genres.slice(0, 3).map((genre) => (
                        <span className="genre-chip" key={genre}>
                          {genre}
                        </span>
                      ))}

                      {genres.length > 3 && (
                        <span
                          className="genre-chip more"
                          title={genres.slice(3).join(", ")}
                        >
                          +{genres.length - 3}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="trending-popularity">
                    <div className="trending-popularity-info">
                      <span>Popularity</span>
                      <strong>{formatNumber(movie.popularity, 0)}</strong>
                    </div>

                    <div className="trending-bar">
                      <div
                        className="trending-bar-fill"
                        style={{
                          width: `${
                            maxPopularity
                              ? (popularity / maxPopularity) * 100
                              : 0
                          }%`,
                        }}
                      />
                    </div>
                  </div>

                  <div className="trending-rating">
                    <span className={`rating-pill rating-${ratingTier}`}>
                      {formatNumber(movie.weighted_rating, 1)}
                    </span>
                    <span className="trending-votes">
                      {formatNumber(movie.vote_count, 0)} votes
                    </span>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}

export default Dashboard;