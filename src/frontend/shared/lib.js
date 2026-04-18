/**
 * Shared library for interacting with the QuranAI API.
 */

const API_BASE_URL = __QURANAI_API_BASE_URL__;
console.info("API URL is: ", API_BASE_URL);

/**
 * Helper for data persistence.
 * Uses chrome.storage.local if available (extension), otherwise falls back to localStorage.
 */
export const storage = {
  async get(key) {
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      return new Promise((resolve) => {
        chrome.storage.local.get([key], (result) => {
          resolve(result[key]);
        });
      });
    }
    const val = localStorage.getItem(key);
    try {
      return JSON.parse(val);
    } catch {
      return val;
    }
  },
  async set(key, value) {
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      return new Promise((resolve) => {
        chrome.storage.local.set({ [key]: value }, resolve);
      });
    }
    localStorage.setItem(key, JSON.stringify(value));
  },
  async remove(key) {
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      return new Promise((resolve) => {
        chrome.storage.local.remove([key], resolve);
      });
    }
    localStorage.removeItem(key);
  }
};

/**
 * Helper to get the current session ID.
 * @returns {Promise<string|null>}
 */
export async function getSessionId() {
  return await storage.get('sessionId');
}

/**
 * Create a new session and store its ID.
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
  // Store the sessionId for 7 days (logic simplified as storage handles expiration if needed).
  await storage.set('sessionId', session.id);
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
