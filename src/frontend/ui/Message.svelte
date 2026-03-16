<script>
  import { marked } from 'marked';
  export let text = '';
  export let sender = 'user'; // 'user' or 'agent'
  export let events = [];

  let expanded = false;

  $: html = marked.parse(text || '');

  function toggleExpand() {
    expanded = !expanded;
  }

  function formatPart(part) {
    if (part.text) return `Text: ${part.text}`;
    if (part.functionCall) {
      return `Tool Call: ${part.functionCall.name}(${JSON.stringify(part.functionCall.args)})`;
    }
    if (part.functionResponse) {
      return `Tool Response [${part.functionResponse.name}]: ${JSON.stringify(part.functionResponse.response)}`;
    }
    if (part.executableCode) {
      return `Code Execution [${part.executableCode.language}]:\n${part.executableCode.code}`;
    }
    if (part.codeExecutionResult) {
      return `Code Result [${part.codeExecutionResult.outcome}]:\n${part.codeExecutionResult.output}`;
    }
    return JSON.stringify(part);
  }
</script>

<style>
  .message-wrapper {
    display: flex;
    flex-direction: column;
    margin-bottom: 10px;
  }
  .bubble {
    max-width: 80%;
    padding: 8px 12px;
    border-radius: 15px;
    line-height: 1.4;
    position: relative;
  }
  .user {
    align-self: flex-end;
    background-color: #007bff;
    color: white;
    border-bottom-right-radius: 2px;
  }
  .agent {
    align-self: flex-start;
    background-color: #e9ecef;
    color: #333;
    border-bottom-left-radius: 2px;
  }

  /* Markdown Styles */
  .bubble :global(p) { margin: 0 0 8px 0; }
  .bubble :global(p:last-child) { margin-bottom: 0; }
  .bubble :global(ul), .bubble :global(ol) { margin: 8px 0; padding-left: 20px; }
  .bubble :global(code) { background: rgba(0,0,0,0.1); padding: 2px 4px; border-radius: 3px; }
  .bubble :global(pre) { background: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 5px; overflow-x: auto; margin: 8px 0; }
  .bubble :global(blockquote) { border-left: 4px solid #ccc; margin: 8px 0; padding-left: 10px; color: #666; }

  .expand-btn {
    align-self: flex-start;
    background: none;
    border: none;
    color: #007bff;
    font-size: 0.75em;
    cursor: pointer;
    padding: 2px 0;
    margin-top: 4px;
    text-decoration: underline;
  }
  .events-log {
    margin-top: 8px;
    font-family: monospace;
    font-size: 0.8em;
    background: #f0f0f0;
    padding: 8px;
    border-radius: 5px;
    border: 1px solid #ddd;
    white-space: pre-wrap;
    max-height: 300px;
    overflow-y: auto;
  }
  .event-item {
    margin-bottom: 8px;
    border-bottom: 1px solid #eee;
    padding-bottom: 4px;
  }
  .event-item:last-child {
    border-bottom: none;
  }
  .event-author {
    font-weight: bold;
    color: #555;
  }
</style>

<div class="message-wrapper">
  <div class="bubble {sender}">
    {@html html}
  </div>
  
  {#if sender === 'agent' && events && events.length > 0}
    <button class="expand-btn" on:click={toggleExpand}>
      {expanded ? 'Hide Steps' : 'Show Steps (' + events.length + ')'}
    </button>
    
    {#if expanded}
      <div class="events-log">
        {#each events as event, i}
          <div class="event-item">
            <div class="event-author">[{i+1}] {event.author}</div>
            {#if event.content && event.content.parts}
              {#each event.content.parts as part}
                <div class="event-part">{formatPart(part)}</div>
              {/each}
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>
