import { useState, useEffect } from 'react';
import './App.css';

const JsonViewer = ({ data, defaultOpen = false }) => {
    if (typeof data !== 'object' || data === null) {
      // For non-objects, just display the value.
      return <span style={{ color: typeof data === 'string' ? '#ce9178' : '#b5cea8' }}>{JSON.stringify(data)}</span>;
    }
  
    return (
      <details open={defaultOpen} style={{ marginLeft: '1em' }}>
        <summary style={{ cursor: 'pointer', listStyle: 'none' }}>
            {Array.isArray(data) ? `Array(${data.length})` : 'Object'}
        </summary>
        <div style={{ marginLeft: '1em', borderLeft: '1px solid #555', paddingLeft: '1em' }}>
        {Object.entries(data).map(([key, value]) => (
          <div key={key}>
            <strong style={{ color: '#9cdcfe' }}>{key}:</strong>{' '}
            <JsonViewer data={value} />
          </div>
        ))}
        </div>
      </details>
    );
  };


function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [showState, setShowState] = useState(false);
  const [agentState, setAgentState] = useState(null);

  useEffect(() => {
    if (sessionId && showState) {
      const fetchState = async () => {
        try {
          const response = await fetch(`/api/state?session_id=${sessionId}`);
          if (response.ok) {
            const data = await response.json();
            setAgentState(data);
          }
        } catch (error) {
          console.error('Failed to fetch agent state:', error);
        }
      };
      fetchState();
    }
  }, [messages, sessionId, showState]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const newMessages = [...messages, { sender: 'user', text: input }];
    setMessages(newMessages);
    setInput('');

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: input, session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();

      setMessages([...newMessages, { sender: 'bot', text: data.response }]);
      if (!sessionId) {
        setSessionId(data.session_id);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages([...newMessages, { sender: 'bot', text: 'Sorry, something went wrong.' }]);
    }
  };

  return (
    <div className="app-container">
        <div className="chat-container">
            <div className="message-list">
                {messages.map((msg, index) => (
                <div key={index} className={`message ${msg.sender}`}>
                    <p>{msg.text}</p>
                </div>
                ))}
            </div>
            <div className="input-area">
                <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Type a message..."
                />
                <button onClick={handleSendMessage}>Send</button>
            </div>
        </div>
        <div className="diagnostics-container">
            <button onClick={() => setShowState(!showState)}>
                {showState ? 'Hide' : 'Show'} Agent State
            </button>
            {showState && agentState && (
                <div className="state-viewer">
                    <h3>Agent State</h3>
                    <JsonViewer data={agentState} defaultOpen={true} />
                </div>
            )}
        </div>
    </div>
  );
}

export default App;
