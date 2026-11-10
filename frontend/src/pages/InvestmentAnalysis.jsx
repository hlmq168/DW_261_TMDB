import { useEffect, useState } from "react";
import "./InvestmentAnalysis.css";

const API_URL = "http://127.0.0.1:8000/api";

function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }

  return Number(value).toLocaleString("en-US", {
    maximumFractionDigits: digits,
  });
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }

  return Number(value).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }

  return `${formatNumber(value, 2)}%`;
}

function InvestmentAnalysis() {
  const [budget, setBudget] = useState("50000000");
  const [genres, setGenres] = useState([]);
  const [availableGenres, setAvailableGenres] = useState([]);
  const [genresLoading, setGenresLoading] = useState(true);
  const [genreError, setGenreError] = useState("");
  const [objective, setObjective] = useState("BALANCED");
  const [minVotes, setMinVotes] = useState("100");
  const [topN, setTopN] = useState("20");

  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchGenres() {
      try {
        const response = await fetch(`${API_URL}/investment/genres`);

        if (!response.ok) {
          throw new Error("Failed to load available genres.");
        }

        const data = await response.json();
        setAvailableGenres(data.genres || []);
      } catch (err) {
        setGenreError(err.message);
      } finally {
        setGenresLoading(false);
      }
    }

    fetchGenres();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();

    setLoading(true);
    setError("");
    setAnalysisData(null);

    const requestBody = {
      budget: Number(budget),
      genres: genres.length > 0 ? genres : null,
      objective,
      min_votes: Number(minVotes),
      top_n: Number(topN),
    };

    try {
      const response = await fetch(`${API_URL}/investment/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to run investment analysis."
        );
      }

      setAnalysisData(data);
    } catch (err) {
      setError(err.message || "Unable to connect to the backend.");
    } finally {
      setLoading(false);
    }
  }

  function handleGenreChange(genre) {
    setGenres(current =>
      current.includes(genre)
        ? current.filter(item => item !== genre)
        : [...current, genre]
    );
  }

  const investment = analysisData?.investment_analysis || {};
  const summary = analysisData?.summary || {};

  const recommendations = Array.isArray(summary.top_recommendations)
    ? summary.top_recommendations
    : Array.isArray(investment.ranking)
      ? investment.ranking.slice(0, 5)
      : [];

  return (
    <div className="investment-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">DECISION SUPPORT SYSTEM</p>
          <h1>Investment Analysis</h1>
          <p className="subtitle">
            Evaluate movie investment opportunities based on your criteria.
          </p>
        </div>
      </section>

      <section className="investment-section">
        <div className="investment-section-heading">
          <h2>Investment Criteria</h2>
          <p>
            Define your constraints and choose how the movies should be ranked.
          </p>
        </div>

        <form className="investment-form" onSubmit={handleSubmit}>
          <div className="investment-form-grid">
            <div className="investment-field">
              <label htmlFor="budget">Maximum Movie Budget (USD)</label>
              <input
                id="budget"
                type="number"
                min="1"
                step="any"
                value={budget}
                onChange={(event) => setBudget(event.target.value)}
                required
              />
              <small>
                Only movies with production budgets less than or equal to this amount are
                considered.
              </small>
            </div>

            <div className="investment-field">
              <label htmlFor="objective">Investment Objective</label>
              <select
                id="objective"
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
              >
                <option value="BALANCED">Balanced</option>
                <option value="HIGH_ROI">High ROI</option>
                <option value="HIGH_PROFIT">High Profit</option>
                <option value="POPULARITY">Popularity</option>
                <option value="LOW_RISK">Low Risk</option>
              </select>
              <small>
                Low Risk uses vote count as a proxy, not a measured financial
                risk.
              </small>
            </div>

            <div className="investment-field">
              <label htmlFor="minVotes">Minimum Vote Count</label>
              <input
                id="minVotes"
                type="number"
                min="0"
                value={minVotes}
                onChange={(event) => setMinVotes(event.target.value)}
                required
              />
              <small>Minimum number of TMDB votes for each movie.</small>
            </div>

            <div className="investment-field">
              <label htmlFor="topN">Number of Results</label>
              <input
                id="topN"
                type="number"
                min="5"
                max="50"
                step="1"
                value={topN}
                onChange={e => setTopN(e.target.value)}
                required
              />
              <small>Choose between 5 and 50 ranked movies.</small>

              <div className="investment-field genre-field">
              <label>Genres</label>

              {genresLoading ? (
                <p>Loading genres...</p>
              ) : genreError ? (
                <p className="genre-error">{genreError}</p>
              ) : (
                <div className="genre-options">
                  {availableGenres.map(genre => (
                    <label key={genre} className="genre-option">
                      <input
                        type="checkbox"
                        checked={genres.includes(genre)}
                        onChange={() => handleGenreChange(genre)}
                      />
                      <span>{genre}</span>
                    </label>
                  ))}
                </div>
              )}

              <small>
                {genres.length > 0
                  ? `${genres.length} genre(s) selected`
                  : "No selection: automatic top 5 genre selection"}
              </small>
            </div>
            </div>
          </div>
          <button
            type="submit"
            className="investment-submit"
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Run Investment Analysis"}
          </button>
        </form>
      </section>

      {loading && (
        <div className="investment-status">
          Running investment analysis. This may take a moment...
        </div>
      )}

      {error && (
        <div className="investment-error">
          <strong>Unable to run analysis</strong>
          <p>{error}</p>
        </div>
      )}

      {analysisData && (
        <>
          <section className="investment-section">
            <div className="investment-section-heading">
              <h2>Analysis Overview</h2>
              <p>
                Results generated using the {investment.ranking_method} ranking
                objective.
              </p>
            </div>

            <div className="investment-overview-grid">
              <div className="investment-overview-card">
                <p>Eligible Candidates</p>
                <h3>{formatNumber(investment.candidate_count, 0)}</h3>
              </div>

              <div className="investment-overview-card">
                <p>Ranked Movies</p>
                <h3>
                  {formatNumber(
                    Array.isArray(investment.ranking)
                      ? investment.ranking.length
                      : 0,
                    0
                  )}
                </h3>
              </div>

              <div className="investment-overview-card">
                <p>Recommended Movies</p>
                <h3>
                  {formatNumber(summary.recommended_movie_count, 0)}
                </h3>
              </div>

              <div className="investment-overview-card">
                <p>Ranking Objective</p>
                <h3 className="objective-value">
                  {investment.ranking_method || "N/A"}
                </h3>
              </div>
            </div>
          </section>

          <section className="investment-section">
            <div className="investment-section-heading">
              <h2>Top 5 Investment Candidates</h2>
              <p>The five highest-ranked movies under the selected objective.</p>
            </div>

            {recommendations.length > 0 ? (
              <div className="investment-table-container">
                <table className="investment-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Movie</th>
                      <th>Budget</th>
                      <th>Revenue</th>
                      <th>Profit</th>
                      <th>ROI</th>
                      <th>Decision Score</th>
                    </tr>
                  </thead>

                  <tbody>
                    {recommendations.map((movie) => (
                      <tr key={movie.tmdb_id || movie.movie_sk}>
                        <td>
                          <strong>#{movie.investment_rank}</strong>
                        </td>
                        <td>
                          <strong>{movie.title}</strong>
                          <span className="investment-movie-year">
                            {movie.release_year || "Year unavailable"}
                          </span>
                        </td>
                        <td>{formatCurrency(movie.budget)}</td>
                        <td>{formatCurrency(movie.revenue)}</td>
                        <td>{formatCurrency(movie.profit)}</td>
                        <td>
                          <span
                            className={`investment-roi ${
                              movie.roi_percent > 0
                                ? "positive"
                                : movie.roi_percent < 0
                                  ? "negative"
                                  : ""
                            }`}
                          >
                            {formatPercent(movie.roi_percent)}
                          </span>
                        </td>
                        <td>{formatNumber(movie.decision_score, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="investment-empty">
                No recommendations were returned for these criteria.
              </div>
            )}
          </section>
          
          <section className="investment-section">
            <div className="investment-section-heading">
              <h2>Full Investment Ranking</h2>
              <p>
                All {investment.ranking?.length || 0} movies ranked under the selected
                investment objective.
              </p>
            </div>

            {Array.isArray(investment.ranking) && investment.ranking.length > 0 ? (
              <div className="investment-table-container">
                <table className="investment-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Movie</th>
                      <th>Budget</th>
                      <th>Revenue</th>
                      <th>Profit</th>
                      <th>ROI</th>
                      <th>Decision Score</th>
                    </tr>
                  </thead>

                  <tbody>
                    {investment.ranking.map(movie => (
                      <tr key={movie.tmdb_id || movie.movie_sk}>
                        <td>
                          <strong>#{movie.investment_rank}</strong>
                        </td>

                        <td>
                          <strong>{movie.title}</strong>
                          <span className="investment-movie-year">
                            {movie.release_year || "Year unavailable"}
                          </span>
                        </td>

                        <td>{formatCurrency(movie.budget)}</td>
                        <td>{formatCurrency(movie.revenue)}</td>
                        <td>{formatCurrency(movie.profit)}</td>

                        <td>
                          <span
                            className={`investment-roi ${
                              movie.roi_percent > 0
                                ? "positive"
                                : movie.roi_percent < 0
                                  ? "negative"
                                  : ""
                            }`}
                          >
                            {formatPercent(movie.roi_percent)}
                          </span>
                        </td>

                        <td>{formatNumber(movie.decision_score, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="investment-empty">
                No ranked movies are available.
              </div>
            )}
          </section>

          {Array.isArray(summary.warnings) && summary.warnings.length > 0 && (
            <section className="investment-warnings">
              <h3>Important Notes</h3>
              <ul>
                {summary.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default InvestmentAnalysis;
