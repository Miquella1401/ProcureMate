import { useEffect, useState } from 'react'
import { getKpis } from '../services/api'
import Loader from '../components/Loader'
import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts'


export default function Analytics() {
const [loading, setLoading] = useState(true)
const [kpis, setKpis] = useState(null)
const [error, setError] = useState('')


useEffect(() => {
(async () => {
try {
const data = await getKpis()
setKpis(data)
} catch (err) {
setError(err?.response?.data?.error || err.message)
} finally { setLoading(false) }
})()
}, [])


const series = kpis?.savings_over_time || [
{ week: 'W1', savings: 0 },
{ week: 'W2', savings: 0 },
]


return (
<div className="container grid" style={{ gap: 16 }}>
<div className="card grid" style={{ gap: 12 }}>
<h2>KPI Dashboard</h2>
{loading && <Loader text="Fetching KPIs…" />}
{error && <div style={{ color: '#f19999' }}>{error}</div>}


<div className="card">
<div style={{ width: '100%', height: 260 }}>
<ResponsiveContainer>
<LineChart data={series} margin={{ left: 8, right: 8, top: 10, bottom: 10 }}>
<CartesianGrid strokeDasharray="3 3" />
<XAxis dataKey="week" />
<YAxis />
<Tooltip />
<Line type="monotone" dataKey="savings" />
</LineChart>
</ResponsiveContainer>
</div>
</div>


<div className="grid" style={{ gap: 8 }}>
<div><strong>Total Savings:</strong> €{kpis?.total_savings ?? 0}</div>
<div><strong>Preferred Vendors:</strong> {(kpis?.preferred_vendors || []).join(', ') || '—'}</div>
</div>
</div>
</div>
)
}