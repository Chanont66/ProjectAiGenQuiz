document.addEventListener('DOMContentLoaded', async () => {
  // 1. จัดกลุ่ม DOM Elements เพื่อให้เรียกใช้งานง่าย
  const elements = {
    textarea: document.getElementById('log-text'),
    numQuiz: document.getElementById('num-questions'),
    sendBtn: document.getElementById('send-btn'),
    statusEl: document.getElementById('status-msg'),
    resultsContainer: document.getElementById('quiz-results')
  };

  // 2. โหลดข้อความที่ค้างไว้
  try {
    const data = await chrome.storage.session.get('context');
    if (data.context) elements.textarea.value = data.context;
  } catch (err) {
    console.warn("Storage API is not available", err);
  }

  // เซฟข้อความอัตโนมัติเมื่อพิมพ์
  elements.textarea.addEventListener('input', () => {
    chrome.storage.session.set({ context: elements.textarea.value });
  });

  // 3. ส่งข้อมูลไปยัง Backend
  elements.sendBtn.addEventListener('click', async () => {
    const text = elements.textarea.value.trim();
    const numquiz = parseInt(elements.numQuiz.value, 10);

    // Validate ข้อมูล
    if (!text) return alert('กรุณาใส่ข้อความ');
    if (isNaN(numquiz) || numquiz < 1) return alert('กรุณาใส่จำนวนข้อให้ถูกต้อง');

    // อัปเดตสถานะ UI เป็น Loading
    setLoadingState(true);

    try {
      const response = await fetch('http://localhost:8000/generate-quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text: text,
          numQuiz: numquiz
        })
      });

      // จัดการ Error กรณีฝั่ง Server มีปัญหา
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || response.statusText || 'Unknown Error');
      }

      const data = await response.json();
      
      // แสดงผลข้อสอบ
      renderQuiz(data.quiz);
      elements.statusEl.textContent = "สร้างข้อสอบสำเร็จ!";

    } catch (e) {
      elements.statusEl.textContent = `ข้อผิดพลาด: ${e.message}`;
      console.error(e);
    } finally {
      // ปลดล็อค UI เมื่อทำงานเสร็จ (ไม่ว่าจะสำเร็จหรือ Error)
      setLoadingState(false, false);
    }
  });

  // ==========================================
  // Helper Functions (แยกฟังก์ชันเพื่อให้โค้ดอ่านง่าย)
  // ==========================================

  // ฟังก์ชันจัดการ UI ตอนโหลด
  function setLoadingState(isLoading, clearResults = true) {
    elements.sendBtn.disabled = isLoading;
    elements.textarea.disabled = isLoading;
    if (isLoading) {
      elements.statusEl.textContent = "กำลังสร้างข้อสอบ...";
      if (clearResults) elements.resultsContainer.innerHTML = ""; 
    }
  }

  // ฟังก์ชันวาด HTML ข้อสอบ
  function renderQuiz(quizList) {
    if (!quizList || quizList.length === 0) {
      elements.resultsContainer.innerHTML = "<p>ไม่สามารถสร้างข้อสอบได้</p>";
      return;
    }

    // ใช้ map แล้ว join เพื่อลดการเรียก DOM หลายๆ รอบ (Performance ดีกว่า)
    const html = quizList.map((item, index) => `
      <div class="quiz-item">
        <h4>ข้อ ${index + 1}: ${escapeHTML(item.question)}</h4>
        <div class="choices-container">
          ${item.choices.map((choice, i) => `
            <div class="choice ${choice === item.answer ? 'correct' : ''}">
              ${String.fromCharCode(65 + i)}) ${escapeHTML(choice)}
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');

    elements.resultsContainer.innerHTML = html;
  }

  // ฟังก์ชันทำความสะอาดข้อความ ป้องกัน XSS Attack
  function escapeHTML(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/[&<>'"]/g, tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag));
  }
});