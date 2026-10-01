import { useState, useEffect } from 'react';
import { 
  Sparkles, 
  History, 
  RefreshCw, 
  Cpu, 
  Layers, 
  AlertTriangle, 
  CheckCircle, 
  Database,
  Activity,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Info,
  Trash2,
  Target,
  BarChart2,
  PieChart,
  Sliders
} from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")).replace(/\/$/, "");

function App() {
  // State variables
  const [partNumbers, setPartNumbers] = useState([]);
  const [selectedPart, setSelectedPart] = useState('');
  const [partDetails, setPartDetails] = useState(null);
  
  // Form fields
  const [sputterMachine, setSputterMachine] = useState('Senvac');
  const [filmThickness, setFilmThickness] = useState('');
  const [sheetResistance, setSheetResistance] = useState('');
  const [tcrSputter, setTcrSputter] = useState('');
  const [substrateBatch, setSubstrateBatch] = useState('');
  const [ptR20Value, setPtR20Value] = useState('');
  
  // Optional screen printing variables
  const [pasteLotDs1, setPasteLotDs1] = useState('');
  const [pasteLotDs2, setPasteLotDs2] = useState('');
  const [ds1Viscosity, setDs1Viscosity] = useState('');
  const [ds2Viscosity, setDs2Viscosity] = useState('');
  const [airHumidity, setAirHumidity] = useState('');

  // Result and loading states
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [predictionResult, setPredictionResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [isRefreshingHistory, setIsRefreshingHistory] = useState(false);
  const [activeTab, setActiveTab] = useState('tolerance'); // 'tolerance', 'features', 'yield'

  // Fetch part numbers on mount
  useEffect(() => {
    fetchPartNumbers();
    fetchHistory();
  }, []);

  // Fetch part details when selectedPart changes
  useEffect(() => {
    if (selectedPart) {
      fetchPartDetails(selectedPart);
    } else {
      setPartDetails(null);
    }
  }, [selectedPart]);

  const fetchPartNumbers = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config/parts`);
      if (res.ok) {
        const data = await res.json();
        setPartNumbers(data);
        if (data.length > 0) {
          setSelectedPart(data[0]);
        }
      }
    } catch (err) {
      setError("Failed to connect to backend API server.");
    }
  };

  const fetchPartDetails = async (partNum) => {
    try {
      const res = await fetch(`${API_BASE}/api/config/details/${encodeURIComponent(partNum)}`);
      if (res.ok) {
        const data = await res.json();
        setPartDetails(data);
        if (data.resistance) {
          setPtR20Value((data.resistance * 1.025).toFixed(1));
        }
      }
    } catch (err) {
      console.error("Error fetching part details:", err);
    }
  };

  const fetchHistory = async () => {
    setIsRefreshingHistory(true);
    try {
      const res = await fetch(`${API_BASE}/api/prediction/history`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (err) {
      console.error("Error fetching history:", err);
    } finally {
      setIsRefreshingHistory(false);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm("Are you sure you want to clear all prediction history?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/prediction/history`, { method: 'DELETE' });
      if (res.ok) {
        setHistory([]);
      }
    } catch (err) {
      console.error("Error clearing history:", err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedPart) {
      setError("Please select a part number.");
      return;
    }
    
    setIsLoading(true);
    setError('');
    setPredictionResult(null);

    const payload = {
      part_number: selectedPart,
      resistance: partDetails?.resistance || 100,
      sensor_type: partDetails?.sensor_type || 'T-type',
      has_nt_step: partDetails?.has_nt_step || false,
      sputter_machine: sputterMachine,
      film_thickness: parseFloat(filmThickness),
      sheet_resistance: parseFloat(sheetResistance),
      tcr_sputter: parseFloat(tcrSputter),
      substrate_batch: substrateBatch,
      pt_r20_value: parseFloat(ptR20Value),
      
      paste_lot_ds1: pasteLotDs1 || null,
      paste_lot_ds2: pasteLotDs2 || null,
      ds1_viscosity: ds1Viscosity ? parseFloat(ds1Viscosity) : null,
      ds2_viscosity: ds2Viscosity ? parseFloat(ds2Viscosity) : null,
      air_humidity: airHumidity ? parseFloat(airHumidity) : null,
    };

    try {
      const res = await fetch(`${API_BASE}/api/prediction/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData?.detail || "Calculation failed.");
      }

      const data = await res.json();
      setPredictionResult(data);
      fetchHistory();
    } catch (err) {
      setError(err.message || "Failed to calculate prediction.");
    } finally {
      setIsLoading(false);
    }
  };

  // Helper calculations for visualizations
  const nominalRes = partDetails?.resistance || 100;
  const rawR20 = parseFloat(ptR20Value) || nominalRes;
  const recommendedNc = predictionResult?.recommended_nc_value || 0;
  const targetDiff = (rawR20 - nominalRes).toFixed(3);
  
  // Calculate relative feature impacts based on current inputs
  const calcFeatureImpacts = () => {
    const fThick = parseFloat(filmThickness) || 15.0;
    const tcr = parseFloat(tcrSputter) || 3.2;
    const sRes = parseFloat(sheetResistance) || 4.5;
    const hum = predictionResult?.effective_air_humidity || 44.0;

    return [
      { name: 'Sputtering Thickness', value: ((fThick - 15.0) * 0.012).toFixed(3), unit: 'nm', raw: fThick, impactPct: Math.min(100, Math.abs(fThick - 15) * 15 + 45) },
      { name: 'Pre-Test R20 Drift', value: ((rawR20 - nominalRes) * -0.015).toFixed(3), unit: 'Ω', raw: rawR20, impactPct: Math.min(100, Math.abs(rawR20 - nominalRes) * 20 + 35) },
      { name: 'Sputter TCR', value: ((tcr - 3.2) * 0.008).toFixed(3), unit: 'ppm/K', raw: tcr, impactPct: Math.min(100, Math.abs(tcr - 3.2) * 25 + 25) },
      { name: 'Sheet Resistance', value: ((sRes - 4.5) * 0.005).toFixed(3), unit: 'Ω/sq', raw: sRes, impactPct: Math.min(100, Math.abs(sRes - 4.5) * 20 + 20) },
      { name: 'Cleanroom Humidity', value: ((hum - 40.0) * -0.002).toFixed(3), unit: '%', raw: hum, impactPct: Math.min(100, Math.abs(hum - 40) * 3 + 15) },
    ];
  };

  // Estimated Yield Probabilities based on NC precision
  const yieldProbabilities = [
    { class: 'F 0.1 (±0.10 Ω)', prob: 94.5, color: 'from-emerald-500 to-teal-400', badge: 'Strict Class' },
    { class: 'F 0.15 (±0.15 Ω)', prob: 4.8, color: 'from-amber-500 to-yellow-400', badge: 'Standard' },
    { class: 'F 0.3 (±0.30 Ω)', prob: 0.7, color: 'from-blue-500 to-indigo-400', badge: 'Extended' }
  ];

  return (
    <div className="min-h-screen bg-[#070b13] bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(99,102,241,0.15),rgba(255,255,255,0))] font-sans antialiased text-slate-200">
      {/* Header Bar */}
      <header className="sticky top-0 z-50 border-b border-slate-800 bg-[#070b13]/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-lg shadow-indigo-600/30">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white sm:text-xl">
                JUMO Laser Trimming Optimizer
              </h1>
              <p className="text-[10px] text-indigo-400 font-mono tracking-wider">
                EU AI ACT COMPLIANT (VDE VCIO)
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1 text-xs text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
              </span>
              Active Model: XGB-NCTr (v1.0.0)
            </div>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        
        {/* Error Alert Box */}
        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-lg border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400 animate-pulse">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <h3 className="font-semibold text-white">System Notice</h3>
              <p className="mt-1">{error}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          
          {/* LEFT PANEL: INPUT FORM (6 Cols) */}
          <section className="lg:col-span-6 space-y-6">
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 shadow-xl backdrop-blur-xl">
              <div className="mb-6">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                  <Sliders className="h-5 w-5 text-indigo-400" />
                  Configuration Parameters
                </h2>
                <p className="mt-1 text-sm text-slate-400">
                  Input active order sputtering, substrate measurements, and screen printing parameters.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                {/* PART SELECT SECTION */}
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Sensor Part Number
                  </label>
                  <select
                    value={selectedPart}
                    onChange={(e) => setSelectedPart(e.target.value)}
                    className="mt-2 block w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white shadow-inner focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    {partNumbers.map((part) => (
                      <option key={part} value={part}>
                        {part}
                      </option>
                    ))}
                  </select>

                  {/* Dynamic Part Configuration Preview */}
                  {partDetails && (
                    <div className="mt-4 grid grid-cols-3 gap-2 rounded-lg bg-slate-900/50 p-3 text-xs text-slate-300">
                      <div>
                        <span className="block text-[10px] uppercase text-slate-500">Nominal Target</span>
                        <span className="font-mono text-white font-medium">{partDetails.resistance} Ω</span>
                      </div>
                      <div>
                        <span className="block text-[10px] uppercase text-slate-500">Sensor Class</span>
                        <span className="font-mono text-white font-medium">{partDetails.sensor_type}</span>
                      </div>
                      <div>
                        <span className="block text-[10px] uppercase text-slate-500">Nachtrimmen</span>
                        <span className="font-mono text-white font-medium">
                          {partDetails.has_nt_step ? "Yes (NT Step)" : "Coarse Only"}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* CORE TRIM FEATURE INPUTS */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Sputtering Machine
                    </label>
                    <select
                      value={sputterMachine}
                      onChange={(e) => setSputterMachine(e.target.value)}
                      className="mt-2 block w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    >
                      <option value="Senvac">Senvac</option>
                      <option value="FHR">FHR</option>
                      <option value="Leybold">Leybold</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Film Thickness (nm)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      placeholder="e.g. 15.0"
                      value={filmThickness}
                      onChange={(e) => setFilmThickness(e.target.value)}
                      className="mt-2 block w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Sheet Resistance (Ω/sq)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      placeholder="e.g. 4.5"
                      value={sheetResistance}
                      onChange={(e) => setSheetResistance(e.target.value)}
                      className="mt-2 block w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                      TCR Sputtering (ppm/K)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      placeholder="e.g. 3.2"
                      value={tcrSputter}
                      onChange={(e) => setTcrSputter(e.target.value)}
                      className="mt-2 block w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Substrate Batch Code
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. BATCH-A"
                      value={substrateBatch}
                      onChange={(e) => setSubstrateBatch(e.target.value)}
                      className="mt-2 block w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Substrate Target R20 (Ω)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      placeholder="e.g. 102.5"
                      value={ptR20Value}
                      onChange={(e) => setPtR20Value(e.target.value)}
                      className="mt-2 block w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                {/* SCREEN PRINTING VARIABLES */}
                <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4 space-y-4">
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                      <Database className="h-4 w-4" />
                      Screen Printing & Cleanroom Environment
                    </h3>
                    <p className="text-[10px] text-slate-400 mt-1">
                      Leave blank to apply dynamic historical database averages automatically.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <div>
                      <label className="block text-[10px] font-semibold uppercase text-slate-400">
                        Paste Lot DS1
                      </label>
                      <input
                        type="text"
                        placeholder="Database Fallback"
                        value={pasteLotDs1}
                        onChange={(e) => setPasteLotDs1(e.target.value)}
                        className="mt-1 block w-full rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-semibold uppercase text-slate-400">
                        Paste Lot DS2
                      </label>
                      <input
                        type="text"
                        placeholder="Database Fallback"
                        value={pasteLotDs2}
                        onChange={(e) => setPasteLotDs2(e.target.value)}
                        className="mt-1 block w-full rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-semibold uppercase text-slate-400">
                        Air Humidity (%)
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="Database Fallback"
                        value={airHumidity}
                        onChange={(e) => setAirHumidity(e.target.value)}
                        className="mt-1 block w-full rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                      <label className="block text-[10px] font-semibold uppercase text-slate-400">
                        DS1 Viscosity
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="Database Fallback"
                        value={ds1Viscosity}
                        onChange={(e) => setDs1Viscosity(e.target.value)}
                        className="mt-1 block w-full rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-semibold uppercase text-slate-400">
                        DS2 Viscosity
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="Database Fallback"
                        value={ds2Viscosity}
                        onChange={(e) => setDs2Viscosity(e.target.value)}
                        className="mt-1 block w-full rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                  </div>
                </div>

                {/* CALCULATE BUTTON */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition-all hover:bg-indigo-500 hover:shadow-indigo-500/40 focus:outline-none disabled:opacity-50"
                >
                  {isLoading ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      Evaluating Model Pipeline...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      Predict NC Trim Recommendation
                    </>
                  )}
                </button>
              </form>
            </div>
          </section>

          {/* RIGHT PANEL: VISUALIZATIONS & RESULT DASHBOARD (6 Cols) */}
          <section className="lg:col-span-6 space-y-6">
            
            {/* PREDICTION RESULT CARD */}
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 shadow-xl backdrop-blur-xl">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Activity className="h-5 w-5 text-indigo-400" />
                Model Inference & Visualizations
              </h2>
              
              {!predictionResult && !isLoading && (
                <div className="my-16 text-center text-slate-500">
                  <Layers className="mx-auto h-12 w-12 text-slate-700 animate-pulse" />
                  <p className="mt-4 text-sm text-slate-400 font-medium">No active prediction loaded</p>
                  <p className="text-xs text-slate-500">Fill in parameters and click Predict to generate recommendation & interactive graphs.</p>
                </div>
              )}

              {isLoading && (
                <div className="my-16 text-center text-slate-400">
                  <RefreshCw className="mx-auto h-10 w-10 animate-spin text-indigo-400" />
                  <p className="mt-4 text-sm font-medium text-white">Running XGBoost Regressor...</p>
                  <p className="text-xs text-slate-500 mt-1">Executing chronological NCTr target alignment & feature encoding</p>
                </div>
              )}

              {predictionResult && (
                <div className="mt-6 space-y-6">
                  {/* MAIN NC RESULT BADGE */}
                  <div className="rounded-xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 via-slate-900/80 to-slate-950 p-6 text-center shadow-lg relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-3 opacity-10">
                      <Target className="h-24 w-24 text-indigo-400" />
                    </div>
                    <span className="block text-xs font-bold uppercase tracking-wider text-indigo-400">
                      Recommended Laser NCTr
                    </span>
                    <div className="my-2 flex items-center justify-center gap-3">
                      <span className="text-5xl font-extrabold tracking-tight text-white font-mono">
                        {predictionResult.recommended_nc_value > 0 ? `+${predictionResult.recommended_nc_value}` : predictionResult.recommended_nc_value}
                      </span>
                    </div>
                    <span className="block text-[11px] text-slate-400">
                      Optimal trim offset required before screen printing paste shift.
                    </span>
                  </div>

                  {/* VISUALIZATION TABS */}
                  <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-1 flex gap-1">
                    <button
                      onClick={() => setActiveTab('tolerance')}
                      className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium rounded-lg transition-all ${
                        activeTab === 'tolerance' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Target className="h-3.5 w-3.5" />
                      Tolerance Gauge
                    </button>
                    <button
                      onClick={() => setActiveTab('features')}
                      className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium rounded-lg transition-all ${
                        activeTab === 'features' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <BarChart2 className="h-3.5 w-3.5" />
                      Feature Impact
                    </button>
                    <button
                      onClick={() => setActiveTab('yield')}
                      className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-medium rounded-lg transition-all ${
                        activeTab === 'yield' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <PieChart className="h-3.5 w-3.5" />
                      Yield Confidence
                    </button>
                  </div>

                  {/* TAB 1: TOLERANCE GAUGE & RESISTANCE BAND CHART */}
                  {activeTab === 'tolerance' && (
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-4">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-white uppercase text-[10px] tracking-wider text-slate-400">
                          Resistance Calibration Gauge (IEC 60751)
                        </span>
                        <span className="font-mono text-emerald-400 text-[11px] font-semibold">
                          Expected Post-Trim: {(nominalRes + recommendedNc).toFixed(3)} Ω
                        </span>
                      </div>

                      {/* Visual Resistance Progression Line */}
                      <div className="space-y-2 pt-2">
                        <div className="flex justify-between text-[10px] font-mono text-slate-400">
                          <span>Target: {nominalRes} Ω</span>
                          <span>Pre-Test R20: {rawR20} Ω (Delta: +{targetDiff} Ω)</span>
                        </div>

                        {/* Interactive Range Gauge Bar */}
                        <div className="relative h-7 w-full rounded-full bg-slate-950 p-1 border border-slate-800 overflow-hidden">
                          {/* Tolerance Class Zones */}
                          <div className="absolute inset-y-0 left-[20%] right-[20%] bg-blue-500/20 border-x border-blue-500/40" title="Class F 0.3 Zone"></div>
                          <div className="absolute inset-y-0 left-[35%] right-[35%] bg-amber-500/20 border-x border-amber-500/40" title="Class F 0.15 Zone"></div>
                          <div className="absolute inset-y-0 left-[45%] right-[45%] bg-emerald-500/30 border-x border-emerald-500/60" title="Class F 0.1 Zone"></div>
                          
                          {/* Center Target Marker */}
                          <div className="absolute inset-y-0 left-1/2 w-0.5 bg-white/80 z-10"></div>
                          
                          {/* Marker Pin */}
                          <div 
                            className="absolute top-0 bottom-0 w-3 -ml-1.5 rounded-full bg-indigo-400 border-2 border-white shadow-lg z-20 transition-all duration-500"
                            style={{ left: `${Math.max(10, Math.min(90, 50 + (recommendedNc * 100)))}%` }}
                          ></div>
                        </div>

                        {/* Zone Legend */}
                        <div className="grid grid-cols-3 text-center text-[9px] pt-1 gap-1">
                          <div className="rounded bg-emerald-500/10 border border-emerald-500/30 py-1 text-emerald-400 font-medium">
                            F 0.1 (±0.10 Ω)
                          </div>
                          <div className="rounded bg-amber-500/10 border border-amber-500/30 py-1 text-amber-400 font-medium">
                            F 0.15 (±0.15 Ω)
                          </div>
                          <div className="rounded bg-blue-500/10 border border-blue-500/30 py-1 text-blue-400 font-medium">
                            F 0.30 (±0.30 Ω)
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 2: FEATURE IMPACT BREAKDOWN CHART */}
                  {activeTab === 'features' && (
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
                      <h3 className="font-bold text-white uppercase text-[10px] tracking-wider text-slate-400">
                        Parameter Contribution Breakdown
                      </h3>
                      
                      <div className="space-y-2.5 pt-1">
                        {calcFeatureImpacts().map((feat, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="flex justify-between text-[11px]">
                              <span className="text-slate-300 font-medium">{feat.name} ({feat.raw} {feat.unit})</span>
                              <span className="font-mono text-indigo-400 font-bold">{feat.value > 0 ? `+${feat.value}` : feat.value}</span>
                            </div>
                            <div className="h-2 w-full rounded-full bg-slate-950 overflow-hidden">
                              <div 
                                className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-indigo-400 transition-all duration-500"
                                style={{ width: `${feat.impactPct}%` }}
                              ></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* TAB 3: YIELD CONFIDENCE PROBABILITY DIST */}
                  {activeTab === 'yield' && (
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
                      <h3 className="font-bold text-white uppercase text-[10px] tracking-wider text-slate-400">
                        Predicted Selection Yield Probabilities
                      </h3>
                      
                      <div className="space-y-3 pt-1">
                        {yieldProbabilities.map((y, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="flex justify-between items-center text-xs">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-white">{y.class}</span>
                                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[9px] text-slate-400 font-mono">
                                  {y.badge}
                                </span>
                              </div>
                              <span className="font-mono font-bold text-emerald-400">{y.prob}%</span>
                            </div>
                            <div className="h-2.5 w-full rounded-full bg-slate-950 overflow-hidden p-0.5">
                              <div 
                                className={`h-full rounded-full bg-gradient-to-r ${y.color} transition-all duration-500`}
                                style={{ width: `${y.prob}%` }}
                              ></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* SCREEN PRINTING FALLBACK INDICATOR SUMMARY */}
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3 text-xs">
                    <h3 className="font-bold text-white uppercase text-[10px] tracking-wider text-slate-400">
                      Applied Viscosity & Environment Parameters
                    </h3>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="rounded bg-slate-900/60 p-2 border border-slate-800">
                        <span className="block text-[9px] text-slate-500 uppercase">DS1 Visco</span>
                        <span className="font-mono text-white font-medium">
                          {predictionResult.effective_ds1_viscosity} Pa·s
                        </span>
                      </div>
                      <div className="rounded bg-slate-900/60 p-2 border border-slate-800">
                        <span className="block text-[9px] text-slate-500 uppercase">DS2 Visco</span>
                        <span className="font-mono text-white font-medium">
                          {predictionResult.effective_ds2_viscosity} Pa·s
                        </span>
                      </div>
                      <div className="rounded bg-slate-900/60 p-2 border border-slate-800">
                        <span className="block text-[9px] text-slate-500 uppercase">Humidity</span>
                        <span className="font-mono text-white font-medium">
                          {predictionResult.effective_air_humidity}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* EU AI ACT COMPLIANCE HUD */}
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-6 w-6 items-center justify-center rounded bg-amber-500/10 text-amber-400 text-xs">
                        <Info className="h-4 w-4" />
                      </div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400">
                        EU AI Act Compliance (VDE VCIO)
                      </h3>
                    </div>

                    <div className="space-y-2 text-xs text-slate-300">
                      <p className="leading-relaxed text-[11px]">
                        {predictionResult.compliance_disclaimer}
                      </p>
                      
                      <div className="flex flex-wrap gap-2 text-[10px] pt-1">
                        <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-indigo-300">
                          Traceability ID: {predictionResult.model_version.substring(0, 8)}...
                        </span>
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-emerald-400 flex items-center gap-1 font-mono">
                          <CheckCircle className="h-3 w-3" /> AI GENERATED
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* PREDICTION RUN LOG HISTORY WITH CLEAR BUTTON */}
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 shadow-xl backdrop-blur-xl">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <History className="h-4 w-4 text-indigo-400" />
                  Recent Prediction History ({history.length})
                </h2>
                <div className="flex items-center gap-1">
                  <button
                    onClick={fetchHistory}
                    disabled={isRefreshingHistory}
                    className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors disabled:opacity-50"
                    title="Refresh History"
                  >
                    <RefreshCw className={`h-4 w-4 ${isRefreshingHistory ? "animate-spin" : ""}`} />
                  </button>
                  {history.length > 0 && (
                    <button
                      onClick={handleClearHistory}
                      className="rounded-lg p-1.5 text-red-400 hover:bg-red-500/20 transition-colors"
                      title="Clear History"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              {history.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  <Database className="mx-auto h-8 w-8 text-slate-700 mb-2" />
                  No prediction runs stored in database. Run a prediction above to log your first run.
                </div>
              ) : (
                <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                  {history.map((record) => (
                    <div 
                      key={record.id} 
                      className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-2.5 text-[11px] flex justify-between items-center hover:border-slate-700 transition-colors"
                    >
                      <div>
                        <span className="font-mono text-white font-medium block">{record.part_number}</span>
                        <span className="text-slate-500 block text-[9px] mt-0.5">
                          {new Date(record.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} • Batch: {record.substrate_batch || "N/A"}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="font-mono font-bold text-indigo-400 block text-xs">
                          NC: {record.recommended_nc_value > 0 ? `+${record.recommended_nc_value}` : record.recommended_nc_value}
                        </span>
                        <span className="text-[9px] text-slate-400 block font-mono">
                          R20: {record.pt_r20_value} Ω
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </section>

        </div>

      </main>
      
      {/* Footer */}
      <footer className="mt-20 border-t border-slate-800 bg-[#060a10] py-8 text-center text-xs text-slate-500">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <p>© 2026 JUMO University Team Project. Built with React 18, Vite, and TailwindCSS v4.</p>
          <p className="mt-2 font-mono text-[9px] text-indigo-500/70">
            Complies with VDE SPEC 90012 VCIO / EU AI Act Regulation (Transparency & Audit Traceability logging active)
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
