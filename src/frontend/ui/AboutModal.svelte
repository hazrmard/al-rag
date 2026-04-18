<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  function close() {
    dispatch('close');
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      close();
    }
  }

  const isExtension = __QURANAI_IS_EXTENSION__;
</script>

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
  }
  .modal-container {
    background: white;
    padding: 20px;
    border-radius: 8px;
    max-width: 400px;
    width: 90%;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    position: relative;
  }
  .close-icon {
    position: absolute;
    top: 10px;
    right: 10px;
    background: none;
    border: none;
    font-size: 1.5em;
    cursor: pointer;
    color: #666;
  }
  h2 {
    margin-top: 0;
    color: #333;
  }
  .features {
    margin: 15px 0;
    padding-left: 20px;
  }
  .features li {
    margin-bottom: 8px;
  }
  .links {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .links a {
    color: #007bff;
    text-decoration: none;
  }
  .links a:hover {
    text-decoration: underline;
  }
  .footer {
    margin-top: 20px;
    font-size: 0.9em;
    color: #666;
    text-align: center;
  }
</style>

<div 
  class="modal-backdrop" 
  on:click|self={close} 
  on:keydown|self={handleKeydown}
  role="button" 
  tabindex="-1"
>
  <div class="modal-container">
    <button class="close-icon" on:click={close}>×</button>
    <h2>About QuranAI</h2>
    <p>QuranAI is an intelligent assistant designed to help you explore and understand the Quran.</p>
    
    <h3>Features</h3>
    <ul class="features">
      <li>Chat with an AI agent about the Quran.</li>
      <li>Add verses to context for more relevant answers.</li>
      <li>Get deep-dive explanations for specific verses.</li>
    </ul>

    {#if !isExtension}
      <h3>Get the Extension</h3>
      <p>Enhance your experience on alislam.org/quran/app with our browser extensions.</p>
      <div class="links">
        <a href="https://chromewebstore.google.com/detail/quranai/hmabpgkeagldiiggmgbkbbfgfmdmppgl" target="_blank" rel="noopener noreferrer">
          Install for Chrome
        </a>
        <a href="https://addons.mozilla.org/en-US/firefox/addon/quranai" target="_blank" rel="noopener noreferrer">
          Install for Firefox
        </a>
      </div>
    {/if}

    <div class="footer">
      Developed by <a href="https://iahmed.me" target="_blank" rel="noopener noreferrer">iahmed.me</a>
    </div>
  </div>
</div>
