(function () {
  'use strict';

  /**
   * Shared library for interacting with the QuranAI API.
   */

  const API_BASE_URL = 'http://localhost:8000';

  /**
   * Helper to set a cookie.
   * @param {string} name 
   * @param {string} value 
   * @param {number} days 
   */
  function setCookie(name, value, days) {
    let expires = "";
    {
      const date = new Date();
      date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
      expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
  }

  /**
   * Helper to get a cookie value.
   * @param {string} name 
   * @returns {string|null}
   */
  function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
      let c = ca[i];
      while (c.charAt(0) === ' ') c = c.substring(1, c.length);
      if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
  }

  /**
   * Helper to get the current session ID from cookies.
   * @returns {string|null}
   */
  function getSessionId() {
    return getCookie('sessionId');
  }

  /**
   * Create a new session and store its ID in a cookie.
   * @param {string} appName 
   * @param {string} userId 
   * @returns {Promise<Object>} The session object.
   */
  async function createSession(appName, userId) {
    const url = `${API_BASE_URL}/apps/${appName}/users/${userId}/sessions`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}), // Req can be null
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }
    
    const session = await response.json();
    // Store the sessionId in a cookie for 7 days.
    setCookie('sessionId', session.id, 7);
    return session;
  }

  /**
   * Run the agent with a message.
   * @param {string} appName 
   * @param {string} userId 
   * @param {string} sessionId 
   * @param {string} message 
   * @param {boolean} streaming 
   * @returns {Promise<Object>} The agent's response.
   */
  async function runAgent(appName, userId, sessionId, message, streaming = false) {
    const url = `${API_BASE_URL}/run`;
    const requestBody = {
      appName,
      userId,
      sessionId,
      newMessage: {
        parts: [
          {
            text: message
          }
        ]
      },
      streaming
    };
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to run agent: ${response.statusText}`);
    }
    
    return await response.json();
  }

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

})();
//# sourceMappingURL=bundle.js.map
