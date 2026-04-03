document.addEventListener('DOMContentLoaded', async () => {
  const textarea = document.getElementById('log-text');
  const numQuiz = document.getElementById('num-questions');
  const sendBtn = document.getElementById('send-btn');
  const statusEl = document.getElementById('status-msg');

  // โหลดข้อความที่ค้างไว้
  const data = await chrome.storage.session.get('context');
  if (data.context) {
    textarea.value = data.context;
  }

  textarea.addEventListener('input', () => {
    chrome.storage.session.set({ context: textarea.value });
  });

  // ส่งข้อมูลไปยัง Backend
  sendBtn.addEventListener('click', async () => {
    const text = textarea.value.trim();
    const numquiz = parseInt(numQuiz.value);
    const resultsContainer = document.getElementById('quiz-results');

    if (!text) return alert('กรุณาใส่ข้อความ');
    if (numquiz < 1) return alert('กรุณาใส่จำนวนข้อให้ถูกต้อง');

    statusEl.textContent = "⏳ Generating Quiz...";
    resultsContainer.innerHTML = ""; 

    try {
      const response = await fetch('http://localhost:8000/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text: text,
          numQuiz: numquiz
        })
      });

      if (response.ok) {
        const data = await response.json();
        statusEl.textContent = "✅ Generated!";
        
        if (data.quiz && data.quiz.length > 0) {
            data.quiz.forEach((item, index) => {
                const quizHtml = `
                    <div class="quiz-item">
                        <h4>Q${index + 1}: ${item.question}</h4>
                        ${item.choices.map((choice, i) => `
                            <span class="choice ${choice === item.answer ? 'correct' : ''}">
                                ${String.fromCharCode(65 + i)}) ${choice}
                            </span>
                        `).join('')}
                    </div>
                `;
                resultsContainer.insertAdjacentHTML('beforeend', quizHtml);
            });
        }
      } else {
        statusEl.textContent = "❌ Error: " + response.statusText;
      }
    } catch (e) {
      statusEl.textContent = "❌ Connection failed";
      console.error(e);
    }
  });
});