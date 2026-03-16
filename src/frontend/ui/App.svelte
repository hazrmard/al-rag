<script>
  import { onMount } from 'svelte';
  import { createSession, getSessionId, runAgent } from '../shared/lib.js';
  import Message from './Message.svelte';

  const APP_NAME = 'agent';
  const USER_ID = 'extension-user';

  let messages = [];
  let userInput = '';
  let messagesDiv;
  let contextVerses = [];
  let lastMessagesLength = 0;

  function addMessage(text, sender) {
    messages = [...messages, { text, sender }];
  }

  $: if (messagesDiv && messages.length > lastMessagesLength) {
    // Only scroll if the user is already near the bottom or if it's a new message they just sent.
    // This prevents the scroll from being "stuck" at the bottom when they try to scroll up.
    const isAtBottom = messagesDiv.scrollTop + messagesDiv.clientHeight >= messagesDiv.scrollHeight - 50;
    const isUserMessage = messages.length > 0 && messages[messages.length - 1].sender === 'user';
    
    if (lastMessagesLength === 0 || isUserMessage || isAtBottom) {
      setTimeout(() => {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      }, 0);
    }
    lastMessagesLength = messages.length;
  }

  onMount(() => {
    addMessage('Welcome! Ask me anything about the Quran.', 'agent');

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
    let sessionId = getSessionId();
    if (!sessionId) {
      addMessage('Creating session...', 'agent');
      const session = await createSession(APP_NAME, USER_ID);
      sessionId = session.id;
    }
    return sessionId;
  }

  function removeFromContext(verse) {
    contextVerses = contextVerses.filter(v => v !== verse);
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
    addMessage(text, 'user');

    try {
      const sessionId = await ensureSession();
      const result = await runAgent(APP_NAME, USER_ID, sessionId, fullText);
      
      let agentResponse = "No response received.";
      if (Array.isArray(result)) {
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

  function handleKeypress(e) {
    if (e.key === 'Enter') {
      sendMessage();
    }
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
  button {
    padding: 5px 10px;
  }
</style>

<h3>QuranAI Chat</h3>
<div class="messages-container" bind:this={messagesDiv}>
  {#each messages as msg}
    <Message text={msg.text} sender={msg.sender} />
  {/each}
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
  <button on:click={sendMessage}>Send</button>
</div>
