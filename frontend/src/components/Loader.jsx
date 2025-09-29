export default function Loader({ text = 'Loading…' }) {
return (
<div className="row" style={{ alignItems: 'center', gap: 8 }}>
<div className="spinner" style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid #2a3246', borderTopColor: '#80b3ff', animation: 'spin 0.8s linear infinite' }} />
<span>{text}</span>
<style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
</div>
)
}