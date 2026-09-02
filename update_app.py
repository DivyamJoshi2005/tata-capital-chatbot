import re

with open('frontend/src/App.tsx', 'r') as f:
    content = f.read()

# 1. Add types for EvalResult
types_insert = """
interface EvalResult {
  model: string;
  question_id: number;
  question: string;
  category: string;
  metrics: {
    latency_seconds: number;
    tokens_generated: number;
    tokens_per_second: number;
    memory_used_mb: number;
  }
}
"""
content = content.replace("export default function App() {", types_insert + "\nexport default function App() {")

# 2. Add State
state_insert = """
  const [selectedModel, setSelectedModel] = useState('deepseek-r1:1.5b');
  const [showEval, setShowEval] = useState(false);
  const [evalData, setEvalData] = useState<EvalResult[]>([]);
  
  useEffect(() => {
    fetch('/api/eval-results').then(res => res.json()).then(data => setEvalData(data));
  }, []);
"""
content = content.replace("const [isSidebarOpen, setIsSidebarOpen] = useState(true);", "const [isSidebarOpen, setIsSidebarOpen] = useState(true);\n" + state_insert)

# 3. Add model_name to API call
content = content.replace(
    "session_id: currentSessionId",
    "session_id: currentSessionId,\n          model_name: selectedModel"
)

# 4. Add Model Selector and Compare button in Header
header_old = """<h1 className="font-semibold text-lg tracking-wide text-gray-100">Tata Capital Advisor</h1>
        </header>"""

header_new = """<h1 className="font-semibold text-lg tracking-wide text-gray-100 flex-1">Tata Capital Advisor</h1>
          
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setShowEval(true)}
              className="px-3 py-1.5 bg-[#2a2a2a] hover:bg-[#333] border border-[#444] rounded-lg text-sm text-blue-400 font-medium transition-colors hidden md:block"
            >
              📊 Compare Models
            </button>
            <select 
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-[#2a2a2a] border border-[#444] text-gray-200 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-1.5 outline-none"
            >
              <option value="deepseek-r1:1.5b">DeepSeek R1 (1.5B)</option>
              <option value="llama3.2:3b">Llama 3.2 (3B)</option>
              <option value="qwen2.5:3b">Qwen 2.5 (3B)</option>
            </select>
          </div>
        </header>"""
content = content.replace(header_old, header_new)


# 5. Add Compare Modal Overlay
modal_ui = """
      {/* Eval Modal */}
      {showEval && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-[#1e1e1e] border border-[#333] rounded-2xl shadow-2xl w-full max-w-4xl max-h-[80vh] flex flex-col">
            <div className="p-5 border-b border-[#333] flex justify-between items-center">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                📊 Model Evaluation Dashboard
              </h2>
              <button onClick={() => setShowEval(false)} className="text-gray-400 hover:text-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>
            <div className="p-6 overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {['deepseek-r1:1.5b', 'llama3.2:3b', 'qwen2.5:3b'].map(m => {
                  const items = evalData.filter(d => d.model === m);
                  if (items.length === 0) return null;
                  const avgLat = (items.reduce((a, b) => a + b.metrics.latency_seconds, 0) / items.length).toFixed(1);
                  const avgTps = (items.reduce((a, b) => a + b.metrics.tokens_per_second, 0) / items.length).toFixed(1);
                  return (
                    <div key={m} className="bg-[#2a2a2a] p-4 rounded-xl border border-[#444]">
                      <h3 className="font-semibold text-blue-400 mb-2">{m}</h3>
                      <div className="text-sm text-gray-300">Avg Latency: <span className="text-white font-mono">{avgLat}s</span></div>
                      <div className="text-sm text-gray-300">Generation Speed: <span className="text-white font-mono">{avgTps} t/s</span></div>
                    </div>
                  );
                })}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left text-gray-300">
                  <thead className="text-xs text-gray-400 uppercase bg-[#252525]">
                    <tr>
                      <th className="px-4 py-3">Model</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Avg Latency</th>
                      <th className="px-4 py-3">Avg Speed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {['deepseek-r1:1.5b', 'llama3.2:3b', 'qwen2.5:3b'].map(m => {
                      const items = evalData.filter(d => d.model === m);
                      if (items.length === 0) return null;
                      return (
                        <tr key={m} className="border-b border-[#333] hover:bg-[#2a2a2a]">
                          <td className="px-4 py-3 font-medium text-white">{m}</td>
                          <td className="px-4 py-3">All Categories</td>
                          <td className="px-4 py-3">{(items.reduce((a, b) => a + b.metrics.latency_seconds, 0) / items.length).toFixed(2)}s</td>
                          <td className="px-4 py-3">{(items.reduce((a, b) => a + b.metrics.tokens_per_second, 0) / items.length).toFixed(2)} tok/s</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
"""

content = content.replace("      {/* Mobile Sidebar Overlay */}", modal_ui + "\n      {/* Mobile Sidebar Overlay */}")

with open('frontend/src/App.tsx', 'w') as f:
    f.write(content)
