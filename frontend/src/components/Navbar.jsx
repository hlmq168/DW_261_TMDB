
function Navbar({ activePage, onNavigate }) {
  const navItems = [
    { id: "dashboard", label: "Dashboard" },
    { id: "investment", label: "Investment Analysis" },
    { id: "recommendations", label: "Recommendations" }
  ];

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-icon">T</span>
        <span>
          TMDB <strong>DSS</strong>
        </span>
      </div>

      <nav className="navigation">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${
              activePage === item.id ? "active" : ""
            }`}
            onClick={() => onNavigate(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </header>
  );
}

export default Navbar;
