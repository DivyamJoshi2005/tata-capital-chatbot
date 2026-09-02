import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';


// --- Types ---
interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Session {
  id: string;
  title: string;
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
  
  useEffect(() => {
    fetch('/api/eval-results').then(res => res.json()).then(data => setEvalData(data));
  }, []);


  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load sessions on mount
  useEffect(() => {
    fetchSessions();
  }, []);

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

      const data = await res.json();
      setMessages(data.updated_history);
      if (!currentSessionId || currentSessionId !== data.session_id) {
        setCurrentSessionId(data.session_id);
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

  return (
    <div className="flex h-screen w-full bg-[#1e1e1e] text-white font-sans overflow-hidden">
      
      {/* Sidebar */}
      <div className={`
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} 
        md:translate-x-0 
        absolute md:relative z-20 w-64 h-full bg-[#121212] border-r border-[#333] flex flex-col transition-transform duration-300
      `}>
        <div className="p-4">
          <button 
            onClick={startNewChat}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold transition-all hover:shadow-lg hover:shadow-blue-500/20 active:scale-95"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
            </svg>
            New Chat
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          {sessions.map(s => (
            <div key={s.id} className="relative group flex items-center">
              <button
                onClick={() => loadSession(s.id)}
                className={`flex-1 text-left px-4 py-3 rounded-lg text-sm truncate transition-colors pr-10 ${
                  currentSessionId === s.id ? 'bg-[#2a2a2a] text-blue-400 font-medium' : 'text-gray-400 hover:bg-[#202020] hover:text-gray-200'
                }`}
              >
                {s.title}
              </button>
              <button
                onClick={(e) => deleteSession(s.id, e)}
                className="absolute right-2 p-1.5 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity bg-[#202020] rounded-md"
                title="Delete Chat"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full relative w-full">
        
        {/* Header */}
        <header className="h-16 flex items-center px-6 border-b border-[#333] bg-[#1e1e1e]/80 backdrop-blur-md sticky top-0 z-10 shrink-0">
          <button 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="md:hidden mr-4 p-2 text-gray-400 hover:text-white"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center mr-3 shadow-lg shadow-blue-500/20">
            <span className="text-white font-bold text-sm">T</span>
          </div>
          <h1 className="font-semibold text-lg tracking-wide text-gray-100 flex-1">Tata Capital Advisor</h1>
          
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
              <option value="compare_all">⚖️ Compare All Models Live</option>
            </select>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 scroll-smooth">
          {messages.length === 0 && !isLoading && (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-70">
              <div className="w-20 h-20 mb-6 rounded-3xl bg-[#2a2a2a] flex items-center justify-center border border-[#333]">
                <svg className="w-10 h-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-200 mb-2">How can I assist you?</h2>
              <p className="text-gray-400 max-w-sm">Ask about personal loans, business loans, eligibility, or interest rates.</p>
            </div>
          )}

          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] md:max-w-[75%] px-5 py-3.5 text-[15px] leading-relaxed ${
                msg.role === 'user' 
                  ? 'bg-gradient-to-br from-indigo-600 to-blue-600 text-white rounded-2xl rounded-tr-sm shadow-lg shadow-blue-900/20' 
                  : 'bg-[#262626] text-gray-100 border border-[#333] rounded-2xl rounded-tl-sm shadow-md overflow-x-auto'
              }`}>
                <div className="prose prose-invert prose-sm md:prose-base max-w-none leading-relaxed prose-p:my-2 prose-headings:my-3 prose-li:my-1">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-[#2a2a2a] rounded-2xl rounded-bl-none p-5 border border-[#333] flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 md:p-6 bg-gradient-to-t from-[#1e1e1e] to-transparent shrink-0">
          <div className="max-w-4xl mx-auto relative">
            
            {/* Image Preview Overlay */}
            {imagePreview && (
              <div className="absolute bottom-full mb-3 left-4 right-4 sm:left-auto sm:right-auto sm:w-64 bg-[#2a2a2a] p-2 rounded-xl border border-[#333] shadow-xl flex items-start gap-3 animate-in fade-in slide-in-from-bottom-4">
                <img src={imagePreview} alt="Upload preview" className="w-16 h-16 object-cover rounded-lg border border-[#444]" />
                <div className="flex-1 min-w-0 pt-1">
                  <p className="text-sm font-medium text-gray-200 truncate">{imageFile?.name}</p>
                  <p className="text-xs text-gray-400 mt-1">Image ready to send (OCR)</p>
                </div>
                <button onClick={clearImage} className="text-gray-400 hover:text-white p-1 bg-[#333] rounded-full">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}

            <form 
              onSubmit={handleSubmit}
              className="relative flex items-center bg-[#252525] rounded-2xl border border-[#333] shadow-lg focus-within:border-blue-500/50 focus-within:shadow-blue-500/10 transition-all overflow-hidden"
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
                className="p-3 ml-2 text-gray-400 hover:text-gray-200 hover:bg-[#333] rounded-xl transition-colors"
                title="Attach Image (OCR)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              </button>

              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Message Tata Capital..."
                className="flex-1 bg-transparent text-white px-4 py-4 focus:outline-none placeholder-gray-500"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || (!input.trim() && !imageFile)}
                className="mr-3 p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:bg-[#333] disabled:text-gray-500 text-white transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                  <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
                </svg>
              </button>
            </form>
          </div>
          <div className="text-center mt-3">
            <span className="text-[11px] text-gray-500 font-medium tracking-wide">
              AI CAN MAKE MISTAKES. VERIFY IMPORTANT INFORMATION.
            </span>
          </div>
        </div>
      </div>


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

      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-10 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
    </div>
  );
}
