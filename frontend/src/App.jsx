
import { useState } from "react";
import "./App.css";

import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import Recommendations from "./pages/Recommendations";
import InvestmentAnalysis from "./pages/InvestmentAnalysis";

function App() {
  const [activePage, setActivePage] = useState("dashboard");

  return (
    <div className="app">
      <Navbar
        activePage={activePage}
        onNavigate={setActivePage}
      />

      <main className="main-content">
        {activePage === "dashboard" && <Dashboard />}

        {activePage === "investment" && <InvestmentAnalysis />}

        {activePage === "recommendations" && <Recommendations />}
      </main>
    </div>
  );
}

export default App;
