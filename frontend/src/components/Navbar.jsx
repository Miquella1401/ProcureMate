import { NavLink } from 'react-router-dom'


export default function Navbar() {
const link = ({ isActive }) => ({ className: isActive ? 'active' : undefined })
return (
<nav>
<div className="container row" style={{ alignItems: 'center', justifyContent: 'space-between' }}>
<div className="row" style={{ gap: 8 }}>
<NavLink to="/" {...{ className: ({ isActive }) => (isActive ? 'active' : '') }}>Home</NavLink>
<NavLink to="/negotiation" className={link}>Negotiation</NavLink>
<NavLink to="/optimization" className={link}>Optimization</NavLink>
<NavLink to="/approval" className={link}>Approval</NavLink>
<NavLink to="/analytics" className={link}>Analytics</NavLink>
<NavLink to="/evaluation" className={link}>Evaluation</NavLink>
</div>
<div style={{ opacity: 0.8 }}>ProcureMate</div>
</div>
</nav>
)
}