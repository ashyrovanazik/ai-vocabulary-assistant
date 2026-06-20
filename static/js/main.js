document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('button');
  buttons.forEach((button) => {
    button.addEventListener('mouseenter', () => {
      button.style.transform = 'translateY(-1px)';
    });
    button.addEventListener('mouseleave', () => {
      button.style.transform = '';
    });
  });

  const openAdd = document.getElementById('open-add-vocab');
  const closeAdd = document.getElementById('close-add-vocab');
  const cancelAdd = document.getElementById('cancel-add-vocab');
  const modal = document.getElementById('add-vocab-modal');

  if (openAdd && modal) {
    openAdd.addEventListener('click', () => modal.classList.add('open'));
  }
  if (closeAdd && modal) {
    closeAdd.addEventListener('click', () => modal.classList.remove('open'));
  }
  if (cancelAdd && modal) {
    cancelAdd.addEventListener('click', () => modal.classList.remove('open'));
  }
  if (modal) {
    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        modal.classList.remove('open');
      }
    });
  }
  // Search agent run handler
  const agentForm = document.getElementById('agent-run-form');
  const agentCommand = document.getElementById('agent-command');
  const agentSteps = document.getElementById('agent-steps');
  const agentResult = document.getElementById('agent-result');

  function showSteps(steps) {
  agentSteps.style.display = 'flex';
  agentSteps.style.flexWrap = 'wrap';
  agentSteps.style.gap = '14px';
  agentSteps.style.justifyContent = 'center';
  agentSteps.innerHTML = '';

  steps.forEach((s) => {
    const el = document.createElement('div');
    el.className = 'workflow-step';

    let cleanStep = s;

    if (cleanStep.includes('Real source found:')) {
      cleanStep = cleanStep.split('|')[0].trim();
    }

    el.textContent = cleanStep;
    agentSteps.appendChild(el);
  });
}
  function showResult(data) {
    agentResult.style.display = 'block';
    agentResult.innerHTML = '';
    if (!data || !data.success) {
      const p = document.createElement('p');
      p.className = 'empty-state';
      p.textContent = data && data.error ? data.error : 'Agent failed.';
      agentResult.appendChild(p);
      return;
    }
    const fields = ['word','phonetic','part_of_speech','chinese_meaning','pinyin','definition','example_sentence','chinese_translation','source_name','source_url','difficulty','ai_explanation'];
    const container = document.createElement('div');
    fields.forEach((f) => {
      const row = document.createElement('div');
      row.style.marginBottom = '10px';
      const label = document.createElement('strong');
      label.textContent = f.replace(/_/g,' ') + ': ';
      const value = document.createElement('span');
      if (f === 'source_url' && data[f]) {
        const a = document.createElement('a');
        a.href = data[f];
        a.target = '_blank';
        a.textContent = data[f];
        value.appendChild(a);
      } else {
        value.textContent = data[f] || '';
      }
      row.appendChild(label);
      row.appendChild(value);
      container.appendChild(row);
    });
    const link = document.createElement('a');
    link.href = '/vocabulary';
    link.className = 'secondary-button';
    link.textContent = 'View in Vocabulary';
    container.appendChild(link);
    agentResult.appendChild(container);
  }

  if (agentForm) {
    agentForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const cmd = agentCommand.value.trim();
      if (!cmd) return;
      agentSteps.style.display = 'block';
      agentSteps.innerHTML = '';
      agentResult.style.display = 'none';
      const initial = ['User input received', 'Searching authentic English sources', 'Real source found', 'Extracting example sentence', 'Generating vocabulary data with LLM', 'Saving to MySQL database', 'Completed'];
      showSteps(['User input received']);

      try {
        const resp = await fetch('/search-agent/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: cmd })
        });
        const data = await resp.json();
        // show progress steps from agent if present
        const remoteSteps = data && data.steps ? data.steps : initial;
        showSteps(remoteSteps);
        showResult(data);
      } catch (err) {
        showSteps(['Agent request failed']);
        showResult({ success: false, error: 'Network or server error' });
      }
    });
  }
});
