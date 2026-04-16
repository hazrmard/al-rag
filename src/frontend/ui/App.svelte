<script>
  import { onMount } from 'svelte';
  import { createSession, getSessionId, runAgent, storage } from '../shared/lib.js';
  import Message from './Message.svelte';
  import AboutModal from './AboutModal.svelte';

  const APP_NAME = 'agent';
  const USER_ID = 'extension-user';

  let messages = [];
  let userInput = '';
  let messagesDiv;
  let contextVerses = [];
  let lastMessagesLength = 0;
  let isLoading = false;
  let isAboutModalOpen = false;

  async function addMessage(text, sender, events = []) {
    messages = [...messages, { text, sender, events }];
    await storage.set('messages', messages);
  }

  $: if (messagesDiv && (messages.length > lastMessagesLength || isLoading)) {
    // Only scroll if the user is already near the bottom or if it's a new message they just sent.
    // This prevents the scroll from being "stuck" at the bottom when they try to scroll up.
    const isAtBottom = messagesDiv.scrollTop + messagesDiv.clientHeight >= messagesDiv.scrollHeight - 50;
    const isUserMessage = messages.length > 0 && messages[messages.length - 1].sender === 'user';
    
    if (lastMessagesLength === 0 || isUserMessage || isAtBottom || isLoading) {
      setTimeout(() => {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      }, 0);
    }
    lastMessagesLength = messages.length;
  }

  onMount(async () => {
    // Check if first time user (only for web app)
    if (!__QURANAI_IS_EXTENSION__) {
      const hasVisited = await storage.get('hasVisited');
      if (!hasVisited) {
        isAboutModalOpen = true;
        await storage.set('hasVisited', true);
      }
    }

    // Load persisted state
    const savedMessages = await storage.get('messages');
    if (savedMessages && Array.isArray(savedMessages)) {
      messages = savedMessages;
    } else {
      addMessage('Welcome! Ask me anything about the Quran.', 'agent');
    }

    const savedContext = await storage.get('contextVerses');
    if (savedContext && Array.isArray(savedContext)) {
      contextVerses = savedContext;
    }

    // Connect to background script to signal the side panel is open
    let port;
    if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.connect) {
      port = chrome.runtime.connect({ name: 'quranai-sidepanel' });
    }

    // Listen for messages from the content script
    if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
      chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === 'add_to_context') {
          if (!contextVerses.includes(request.verse)) {
            contextVerses = [...contextVerses, request.verse];
            storage.set('contextVerses', contextVerses);
          }
        } else if (request.action === 'explain_verse') {
          const verse = request.verse;
          userInput = `Explain verse ${verse}`;
          sendMessage();
        }
      });
    }

    return () => {
      if (port) port.disconnect();
    };
  });

  async function ensureSession() {
    let sessionId = await getSessionId();
    if (!sessionId) {
      const session = await createSession(APP_NAME, USER_ID);
      sessionId = session.id;
    }
    return sessionId;
  }

  async function removeFromContext(verse) {
    contextVerses = contextVerses.filter(v => v !== verse);
    await storage.set('contextVerses', contextVerses);
  }

  async function sendMessage() {
    const text = userInput.trim();
    if (!text) return;

    // Prepend context if any
    let fullText = text;
    if (contextVerses.length > 0) {
      fullText = `Context: ${contextVerses.join(', ')}\n\n${text}`;
    }

    userInput = '';
    await addMessage(text, 'user');
    isLoading = true;

    try {
      const sessionId = await ensureSession();
      const result = await runAgent(APP_NAME, USER_ID, sessionId, fullText);
      
      let agentResponse = "No response received.";
      let events = [];
      if (Array.isArray(result)) {
        events = result;
        for (let i = result.length - 1; i >= 0; i--) {
          const event = result[i];
          const textPart = event.content?.parts?.find(p => p.text)?.text;
          if (textPart) {
            agentResponse = textPart;
            break;
          }
        }
      } else if (result.result?.parts?.[0]?.text) {
        agentResponse = result.result.parts[0].text;
        events = [result];
      }
      
      await addMessage(agentResponse, 'agent', events);
    } catch (err) {
      console.error(err);
      await addMessage(`Error: ${err.message}`, 'agent');
    } finally {
      isLoading = false;
    }
  }

  async function startNewChat() {
    messages = [];
    contextVerses = [];
    await storage.remove('messages');
    await storage.remove('contextVerses');
    await storage.remove('sessionId');
    await addMessage('Welcome! Ask me anything about the Quran.', 'agent');
  }

  function handleKeypress(e) {
    if (e.key === 'Enter') {
      sendMessage();
    }
  }

  function toggleAboutModal() {
    isAboutModalOpen = !isAboutModalOpen;
  }
</script>

<style>
  :global(body) {
    height: 100vh;
    font-family: Arial, sans-serif;
    display: flex;
    flex-direction: column;
    margin: 0;
    padding: 10px;
    box-sizing: border-box;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
  }
  .header h3 {
    margin: 0;
  }
  .header-actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .action-btn {
    background: none;
    border: none;
    color: #666;
    font-size: 0.8em;
    cursor: pointer;
    text-decoration: underline;
    padding: 0;
  }
  .messages-container {
    flex: 1;
    overflow-y: auto;
    border: 1px solid #ccc;
    margin-bottom: 10px;
    padding: 5px;
    min-height: 0; /* Ensures container can shrink properly in flexbox for stable scrolling */
  }
  .context-area {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-bottom: 10px;
    padding: 5px;
    border: 1px dashed #ccc;
    min-height: 30px;
  }
  .badge {
    background: #e0e0e0;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .badge button {
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    font-weight: bold;
    color: #666;
  }
  .input-area {
    display: flex;
  }
  input {
    flex: 1;
    padding: 5px;
  }
  .send-btn {
    padding: 5px 10px;
    background-color: #007bff;
    color: white;
    border: none;
    cursor: pointer;
  }
  .send-btn:hover {
    background-color: #0056b3;
  }
  .loading-bubble {
    align-self: flex-start;
    background-color: #e9ecef;
    color: #888;
    padding: 8px 12px;
    border-radius: 15px;
    border-bottom-left-radius: 2px;
    font-size: 0.9em;
    font-style: italic;
    margin-bottom: 10px;
    animation: pulse 1.5s infinite;
  }
  @keyframes pulse {
    0% { opacity: 0.6; }
    50% { opacity: 1; }
    100% { opacity: 0.6; }
  }
</style>

<div class="header">
  <h3>QuranAI Chat</h3>
  <div class="header-actions">
    <button class="action-btn" on:click={toggleAboutModal}>About</button>
    <button class="action-btn" on:click={startNewChat}>New Chat</button>
  </div>
</div>

<div class="messages-container" bind:this={messagesDiv}>
  {#each messages as msg}
    <Message text={msg.text} sender={msg.sender} events={msg.events} />
  {/each}
  {#if isLoading}
    <div class="loading-bubble">Thinking...</div>
  {/if}
</div>

<div class="context-area">
  {#if contextVerses.length === 0}
    <span style="color: #999; font-size: 0.8em;">No verses in context</span>
  {/if}
  {#each contextVerses as verse}
    <div class="badge">
      {verse}
      <button on:click={() => removeFromContext(verse)}>×</button>
    </div>
  {/each}
</div>

<div class="input-area">
  <input
    type="text"
    bind:value={userInput}
    on:keypress={handleKeypress}
    placeholder="Ask a question..."
  />
  <button class="send-btn" on:click={sendMessage}>Send</button>
</div>

{#if isAboutModalOpen}
  <AboutModal on:close={toggleAboutModal} />
{/if}
