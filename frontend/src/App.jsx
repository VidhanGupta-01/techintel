import { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { BrainCircuit, LineChart, FileText, Activity, Search, Sparkles } from 'lucide-react';
import './index.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [overview, setOverview] = useState(null);
  const [scurveData, setScurveData] = useState([]);
  const [patents, setPatents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // AI Insight State
  const [insight, setInsight] = useState('');
  const [generating, setGenerating] = useState(false);

  // Fetch overview or search results
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        let url = 'http://localhost:8000/api/overview';
        if (searchQuery.trim() !== '') {
          url = `http://localhost:8000/api/search?q=${encodeURIComponent(searchQuery)}`;
        }
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.results) {
          setOverview(data.results);
        } else {
          setOverview(data);
        }
        
        setInsight('');
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
      }
    };

    const delayDebounceFn = setTimeout(() => {
      fetchDashboardData();
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  // Fetch static scurve and patent data once
  useEffect(() => {
    const fetchStaticData = async () => {
      try {
        const [scurveRes, patentsRes] = await Promise.all([
          fetch('http://localhost:8000/api/scurve'),
          fetch('http://localhost:8000/api/patents')
        ]);
        
        const scurveRaw = await scurveRes.json();
        const patentsRaw = await patentsRes.json();
        
        const formattedScurve = scurveRaw.labels.map((label, index) => ({
          year: label,
          adoption: scurveRaw.values[index]
        }));
        
        setScurveData(formattedScurve);
        setPatents(patentsRaw);
      } catch (error) {
        console.error("Failed to fetch static data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchStaticData();
  }, []);

  const generateInsight = async () => {
    setGenerating(true);
    setInsight('');
    try {
      const url = `http://localhost:8000/api/generate-insight?q=${encodeURIComponent(searchQuery)}`;
      const res = await fetch(url);
      const data = await res.json();
      
      setTimeout(() => {
        setInsight(data.insight);
        setGenerating(false);
      }, 1500);
    } catch (error) {
      console.error("Failed to generate insight", error);
      setGenerating(false);
    }
  };

  if (loading) {
    return <div className="loader">Initializing AI Core...</div>;
  }

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <BrainCircuit size={28} color="#c084fc" />
          <span>TechIntel</span>
        </div>
        
        <nav className="nav-links">
          <div 
            className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <Activity size={20} />
            Overview
          </div>
          <div 
            className={`nav-link ${activeTab === 'forecast' ? 'active' : ''}`}
            onClick={() => setActiveTab('forecast')}
          >
            <LineChart size={20} />
            Forecasting
          </div>
          <div 
            className={`nav-link ${activeTab === 'patents' ? 'active' : ''}`}
            onClick={() => setActiveTab('patents')}
          >
            <FileText size={20} />
            Patents DB
          </div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="header">
          <h1>
            {activeTab === 'dashboard' && 'Technology Overview'}
            {activeTab === 'forecast' && 'Forecasting & Signals'}
            {activeTab === 'patents' && 'Raw Database'}
          </h1>
          
          {activeTab === 'dashboard' && (
            <div className="search-container">
              <Search size={18} color="#94a3b8" />
              <input 
                type="text" 
                className="search-input" 
                placeholder="Search technologies..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          )}
        </header>

        {activeTab === 'dashboard' && (
          <>
            <div className="dashboard-grid">
              <div className="glass-card">
                <div className="card-title">Total Patents Tracked</div>
                <div className="card-value">{overview?.total_patents}</div>
              </div>
              <div className="glass-card">
                <div className="card-title">Publications Analyzed</div>
                <div className="card-value">{overview?.total_publications}</div>
              </div>
              <div className="glass-card" style={{ borderColor: 'rgba(139, 92, 246, 0.4)'}}>
                <div className="card-title">Avg. Tech Readiness (TRL)</div>
                <div className="card-value" style={{ color: '#c084fc'}}>{overview?.average_trl} / 9</div>
              </div>
            </div>

            {/* AI Insight Section */}
            <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr', marginBottom: '1.5rem' }}>
               <div className="glass-card" style={{ background: 'rgba(139, 92, 246, 0.05)', borderColor: 'rgba(139, 92, 246, 0.2)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <div className="card-title" style={{ margin: 0, color: '#c084fc', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Sparkles size={16} /> Simulated AI Analyst
                    </div>
                    <button 
                      onClick={generateInsight}
                      disabled={generating}
                      style={{
                        background: 'linear-gradient(to right, #3b82f6, #8b5cf6)',
                        color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '0.5rem',
                        cursor: generating ? 'not-allowed' : 'pointer', fontWeight: 600, opacity: generating ? 0.7 : 1
                      }}
                    >
                      {generating ? 'Analyzing...' : 'Generate Insight'}
                    </button>
                  </div>
                  
                  {insight && (
                    <div style={{ padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '0.5rem', lineHeight: '1.6' }}>
                      {insight}
                    </div>
                  )}
                  {!insight && !generating && (
                    <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      Click the button above to generate a strategic intelligence report based on the current search data.
                    </div>
                  )}
               </div>
            </div>

            <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr' }}>
              <div className="glass-card">
                <div className="card-title" style={{ marginBottom: '1.5rem' }}>Active Technology Sectors</div>
                {overview?.active_sectors.length > 0 ? (
                  <div className="list-container">
                    {overview.active_sectors.map((sector, idx) => (
                      <div key={idx} className="sector-item">
                        <span style={{ fontWeight: 500 }}>{sector}</span>
                        <span style={{ color: 'var(--accent-blue)' }}>Monitoring</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)' }}>No technologies match your search.</div>
                )}
              </div>
            </div>
          </>
        )}

        {activeTab === 'forecast' && (
          <div className="dashboard-grid" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="glass-card" style={{ flex: 1, minHeight: '500px' }}>
              <div className="card-title">Technology S-Curve (Adoption over time)</div>
              <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', fontSize: '0.9rem' }}>
                AI-driven analysis of patent filing velocity and publication volume.
              </p>
              
              <div style={{ height: '400px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={scurveData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorAdoption" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="year" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="adoption" 
                      stroke="#c084fc" 
                      strokeWidth={3}
                      fillOpacity={1} 
                      fill="url(#colorAdoption)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'patents' && (
          <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr' }}>
            <div className="glass-card">
              <div className="card-title" style={{ marginBottom: '1.5rem' }}>Raw Patent Database</div>
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Title</th>
                      <th>Category</th>
                      <th>TRL</th>
                      <th>Date Filed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {patents.map((p) => (
                      <tr key={p.id}>
                        <td style={{ color: 'var(--accent-blue)', fontWeight: '500' }}>{p.id}</td>
                        <td>{p.title}</td>
                        <td>{p.category}</td>
                        <td>
                          <span style={{ 
                            background: 'rgba(139, 92, 246, 0.2)', 
                            color: '#c084fc', 
                            padding: '0.25rem 0.5rem', 
                            borderRadius: '0.25rem',
                            fontSize: '0.875rem',
                            fontWeight: '600'
                          }}>
                            TRL {p.trl}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-muted)' }}>{p.date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
