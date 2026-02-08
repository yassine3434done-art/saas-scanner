import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar.jsx";

import Home from "./pages/Home.jsx";
import Sites from "./pages/Sites.jsx";
import Scans from "./pages/Scans.jsx";
import ScanDetails from "./pages/ScanDetails.jsx";

export default function App() {
  return (
    <div style={{ fontFamily: "Arial, sans-serif", minHeight: "100vh", background: "#fafafa" }}>
      <NavBar />

      <main style={{ maxWidth: 1000, margin: "0 auto", padding: 16 }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/sites" element={<Sites />} />
          <Route path="/scans" element={<Scans />} />
          <Route path="/scans/:id" element={<ScanDetails />} />
        </Routes>
      </main>
    </div>
  );
}