import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import { v4 as uuidv4 } from 'uuid';

const API_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

function App() {
  const [sessionId, setSessionId] = useState(uuidv4());
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/auth/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        setError(null);
      } else {
        setError("Failed to fetch integration status.");
      }
    } catch (e) {
      setError(`API server not running at ${API_URL}`);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000); // Poll status
    return () => clearInterval(interval);
  }, []);

  const handleClearChat = async () => {
    setMessages([]);
    try {
      await fetch(`${API_URL}/chat/history/${sessionId}`, { method: 'DELETE' });
    } catch(e) {}
  };

  const handleNewSession = () => {
    setMessages([]);
    setSessionId(uuidv4());
  };

  return (
    <div className="app-container">
      <Sidebar 
        status={status} 
        onClearChat={handleClearChat}
        onNewSession={handleNewSession}
        apiUrl={API_URL}
      />
      <Chat 
        messages={messages} 
        setMessages={setMessages} 
        sessionId={sessionId} 
        apiUrl={API_URL}
      />
      {error && (
        <div style={{position: 'absolute', bottom: 20, right: 20, background: '#EF4444', color: '#fff', padding: '12px 20px', borderRadius: '8px', zIndex: 100}}>
          {error}
        </div>
      )}
    </div>
  );
}

export default App;
