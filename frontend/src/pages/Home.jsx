import { useState } from 'react'
import { runProcurement } from '../services/api'
import Loader from '../components/Loader'


export default function Home() {
const [requestText, setRequestText] = useState('Order 20 ergonomic chairs under €200 each.')
const [policyText, setPolicyText] = useState('')
const [loading, setLoading] = useState(false)
const [result, setResult] = useState(null)
const [error, setError] = useState('')


async function handleRun(e) {
e.preventDefault()
setLoading(true); setError(''); setResult(null)
try {
const res = await runProcurement(requestText, policyText)
setResult(res.final)
} catch (err) {
setError(err?.response?.data?.error || err.message || 'Request failed')
} finally {
setLoading(false)
}
}


return (
<div className="container grid" style={{ gap: 16 }}>
<div className="card grid">
<h2>One‑Click Pipeline</h2>
<form className="grid" style={{ gap: 12 }} onSubmit={handleRun}>
<div className="grid" style={{ gap: 6 }}>
<label>Request</label>
<textarea rows={3} value={requestText} onChange={e => setRequestText(e.target.value)} />
</div>
<div className="grid" style={{ gap: 6 }}>
<label>Policy (optional)</label>
<textarea rows={3} value={policyText} onChange={e => setPolicyText(e.target.value)} />
</div>
<div className="row" style={{ gap: 8 }}>
<button type="submit" disabled={loading}>{loading ? 'Running…' : 'Run Agents'}</button>
{loading && <Loader />}
</div>
</form>
</div>


{error && <div className="card" style={{ borderColor: '#702a2a' }}><strong>Error:</strong> {error}</div>}


{result && (
<div className="card grid" style={{ gap: 12 }}>
<h3>Result</h3>
<pre>{JSON.stringify(result, null, 2)}</pre>
</div>
)}
</div>
)
}