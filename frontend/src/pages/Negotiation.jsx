import { useState } from 'react'
import { negotiate } from '../services/api'
import Loader from '../components/Loader'


export default function Negotiation() {
const [form, setForm] = useState({ vendor: 'Acme Corp', product: 'office chair', quantity: 10 })
const [loading, setLoading] = useState(false)
const [data, setData] = useState(null)
const [error, setError] = useState('')


const onChange = e => {
const { name, value } = e.target
setForm(f => ({ ...f, [name]: name === 'quantity' ? Number(value) : value }))
}


async function onSubmit(e) {
e.preventDefault()
setLoading(true); setError(''); setData(null)
try {
const res = await negotiate(form)
setData(res)
} catch (err) {
setError(err?.response?.data?.error || err.message)
} finally { setLoading(false) }
}


return (
<div className="container grid" style={{ gap: 16 }}>
<div className="card grid" style={{ gap: 12 }}>
<h2>Negotiation Agent</h2>
<form className="grid" style={{ gap: 10 }} onSubmit={onSubmit}>
<div className="row" style={{ gap: 10 }}>
<div className="grid" style={{ flex: 1 }}>
<label>Vendor</label>
<input name="vendor" value={form.vendor} onChange={onChange} />
</div>
<div className="grid" style={{ flex: 1 }}>
<label>Product</label>
<input name="product" value={form.product} onChange={onChange} />
</div>
<div className="grid" style={{ width: 160 }}>
<label>Quantity</label>
<input type="number" name="quantity" value={form.quantity} onChange={onChange} />
</div>
</div>
<div className="row" style={{ gap: 8 }}>
<button type="submit" disabled={loading}>{loading ? 'Generating…' : 'Generate Email'}</button>
{loading && <Loader />}
</div>
</form>
</div>


{error && <div className="card" style={{ borderColor: '#702a2a' }}><strong>Error:</strong> {error}</div>}


{data && (
<div className="card grid" style={{ gap: 10 }}>
<h3>Generated Email</h3>
<pre>{data.email_text || JSON.stringify(data, null, 2)}</pre>
</div>
)}
</div>
)
}