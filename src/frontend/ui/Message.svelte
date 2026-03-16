<script>
  import { marked } from 'marked';
  export let text = '';
  export let sender = 'agent';

  $: html = marked.parse(text);
</script>

<div class="message {sender}">
  <div class="label">{sender === 'user' ? 'You' : 'AI'}:</div>
  <div class="content">
    {@html html}
  </div>
</div>

<style>
  .message {
    margin-bottom: 12px;
    padding: 8px;
    border-radius: 8px;
  }
  .user {
    text-align: right;
    color: #2563eb;
    background-color: #f0f7ff;
    margin-left: 20%;
  }
  .agent {
    text-align: left;
    color: #059669;
    background-color: #f0fdf4;
    margin-right: 20%;
  }
  .label {
    font-weight: bold;
    font-size: 0.85em;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .content {
    word-break: break-word;
    font-size: 0.95em;
    line-height: 1.5;
  }
  
  /* Markdown specific styles */
  .content :global(p) {
    margin: 0 0 0.75em 0;
  }
  .content :global(p:last-child) {
    margin-bottom: 0;
  }
  .content :global(ul), .content :global(ol) {
    margin: 0 0 0.75em 0;
    padding-left: 1.5em;
    text-align: left;
  }
  .content :global(li) {
    margin-bottom: 0.25em;
  }
  .content :global(code) {
    background: rgba(0, 0, 0, 0.05);
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: monospace;
  }
  .content :global(pre) {
    background: rgba(0, 0, 0, 0.05);
    padding: 8px;
    border-radius: 4px;
    overflow-x: auto;
    margin-bottom: 0.75em;
  }
  .content :global(pre code) {
    background: none;
    padding: 0;
  }
  .content :global(h1), .content :global(h2), .content :global(h3) {
    margin: 0.5em 0;
    font-size: 1.1em;
    text-align: left;
  }
  .content :global(blockquote) {
    border-left: 4px solid #ccc;
    margin: 0 0 0.75em 0;
    padding-left: 12px;
    color: #666;
    font-style: italic;
    text-align: left;
  }
</style>
