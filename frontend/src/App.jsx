import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';   // <-- path fixed
import Home from './pages/Home.jsx';
import Negotiation from './pages/Negotiation.jsx';
import Optimization from './pages/Optimization.jsx';
import Approval from './pages/Approval.jsx';
import Analytics from './pages/Analytics.jsx';
import Evaluation from './pages/Evaluation.jsx';

export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/negotiation" element={<Negotiation />} />
        <Route path="/optimization" element={<Optimization />} />
        <Route path="/approval" element={<Approval />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route
          path="*"
          element={
            <div className="container">
              <div className="card">404 — Page not found</div>
            </div>
          }
        />
      </Routes>
    </>
  );
}
