import { useState } from 'react'
import { optimize } from '../services/api'
import Loader from '../components/Loader'


export default function Optimization() {
const [itemsJson, setItemsJson] = useState('[\n { "sku": "CHR-ERG-01", "qty": 20, "maxUnit": 200 }\n]')
const [budget, setBudget] = useState(4000)
const [loading, setLoading] = useState(false)
const [result, setResult] = useState(null)
const [error, setError] = useState('')


async function onSubmit(e) {
e.preventDefault()
setLoading(true); setError(''); setResult(null)
try {
const items = JSON.parse(itemsJson)
const res = await optimize({ items, budget })
setResult(res)
} catch (err) {
setError(err?.response?.data?.error || err.message)
} finally { setLoading(false) }
}


return (
<div className="container grid" style={{ gap: 16 }}>
<div className="card grid" style={{ gap: 12 }}>
<h2>Budget‑Aware Optimization</h2>
<form className="grid" style={{ gap: 10 }} onSubmit={onSubmit}>
<div className="grid" style={{ gap: 6 }}>
<label>Items (JSON)</label>
<textarea rows={6} value={itemsJson} onChange={e => setItemsJson(e.target.value)} />
</div>
<div className="grid" style={{ gap: 6, width: 220 }}>
<label>Budget (€)</label>
<input type="number" value={budget} onChange={e => setBudget(Number(e.target.value))} />
</div>
<div className="row" style={{ gap: 8 }}>
<button type="submit" disabled={loading}>{loading ? 'Optimizing…' : 'Optimize'}</button>
{loading && <Loader />}
</div>
</form>
</div>


{error && <div className="card" style={{ borderColor: '#702a2a' }}><strong>Error:</strong> {error}</div>}
{result && (
<div className="card grid" style={{ gap: 10 }}>
<h3>Optimization Result</h3>
<pre>{JSON.stringify(result, null, 2)}</pre>
</div>
)}
</div>
)
}