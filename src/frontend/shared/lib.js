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
export function setCookie(name, value, days) {
  let expires = "";
  if (days) {
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
export function getCookie(name) {
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
export function getSessionId() {
  return getCookie('sessionId');
}

/**
 * Create a new session and store its ID in a cookie.
 * @param {string} appName 
 * @param {string} userId 
 * @returns {Promise<Object>} The session object.
 */
export async function createSession(appName, userId) {
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
export async function runAgent(appName, userId, sessionId, message, streaming = false) {
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
