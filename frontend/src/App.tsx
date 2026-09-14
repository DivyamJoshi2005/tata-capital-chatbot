import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { 
  MessageSquare, Plus, Trash2, Menu, X, Image as ImageIcon, Send, BarChart3, Bot, User, BrainCircuit, Table, Activity, Zap, LineChart as LineChartIcon
} from 'lucide-react';

// --- Types ---
interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Session {
  id: string;
  title: string;
}

interface LiveMetric {
  queryIndex: number;
  model: string;
  latency_seconds: number;
  tokens_generated: number;
  tokens_per_second: number;
  memory_used_mb: number;
}

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
    semantic_score: number;
    correctness_accuracy: number;
    hallucination_rate: number;
    rag_uplift: number;
  }
}

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const [selectedModel, setSelectedModel] = useState('deepseek-r1:1.5b');
  const [showEval, setShowEval] = useState(false);
  const [evalData, setEvalData] = useState<EvalResult[]>([]);
  const [evalTab, setEvalTab] = useState<'charts' | 'table' | 'live'>('charts');
  const [liveMetrics, setLiveMetrics] = useState<LiveMetric[]>([]);
  
  useEffect(() => {
    const fetchEvalData = () => {
      fetch('/api/eval-results')
        .then(res => res.json())
        .then(data => setEvalData(data))
        .catch(err => console.error("Failed to fetch eval data", err));
    };

    // Initial fetch
    fetchEvalData();

    // Poll for live updates every 5 seconds
    const intervalId = setInterval(fetchEvalData, 5000);
    
    // Cleanup interval on unmount
    return () => clearInterval(intervalId);
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchSessions = async () => {
    try {
      const res = await fetch('/api/sessions');
      const data = await res.json();
      setSessions(data);
      if (data.length > 0 && !currentSessionId) {
        loadSession(data[0].id);
      } else if (data.length === 0) {
        startNewChat();
      }
    } catch (error) {
      console.error("Failed to fetch sessions", error);
    }
  };

  const loadSession = async (id: string) => {
    setCurrentSessionId(id);
    setIsLoading(true);
    try {
      const res = await fetch(`/api/sessions/${id}/history`);
      const data = await res.json();
      setMessages(data);
    } catch (error) {
      console.error("Failed to load history", error);
    } finally {
      setIsLoading(false);
    }
    // Close sidebar on mobile
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const startNewChat = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/sessions', { method: 'POST' });
      const data = await res.json();
      setCurrentSessionId(data.id);
      setMessages([]);
      fetchSessions();
    } catch (error) {
      console.error("Failed to start chat", error);
    } finally {
      setIsLoading(false);
    }
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  const deleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this chat?')) return;
    
    try {
      await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
      const newSessions = sessions.filter(s => s.id !== id);
      setSessions(newSessions);
      
      if (currentSessionId === id) {
        if (newSessions.length > 0) {
          loadSession(newSessions[0].id);
        } else {
          startNewChat();
        }
      }
    } catch (error) {
      console.error("Failed to delete chat", error);
    }
  };

  // Load sessions on mount
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const clearImage = () => {
    setImageFile(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const getBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() && !imageFile) return;

    let base64Image = null;
    if (imageFile) {
      base64Image = await getBase64(imageFile);
    }

    const newMessage: Message = { role: 'user', content: input || '[Image Attached]' };
    setMessages(prev => [...prev, newMessage]);
    setInput('');
    setIsLoading(true);
    clearImage(); // Clear preview immediately

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          image_base64: base64Image,
          session_id: currentSessionId,
          model_name: selectedModel
        }),
      });

      if (!res.ok) throw new Error('API Error');

      const returnedSessionId = res.headers.get("X-Session-Id");
      if (returnedSessionId && (!currentSessionId || currentSessionId !== returnedSessionId)) {
        setCurrentSessionId(returnedSessionId);
      }

      if (res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        
        // Add an empty assistant message that we will stream into
        setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
        setIsLoading(false);

        let assistantMessage = "";
        let finalMemory = 0;
        const startTime = Date.now();
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          assistantMessage += chunk;
          
          if (assistantMessage.includes('__METRICS__')) {
            const parts = assistantMessage.split('__METRICS__');
            assistantMessage = parts[0];
            try {
               const parsed = JSON.parse(parts[1]);
               finalMemory = parsed.memory_used_mb;
            } catch {
               // ignore parsing errors
            }
          }
          
          setMessages(prev => {
            const newMsgs = [...prev];
            newMsgs[newMsgs.length - 1].content = assistantMessage;
            return newMsgs;
          });
        }
        
        // Compute live metrics
        const endTime = Date.now();
        const latencySeconds = Number(((endTime - startTime) / 1000).toFixed(2));
        const words = assistantMessage.split(/\s+/).length;
        const estimatedTokens = Math.round(words * 1.3);
        const tps = Number((estimatedTokens / (latencySeconds || 1)).toFixed(2));
        
        setLiveMetrics(prev => [...prev, {
          queryIndex: prev.length + 1,
          model: selectedModel,
          latency_seconds: latencySeconds,
          tokens_generated: estimatedTokens,
          tokens_per_second: tps,
          memory_used_mb: finalMemory
        }]);
      }
      
      fetchSessions(); // Refresh sidebar titles
    } catch (error) {
      console.error(error);
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: '🚨 An error occurred. Please try again.' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Compute Chart Data ---
  const chartData = ['deepseek-r1:1.5b', 'llama3.2:3b', 'qwen2.5:3b'].map(m => {
    const items = evalData.filter(d => d.model === m);
    if (items.length === 0) return null;
    return {
      name: m,
      latency: Number((items.reduce((a, b) => a + b.metrics.latency_seconds, 0) / items.length).toFixed(2)),
      tps: Number((items.reduce((a, b) => a + b.metrics.tokens_per_second, 0) / items.length).toFixed(2)),
      memory: Number((items.reduce((a, b) => a + b.metrics.memory_used_mb, 0) / items.length).toFixed(0)),
      semantic: Number((items.reduce((a, b) => a + (b.metrics.semantic_score || 0), 0) / items.length).toFixed(2)),
      accuracy: Number((items.reduce((a, b) => a + (b.metrics.correctness_accuracy || 0), 0) / items.length).toFixed(2)),
      hallucination: Number((items.reduce((a, b) => a + (b.metrics.hallucination_rate || 0), 0) / items.length).toFixed(2)),
      rag_uplift: Number((items.reduce((a, b) => a + (b.metrics.rag_uplift || 0), 0) / items.length).toFixed(2)),
      semantic_scaled: Number(((items.reduce((a, b) => a + (b.metrics.semantic_score || 0), 0) / items.length) / 10).toFixed(2)),
    };
  }).filter((item): item is NonNullable<typeof item> => Boolean(item));

  return (
    <div className="flex h-screen w-full bg-[#0a0a0a] text-gray-100 font-sans overflow-hidden selection:bg-indigo-500/30">
      
      {/* Sidebar */}
      <div className={`
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} 
        md:translate-x-0 
        absolute md:relative z-20 w-72 h-full bg-[#111111] border-r border-white/5 flex flex-col transition-transform duration-300 shadow-2xl md:shadow-none
      `}>
        <div className="p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
             <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
               <BrainCircuit className="w-5 h-5 text-white" />
             </div>
             <h1 className="font-bold text-lg tracking-tight bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">Tata Advisor</h1>
          </div>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="px-4 pb-4">
          <button 
            onClick={startNewChat}
            className="w-full flex items-center gap-3 py-3 px-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 text-sm font-medium transition-all active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            New Conversation
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-3 space-y-1">
          <div className="px-3 pb-2 pt-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Recent Chats</div>
          {sessions.map(s => (
            <div key={s.id} className="relative group flex items-center">
              <button
                onClick={() => loadSession(s.id)}
                className={`flex-1 flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm truncate transition-all ${
                  currentSessionId === s.id ? 'bg-indigo-500/10 text-indigo-400 font-medium' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                }`}
              >
                <MessageSquare className="w-4 h-4 shrink-0" />
                <span className="truncate">{s.title}</span>
              </button>
              <button
                onClick={(e) => deleteSession(s.id, e)}
                className="absolute right-2 p-1.5 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity bg-[#111] rounded-md"
                title="Delete Chat"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full relative w-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-900/10 via-[#0a0a0a] to-[#0a0a0a]">
        
        {/* Header */}
        <header className="h-16 flex items-center px-4 md:px-8 border-b border-white/5 bg-black/20 backdrop-blur-xl sticky top-0 z-10 shrink-0">
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className={`md:hidden mr-4 p-2 -ml-2 text-gray-400 hover:text-white transition-opacity ${isSidebarOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
          >
            <Menu className="w-5 h-5" />
          </button>
          
          <div className="flex-1" />
          
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setShowEval(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 rounded-lg text-sm font-medium transition-colors"
            >
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">Performance</span>
            </button>
            <select 
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-[#111] border border-white/10 hover:border-white/20 text-gray-200 text-sm rounded-lg focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 block p-1.5 outline-none transition-colors cursor-pointer"
            >
              <option value="deepseek-r1:1.5b">DeepSeek R1 (1.5B)</option>
              <option value="llama3.2:3b">Llama 3.2 (3B)</option>
              <option value="qwen2.5:3b">Qwen 2.5 (3B)</option>
              <option value="compare_all">⚖️ Compare Live</option>
            </select>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth">
          <div className="max-w-4xl mx-auto space-y-8">
            {messages.length === 0 && !isLoading && (
              <div className="h-full mt-20 flex flex-col items-center justify-center text-center">
                <div className="w-20 h-20 mb-8 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 shadow-2xl">
                  <BrainCircuit className="w-10 h-10 text-indigo-400" />
                </div>
                <h2 className="text-3xl font-bold text-gray-100 mb-3 tracking-tight">How can I help you today?</h2>
                <p className="text-gray-400 max-w-md text-lg">Ask about Tata Capital personal loans, business loans, eligibility, or current interest rates.</p>
              </div>
            )}

            {messages.map((msg, index) => (
              <div key={index} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0 mt-1 shadow-lg shadow-indigo-500/20">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                )}
                
                <div className={`max-w-[85%] md:max-w-[75%] px-5 py-4 text-[15px] leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-indigo-600 text-white rounded-2xl rounded-tr-sm shadow-xl shadow-indigo-900/20' 
                    : 'bg-[#1a1a1a] text-gray-200 border border-white/5 rounded-2xl rounded-tl-sm shadow-xl overflow-x-auto'
                }`}>
                  <div className="prose prose-invert prose-sm md:prose-base max-w-none leading-relaxed prose-p:my-2 prose-headings:my-3 prose-li:my-1 prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10 prose-pre:rounded-xl">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center shrink-0 mt-1 border border-white/10">
                    <User className="w-5 h-5 text-gray-400" />
                  </div>
                )}
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start gap-4">
                <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0 mt-1 shadow-lg shadow-indigo-500/20">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div className="bg-[#1a1a1a] rounded-2xl rounded-tl-sm p-5 border border-white/5 flex items-center gap-2 h-[52px]">
                  <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>

        {/* Input Area */}
        <div className="p-4 md:p-6 bg-gradient-to-t from-[#0a0a0a] via-[#0a0a0a] to-transparent shrink-0">
          <div className="max-w-4xl mx-auto relative">
            
            {/* Image Preview Overlay */}
            {imagePreview && (
              <div className="absolute bottom-full mb-4 left-0 sm:w-72 bg-[#1a1a1a] p-3 rounded-2xl border border-white/10 shadow-2xl flex items-start gap-3">
                <img src={imagePreview} alt="Upload preview" className="w-16 h-16 object-cover rounded-xl border border-white/10" />
                <div className="flex-1 min-w-0 pt-1">
                  <p className="text-sm font-medium text-gray-200 truncate">{imageFile?.name}</p>
                  <p className="text-xs text-gray-500 mt-1">Image ready to send (OCR)</p>
                </div>
                <button onClick={clearImage} className="text-gray-400 hover:text-white p-1.5 hover:bg-white/10 rounded-full transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            <form 
              onSubmit={handleSubmit}
              className="relative flex items-center bg-[#151515] rounded-2xl border border-white/10 shadow-xl focus-within:border-indigo-500/50 focus-within:shadow-indigo-500/10 transition-all overflow-hidden"
            >
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleImageUpload} 
                accept="image/*" 
                className="hidden" 
              />
              <button 
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-3 ml-2 text-gray-400 hover:text-gray-200 hover:bg-white/5 rounded-xl transition-colors"
                title="Attach Image (OCR)"
              >
                <ImageIcon className="w-5 h-5" />
              </button>

              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask Tata Advisor..."
                className="flex-1 bg-transparent text-white px-3 py-4 focus:outline-none placeholder-gray-500 text-[15px]"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || (!input.trim() && !imageFile)}
                className="mr-2 p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:bg-white/5 disabled:text-gray-500 text-white transition-all active:scale-95"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
          <div className="text-center mt-4">
            <span className="text-[11px] text-gray-500 font-medium tracking-widest uppercase">
              AI can make mistakes. Verify important information.
            </span>
          </div>
        </div>
      </div>

      {/* Eval Modal */}
      {showEval && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 md:p-8">
          <div className="bg-[#111] border border-white/10 rounded-2xl shadow-2xl w-full max-w-6xl max-h-full flex flex-col overflow-hidden">
            <div className="p-6 border-b border-white/10 flex justify-between items-center bg-[#151515]">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-indigo-400" />
                  Model Performance Dashboard
                </h2>
                <p className="text-sm text-gray-400 mt-1">Comparing DeepSeek, Llama, and Qwen</p>
              </div>
              <button onClick={() => setShowEval(false)} className="text-gray-400 hover:text-white p-2 hover:bg-white/10 rounded-full transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/10 bg-[#151515] px-6">
              <button 
                onClick={() => setEvalTab('charts')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${evalTab === 'charts' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
              >
                <BarChart3 className="w-4 h-4" />
                Performance Chart
              </button>
              <button 
                onClick={() => setEvalTab('live')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${evalTab === 'live' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
              >
                <LineChartIcon className="w-4 h-4" />
                Live Session Chart
              </button>
              <button 
                onClick={() => setEvalTab('table')}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${evalTab === 'table' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
              >
                <Table className="w-4 h-4" />
                Data Table
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1 bg-[#0a0a0a]">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                {['deepseek-r1:1.5b', 'llama3.2:3b', 'qwen2.5:3b'].map(m => {
                  const items = evalData.filter(d => d.model === m);
                  if (items.length === 0) return null;
                  const avgLat = (items.reduce((a, b) => a + b.metrics.latency_seconds, 0) / items.length).toFixed(2);
                  const avgTps = (items.reduce((a, b) => a + b.metrics.tokens_per_second, 0) / items.length).toFixed(2);
                  const avgAcc = (items.reduce((a, b) => a + (b.metrics.correctness_accuracy||0), 0) / items.length * 100).toFixed(0);
                  const avgUplift = (items.reduce((a, b) => a + (b.metrics.rag_uplift||0), 0) / items.length * 100).toFixed(0);
                  return (
                    <div key={m} className="bg-[#151515] p-5 rounded-xl border border-white/5 shadow-sm relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-4 opacity-5">
                         <Zap className="w-16 h-16" />
                      </div>
                      <h3 className="font-bold text-gray-200 mb-4">{m}</h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-xs text-gray-500 uppercase font-semibold">Latency</div>
                          <div className="text-lg text-white font-mono">{avgLat}s</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 uppercase font-semibold">Speed</div>
                          <div className="text-lg text-white font-mono">{avgTps} t/s</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 uppercase font-semibold">Accuracy</div>
                          <div className="text-lg text-emerald-400 font-mono">{avgAcc}%</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 uppercase font-semibold">RAG Uplift</div>
                          <div className="text-lg text-cyan-400 font-mono">+{avgUplift}%</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {evalTab === 'charts' && chartData.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Quality Metrics Chart */}
                  <div className="bg-[#151515] p-5 rounded-xl border border-white/5 h-80 flex flex-col">
                    <h3 className="font-semibold text-gray-200 mb-4 text-sm text-center">Quality Score (Higher is Better)</h3>
                    <div className="flex-1">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                          <XAxis dataKey="name" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                          <YAxis stroke="#666" fontSize={11} domain={[0, 1]} tickLine={false} axisLine={false} />
                          <RechartsTooltip cursor={{fill: '#222'}} contentStyle={{backgroundColor: '#111', borderColor: '#333', borderRadius: '8px', color: '#fff'}} />
                          <Legend wrapperStyle={{fontSize: '12px', paddingTop: '10px'}} />
                          <Bar dataKey="accuracy" fill="#10b981" radius={[4, 4, 0, 0]} name="Accuracy" />
                          <Bar dataKey="semantic_scaled" fill="#6366f1" radius={[4, 4, 0, 0]} name="Semantic Score (/10)" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Hallucination Rate Chart */}
                  <div className="bg-[#151515] p-5 rounded-xl border border-white/5 h-80 flex flex-col">
                    <h3 className="font-semibold text-gray-200 mb-4 text-sm text-center">Hallucination Rate (Lower is Better)</h3>
                    <div className="flex-1">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                          <XAxis dataKey="name" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                          <YAxis stroke="#666" fontSize={11} domain={[0, 1]} tickLine={false} axisLine={false} />
                          <RechartsTooltip cursor={{fill: '#222'}} contentStyle={{backgroundColor: '#111', borderColor: '#333', borderRadius: '8px', color: '#fff'}} />
                          <Legend wrapperStyle={{fontSize: '12px', paddingTop: '10px'}} />
                          <Bar dataKey="hallucination" fill="#ef4444" radius={[4, 4, 0, 0]} name="Hallucination Rate" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Latency & Throughput Chart */}
                  <div className="bg-[#151515] p-5 rounded-xl border border-white/5 h-80 flex flex-col">
                    <h3 className="font-semibold text-gray-200 mb-4 text-sm text-center">Inference Speed (Tokens/sec)</h3>
                    <div className="flex-1">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                          <XAxis dataKey="name" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                          <YAxis stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                          <RechartsTooltip cursor={{fill: '#222'}} contentStyle={{backgroundColor: '#111', borderColor: '#333', borderRadius: '8px', color: '#fff'}} />
                          <Legend wrapperStyle={{fontSize: '12px', paddingTop: '10px'}} />
                          <Bar dataKey="tps" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Tokens/sec" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Resource Usage Chart */}
                  <div className="bg-[#151515] p-5 rounded-xl border border-white/5 h-80 flex flex-col">
                    <h3 className="font-semibold text-gray-200 mb-4 text-sm text-center">Resource Usage</h3>
                    <div className="flex-1">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                          <XAxis dataKey="name" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                          <YAxis yAxisId="left" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                          <YAxis yAxisId="right" orientation="right" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                          <RechartsTooltip cursor={{fill: '#222'}} contentStyle={{backgroundColor: '#111', borderColor: '#333', borderRadius: '8px', color: '#fff'}} />
                          <Legend wrapperStyle={{fontSize: '12px', paddingTop: '10px'}} />
                          <Bar yAxisId="left" dataKey="latency" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Avg Latency (s)" />
                          <Bar yAxisId="right" dataKey="memory" fill="#ec4899" radius={[4, 4, 0, 0]} name="Memory (MB)" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              )}

              {evalTab === 'live' && (
                <div className="animate-in fade-in space-y-6">
                  {liveMetrics.length === 0 ? (
                    <div className="text-center text-gray-500 py-20 bg-[#151515] rounded-xl border border-white/5">
                      <LineChartIcon className="w-12 h-12 mx-auto mb-4 opacity-20" />
                      <p className="text-lg">No live metrics yet!</p>
                      <p className="text-sm mt-2">Ask a query in the chat to see real-time inference metrics recorded here.</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div className="bg-[#151515] p-5 rounded-xl border border-white/5 h-80 flex flex-col">
                        <h3 className="font-semibold text-gray-200 mb-4 text-sm text-center">Latency per Query (s)</h3>
                        <div className="flex-1">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={liveMetrics} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                              <XAxis dataKey="queryIndex" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                              <YAxis stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                              <RechartsTooltip cursor={{stroke: '#444'}} contentStyle={{backgroundColor: '#111', borderColor: '#333', borderRadius: '8px', color: '#fff'}} />
                              <Legend wrapperStyle={{fontSize: '12px', paddingTop: '10px'}} />
                              <Line type="monotone" dataKey="latency_seconds" stroke="#f59e0b" strokeWidth={3} dot={{r: 4, fill: '#f59e0b', strokeWidth: 0}} name="Latency" />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      <div className="bg-[#151515] p-5 rounded-xl border border-white/5 h-80 flex flex-col">
                        <h3 className="font-semibold text-gray-200 mb-4 text-sm text-center">Tokens per Second</h3>
                        <div className="flex-1">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={liveMetrics} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                              <XAxis dataKey="queryIndex" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                              <YAxis stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                              <RechartsTooltip cursor={{stroke: '#444'}} contentStyle={{backgroundColor: '#111', borderColor: '#333', borderRadius: '8px', color: '#fff'}} />
                              <Legend wrapperStyle={{fontSize: '12px', paddingTop: '10px'}} />
                              <Line type="monotone" dataKey="tokens_per_second" stroke="#3b82f6" strokeWidth={3} dot={{r: 4, fill: '#3b82f6', strokeWidth: 0}} name="Tokens/sec" />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      <div className="bg-[#151515] p-5 rounded-xl border border-white/5 h-80 flex flex-col">
                        <h3 className="font-semibold text-gray-200 mb-4 text-sm text-center">Memory Usage (MB)</h3>
                        <div className="flex-1">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={liveMetrics} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                              <XAxis dataKey="queryIndex" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                              <YAxis stroke="#666" fontSize={11} domain={['auto', 'auto']} tickLine={false} axisLine={false} />
                              <RechartsTooltip cursor={{stroke: '#444'}} contentStyle={{backgroundColor: '#111', borderColor: '#333', borderRadius: '8px', color: '#fff'}} />
                              <Legend wrapperStyle={{fontSize: '12px', paddingTop: '10px'}} />
                              <Line type="monotone" dataKey="memory_used_mb" stroke="#ec4899" strokeWidth={3} dot={{r: 4, fill: '#ec4899', strokeWidth: 0}} name="Memory (MB)" />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      <div className="bg-[#151515] p-5 rounded-xl border border-white/5 h-80 flex flex-col">
                        <h3 className="font-semibold text-gray-200 mb-4 text-sm text-center">Tokens Generated</h3>
                        <div className="flex-1">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={liveMetrics} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                              <XAxis dataKey="queryIndex" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                              <YAxis stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
                              <RechartsTooltip cursor={{stroke: '#444'}} contentStyle={{backgroundColor: '#111', borderColor: '#333', borderRadius: '8px', color: '#fff'}} />
                              <Legend wrapperStyle={{fontSize: '12px', paddingTop: '10px'}} />
                              <Line type="monotone" dataKey="tokens_generated" stroke="#10b981" strokeWidth={3} dot={{r: 4, fill: '#10b981', strokeWidth: 0}} name="Tokens" />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {evalTab === 'table' && (
                <div className="overflow-x-auto bg-[#151515] rounded-xl border border-white/5 animate-in fade-in">
                  <table className="w-full text-sm text-left text-gray-300">
                    <thead className="text-xs text-gray-400 uppercase bg-black/40 border-b border-white/5">
                      <tr>
                        <th className="px-6 py-4 font-semibold tracking-wider">Model</th>
                        <th className="px-6 py-4 font-semibold tracking-wider text-right">Avg Latency</th>
                        <th className="px-6 py-4 font-semibold tracking-wider text-right">Avg Speed</th>
                        <th className="px-6 py-4 font-semibold tracking-wider text-right">Accuracy</th>
                        <th className="px-6 py-4 font-semibold tracking-wider text-right">Semantic</th>
                        <th className="px-6 py-4 font-semibold tracking-wider text-right">Hallucination</th>
                        <th className="px-6 py-4 font-semibold tracking-wider text-right">RAG Uplift</th>
                        <th className="px-6 py-4 font-semibold tracking-wider text-right">Memory</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {chartData.map((d, i) => (
                        <tr key={i} className="hover:bg-white/5 transition-colors">
                          <td className="px-6 py-4 font-medium text-white">{d.name}</td>
                          <td className="px-6 py-4 text-right font-mono text-amber-400">{d.latency}s</td>
                          <td className="px-6 py-4 text-right font-mono text-blue-400">{d.tps} t/s</td>
                          <td className="px-6 py-4 text-right font-mono text-emerald-400">{d.accuracy}</td>
                          <td className="px-6 py-4 text-right font-mono text-indigo-400">{d.semantic * 10}</td>
                          <td className="px-6 py-4 text-right font-mono text-red-400">{d.hallucination}</td>
                          <td className="px-6 py-4 text-right font-mono text-cyan-400">+{Math.round(d.rag_uplift * 100)}%</td>
                          <td className="px-6 py-4 text-right font-mono text-pink-400">{d.memory} MB</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-10 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
    </div>
  );
}
