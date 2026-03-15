<script>
  import { onMount } from 'svelte';
  import { createSession, getSessionId, runAgent } from '../shared/lib.js';

  const APP_NAME = 'agent';
  const USER_ID = 'extension-user';

  let messages = [];
  let userInput = '';
  let messagesDiv;

  function addMessage(text, sender) {
    messages = [...messages, { text, sender }];
  }

  $: if (messages && messagesDiv) {
    // Scroll to bottom when messages change
    setTimeout(() => {
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }, 0);
  }

  async function ensureSession() {
    let sessionId = getSessionId();
    if (!sessionId) {
      addMessage('Creating session...', 'agent');
      const session = await createSession(APP_NAME, USER_ID);
      sessionId = session.id;
    }
    return sessionId;
  }

  async function sendMessage() {
    const text = userInput.trim();
    if (!text) return;

    userInput = '';
    addMessage(text, 'user');

    try {
      const sessionId = await ensureSession();
      const result = await runAgent(APP_NAME, USER_ID, sessionId, text);
      
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

  onMount(() => {
    addMessage('Welcome! Ask me anything about the Quran.', 'agent');
  });
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
  }
  .message {
    margin-bottom: 8px;
  }
  .user {
    text-align: right;
    color: blue;
  }
  .agent {
    text-align: left;
    color: green;
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
    <div class="message {msg.sender}">
      {msg.sender === 'user' ? 'You' : 'AI'}: {msg.text}
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
