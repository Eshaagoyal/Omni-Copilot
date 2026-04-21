import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Bot, User, LayoutGrid } from 'lucide-react';

const Chat = ({ messages, setMessages, sessionId, apiUrl }) => {
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const endOfMessagesRef = useRef(null);

  const scrollToBottom = () => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim()) return;

    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    const activeMsgId = Date.now();
    setMessages(prev => [...prev, { id: activeMsgId, role: 'assistant', content: '' }]);

    try {
      const response = await fetch(`${apiUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, session_id: sessionId, use_history: true })
      });

      if (!response.ok) throw new Error("Failed to connect");
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let fullContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data === '[DONE]') break;
            if (!data) continue;
            
            try {
              const parsed = JSON.parse(data);
              const chunkStr = parsed.chunk;
              
              if (typeof chunkStr === 'string' && chunkStr.startsWith('__AUDIT__')) {
                const toolName = chunkStr.replace(/__AUDIT__/g, '');
                
                setMessages(prev => prev.map(msg => 
                  msg.id === activeMsgId 
                    ? { ...msg, 
                        auditLogs: [...(msg.auditLogs || []), `⚙️ Executing Action: ${toolName}`]
                      } 
                    : msg
                ));
                continue;
              }
              
              fullContent += chunkStr;
              
              setMessages(prev => prev.map(msg => 
                msg.id === activeMsgId ? { ...msg, content: fullContent } : msg
              ));
            } catch (e) {
               // ignore invalid json from partial chunks if any (though SSE should frame it per line)
            }
          }
        }
      }
    } catch (err) {
      setMessages(prev => prev.map(msg => 
        msg.id === activeMsgId ? { ...msg, content: `⚠️ Error: ${err.message}` } : msg
      ));
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="main-chat">
      <div className="chat-header">
        <div style={{display: 'flex', alignItems: 'center', gap: '12px'}}>
          <LayoutGrid size={20} color="var(--accent-color)" />
          <h2 style={{fontSize: '18px', fontWeight: 500}}>Omni Dashboard</h2>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{textAlign: 'center', color: 'var(--text-secondary)', marginTop: 'auto', marginBottom: 'auto'}}>
            <Bot size={48} style={{opacity: 0.2, margin: '0 auto 16px auto'}} />
            <p>Connect your tools in the sidebar, then ask me anything.</p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="avatar">
              {msg.role === 'user' ? <User size={20} /> : <Bot size={20} color="#fff" />}
            </div>
            <div className="message-content">
              {msg.auditLogs && msg.auditLogs.length > 0 && (
                <div style={{
                  background: 'rgba(0,0,0,0.5)', 
                  padding: '8px 12px', 
                  borderRadius: '6px', 
                  marginBottom: '12px',
                  borderLeft: '3px solid var(--accent-color)',
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  color: 'var(--text-secondary)'
                }}>
                  {msg.auditLogs.map((log, i) => (
                    <div key={i} style={{marginBottom: '4px'}}>{log}</div>
                  ))}
                </div>
              )}
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="message assistant">
             <div className="avatar">
                <Bot size={20} color="#fff" />
             </div>
             <div className="message-content" style={{display: 'flex', alignItems: 'center'}}>
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
             </div>
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      <div className="chat-input-container">
        <form className="chat-input-wrapper" onSubmit={handleSend}>
          <input 
            type="text" 
            className="chat-input" 
            placeholder="Ask about your emails, files, schedule, or send a Slack/Discord message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isTyping}
          />
          <button type="submit" className="send-button" disabled={isTyping || !input.trim()}>
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chat;
