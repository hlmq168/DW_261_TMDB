import { useEffect, useRef, useState } from "react";
import "./Recommendations.css";
const API_URL = "http://127.0.0.1:8000/api";
const PAGE_SIZE = 12;

function formatScore(value) {
  if (value === null || value === undefined) return "N/A";
  return Number(value).toFixed(2);
}

function Recommendations() {
  const [search, setSearch] = useState("");
  const [allMovies, setAllMovies] = useState([]);
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [submittedSearch, setSubmittedSearch] = useState("");
  const [loadingMovies, setLoadingMovies] = useState(false);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [error, setError] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const searchController = useRef(null);
  const recommendationController = useRef(null);

  const movies = allMovies;
  const total = movies.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const paginatedMovies = movies.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  useEffect(() => {
    const trimmedSearch = submittedSearch.trim();

    if (!trimmedSearch) {
      setAllMovies([]);
      setLoadingMovies(false);
      return;
    }

    async function fetchMovies() {
      if (searchController.current) {
        searchController.current.abort();
      }

      const controller = new AbortController();
      searchController.current = controller;

      try {
        setLoadingMovies(true);
        setError("");

        const response = await fetch(
          `${API_URL}/movies/search?q=${encodeURIComponent(
            trimmedSearch
          )}&limit=500&offset=0`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("Failed to search movies.");
        }

        const data = await response.json();

        const sortedMovies = [...(data.results || [])].sort((a, b) => {
          const popularityA = Number(a.popularity);
          const popularityB = Number(b.popularity);

          return (
            (Number.isFinite(popularityB) ? popularityB : 0) -
            (Number.isFinite(popularityA) ? popularityA : 0)
          );
        });

        setAllMovies(sortedMovies);
        setCurrentPage(1);
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingMovies(false);
        }
      }
    }

    fetchMovies();
  }, [submittedSearch]);

  useEffect(() => {
    return () => {
      searchController.current?.abort();
      recommendationController.current?.abort();
    };
  }, []);

  function clearRecommendations() {
    setRecommendations([]);
    setError("");
  }

  function handleSearchChange(value) {
    setSearch(value);
    setAllMovies([]);
    setSelectedMovie(null);
    setCurrentPage(1);
    clearRecommendations();
  }

  function handleSelectMovie(movie) {
    setSelectedMovie(movie);
    clearRecommendations();
  }

  async function handleRecommend() {
    if (!selectedMovie) return;

    recommendationController.current?.abort();

    const controller = new AbortController();
    recommendationController.current = controller;

    try {
      setLoadingRecommendations(true);
      setError("");
      setRecommendations([]);

      const response = await fetch(`${API_URL}/recommendations/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          movie_id: selectedMovie.id,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to generate recommendations.");
      }

      const data = await response.json();

      setRecommendations(
        Array.isArray(data) ? data : data.results || []
      );
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message);
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoadingRecommendations(false);
      }
    }
  }

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="eyebrow">CONTENT-BASED ANALYSIS</p>
          <h1>Movie Recommendations</h1>
          <p className="subtitle">
            Find similar movies using content similarity and business scores.
          </p>
        </div>
      </section>

      <section className="search-section">
        <form
          className="search-box"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmittedSearch(search.trim());
          }}
        >
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search for a movie..."
          />
        </form>

        {loadingMovies && <p>Searching movies...</p>}

        {movies.length > 0 && (
          <>
            <div className="movie-grid">
              {paginatedMovies.map((movie) => (
                <button
                  key={movie.id}
                  className={`movie-card ${
                    selectedMovie?.id === movie.id ? "selected" : ""
                  }`}
                  onClick={() => handleSelectMovie(movie)}
                  disabled={loadingRecommendations}
                >
                  <strong>{movie.title}</strong>
                  <span>
                    {movie.release_year || movie.release_date || "Year unknown"}
                  </span>
                  <span>Popularity: {formatScore(movie.popularity)}</span>
                </button>
              ))}
            </div>

            <div className="pagination">
              <button
                disabled={currentPage === 1 || loadingRecommendations}
                onClick={() => setCurrentPage((page) => page - 1)}
              >
                Previous
              </button>

              <span>
                Page {currentPage} of {totalPages}
              </span>

              <button
                disabled={currentPage >= totalPages || loadingRecommendations}
                onClick={() => setCurrentPage((page) => page + 1)}
              >
                Next
              </button>
            </div>
          </>
        )}

        {submittedSearch && !loadingMovies && movies.length === 0 && (
          <p>No movies found.</p>
        )}

        {selectedMovie && (
          <div className="selected-movie">
            <div>
              <p className="eyebrow">SELECTED MOVIE</p>
              <h3>{selectedMovie.title}</h3>
            </div>

            <button
              className="recommend-button"
              onClick={handleRecommend}
              disabled={loadingRecommendations}
            >
              {loadingRecommendations
                ? "Generating..."
                : "Recommend"}
            </button>
          </div>
        )}
      </section>

      {error && <p className="error-message">{error}</p>}

      {loadingRecommendations && (
        <p className="loading-message">
          Generating movie recommendations...
        </p>
      )}

      {recommendations.length > 0 && (
        <section className="recommendation-section">
          <div className="section-heading">
            <h2>Recommended Movies</h2>
            <p>{recommendations.length} results</p>
          </div>

          <div className="table-container">
            <table className="recommendation-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Movie</th>
                  <th>Content Similarity</th>
                  <th>Weighted Rating</th>
                  <th>ROI Tier</th>
                  <th>Final Score</th>
                </tr>
              </thead>

              <tbody>
                {recommendations.map((movie, index) => (
                  <tr key={movie.id || index}>
                    <td>{index + 1}</td>
                    <td>{movie.title}</td>
                    <td>
                      {formatScore(
                        movie.content_similarity ??
                        movie.similarity_score
                      )}
                    </td>
                    <td>{formatScore(movie.weighted_rating)}</td>
                    <td>
                      <span
                        className={`roi-tier ${
                          movie.roi_tier?.toLowerCase() || ""
                        }`}
                      >
                        {movie.roi_tier || "N/A"}
                      </span>
                    </td>
                    <td>
                      {formatScore(movie.final_score)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

export default Recommendations;
