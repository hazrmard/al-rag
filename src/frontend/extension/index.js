import { createSession, getSessionId, runAgent } from '../shared/lib.js';

const APP_NAME = 'agent'; 
const USER_ID = 'extension-user'; 

const messagesDiv = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

/**
 * Add a message to the UI.
 * @param {string} text 
 * @param {string} sender 
 */
function addMessage(text, sender) {
  const msgDiv = document.createElement('div');
  msgDiv.classList.add('message', sender);
  msgDiv.textContent = `${sender === 'user' ? 'You' : 'AI'}: ${text}`;
  messagesDiv.appendChild(msgDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

/**
 * Ensure a session exists, creating one if necessary.
 * @returns {Promise<string>}
 */
async function ensureSession() {
  let sessionId = getSessionId();
  if (!sessionId) {
    addMessage('Creating session...', 'agent');
    const session = await createSession(APP_NAME, USER_ID);
    sessionId = session.id;
  }
  return sessionId;
}

/**
 * Send a message and display the agent's response.
 */
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  userInput.value = '';
  addMessage(text, 'user');

  try {
    const sessionId = await ensureSession();
    const result = await runAgent(APP_NAME, USER_ID, sessionId, text);
    console.log('Raw API Response:', result);
    
    // The result is an array of events. 
    // We want to find the final response text.
    let agentResponse = "No response received.";
    if (Array.isArray(result)) {
      // Find the last event that has content with text parts.
      for (let i = result.length - 1; i >= 0; i--) {
        const event = result[i];
        const text = event.content?.parts?.[0]?.text;
        if (text) {
          agentResponse = text;
          break;
        }
      }
    } else if (result.result?.parts?.[0]?.text) {
      agentResponse = result.result.parts[0].text;
    }
    
    addMessage(agentResponse, 'agent');
  } catch (err) {
    console.error(err);
    addMessage(`Error: ${err.message}`, 'agent');
  }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    sendMessage();
  }
});

// Optional: Display an initial welcome message
addMessage('Welcome! Ask me anything about the Quran.', 'agent');
