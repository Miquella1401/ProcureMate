import { useState } from 'react'
import { approve } from '../services/api'
import Loader from '../components/Loader'

export default function Approval() {
  const [poDraft, setPoDraft] = useState(`{
  "poNumber": "PO-0001",
  "vendor": "Acme Corp",
  "items": [{ "sku": "CHR-ERG-01", "qty": 20, "price": 190 }]
}`)
  const [approver, setApprover] = useState('manager@supply.example')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function onSubmit(e) {
    e.preventDefault()
    setLoading(true); setError(''); setResult(null)
    try {
      let draft
      try {
        draft = JSON.parse(poDraft)
      } catch {
        throw new Error('PO Draft must be valid JSON')
      }
      const res = await approve({ poDraft: draft, approver })
      setResult(res)
    } catch (err) {
      setError(err?.response?.data?.error || err.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container grid" style={{ gap: 16 }}>
      <div className="card grid" style={{ gap: 12 }}>
        <h2>Approval Workflow</h2>
        <form className="grid" style={{ gap: 10 }} onSubmit={onSubmit}>
          <div className="grid" style={{ gap: 6 }}>
            <label>PO Draft (JSON)</label>
            <textarea rows={8} value={poDraft} onChange={e => setPoDraft(e.target.value)} />
          </div>
          <div className="grid" style={{ gap: 6, width: 320 }}>
            <label>Approver Email</label>
            <input value={approver} onChange={e => setApprover(e.target.value)} />
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button type="submit" disabled={loading}>
              {loading ? 'Submitting…' : 'Submit for Approval'}
            </button>
            {loading && <Loader />}
          </div>
        </form>
      </div>

      {error && (
        <div className="card" style={{ borderColor: '#702a2a' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="card grid" style={{ gap: 10 }}>
          <h3>Approval Result</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
