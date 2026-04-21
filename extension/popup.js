document.addEventListener('DOMContentLoaded', async () => {
  // ============================================================
  // STATE
  // ============================================================
  let quizData = [];       // ข้อสอบทั้งหมดจาก Backend
  let currentIndex = 0;   // ข้อปัจจุบัน
  let score = 0;           // คะแนน
  let answers = [];        // ที่เก็บคำตอบผู้ใช้แต่ละข้อ
  let answered = false;    // ผู้ใช้ตอบข้อนี้แล้วหรือยัง

  // ============================================================
  // DOM ELEMENTS
  // ============================================================
  const $ = id => document.getElementById(id);

  const views = {
    setup: $('view-setup'),
    quiz:  $('view-quiz'),
    result: $('view-result'),
  };

  const setupEls = {
    textarea: $('log-text'),
    numQuiz:  $('num-questions'),
    sendBtn:  $('send-btn'),
    statusEl: $('status-msg'),
  };

  const quizEls = {
    progress:    $('q-progress'),
    progressBar: $('q-bar'),
    scoreBadge:  $('q-score'),
    qText:       $('q-text'),
    choices:     $('q-choices'),
    feedback:    $('q-feedback'),
    nextBtn:     $('q-next'),
    backBtn:     $('q-back'),
  };

  const resultEls = {
    emoji:    $('r-emoji'),
    title:    $('r-title'),
    subtitle: $('r-subtitle'),
    bigScore: $('r-score'),
    pct:      $('r-pct'),
    review:   $('r-review'),
    retryBtn: $('retry-btn'),
    newBtn:   $('new-quiz-btn'),
  };

  // ============================================================
  // VIEW SWITCHER
  // ============================================================
  function showView(name) {
    Object.values(views).forEach(v => v.classList.remove('active'));
    views[name].classList.add('active');
  }

  // ============================================================
  // SETUP VIEW: โหลดข้อมูลเก่า + ส่งสร้างข้อสอบ
  // ============================================================
  try {
    const data = await chrome.storage.session.get('context');
    if (data.context) setupEls.textarea.value = data.context;
  } catch (err) { /* ไม่มี Storage API - รันนอก Extension */ }

  setupEls.textarea.addEventListener('input', () => {
    try { chrome.storage.session.set({ context: setupEls.textarea.value }); } catch (_) {}
  });

  setupEls.sendBtn.addEventListener('click', async () => {
    const text = setupEls.textarea.value.trim();
    const numquiz = parseInt(setupEls.numQuiz.value, 10);

    if (!text) return showStatus('กรุณาใส่เนื้อหาก่อนสร้างข้อสอบ', true);
    if (isNaN(numquiz) || numquiz < 1) return showStatus('กรุณาใส่จำนวนข้อให้ถูกต้อง', true);

    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/generate-quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, numQuiz: numquiz }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || response.statusText || 'Unknown Error');
      }

      const data = await response.json();
      if (!data.quiz || data.quiz.length === 0) throw new Error('ไม่สามารถสร้างข้อสอบได้');

      // เริ่มโหมดถามตอบ
      startQuiz(data.quiz);

    } catch (e) {
      showStatus(`ข้อผิดพลาด: ${e.message}`, true);
    } finally {
      setLoading(false);
    }
  });

  function setLoading(on) {
    setupEls.sendBtn.disabled = on;
    setupEls.textarea.disabled = on;
    setupEls.statusEl.className = 'status';
    setupEls.statusEl.textContent = on ? '⏳ กำลังสร้างข้อสอบ กรุณารอสักครู่...' : '';
  }

  function showStatus(msg, isError = false) {
    setupEls.statusEl.className = 'status' + (isError ? ' error' : '');
    setupEls.statusEl.textContent = msg;
  }

  // ============================================================
  // QUIZ MODE
  // ============================================================
  function startQuiz(data) {
    quizData = data;
    currentIndex = 0;
    score = 0;
    answers = new Array(data.length).fill(null);
    showView('quiz');
    renderQuestion();
  }

  function renderQuestion() {
    const item = quizData[currentIndex];
    const total = quizData.length;
    answered = answers[currentIndex] !== null;

    // Progress
    quizEls.progress.textContent = `ข้อ ${currentIndex + 1} / ${total}`;
    quizEls.progressBar.style.width = `${((currentIndex) / total) * 100}%`;
    quizEls.scoreBadge.textContent = `คะแนน: ${score}`;
    quizEls.qText.textContent = item.question;

    // Render choices
    const labels = ['A. ', 'B. ', 'C. ', 'D. '];
    quizEls.choices.innerHTML = '';
    item.choices.forEach((choice, i) => {
      const btn = document.createElement('button');
      btn.className = 'choice-btn';
      btn.innerHTML = `<span class="choice-label">${labels[i]}</span><span>${escapeHTML(choice)}</span>`;
      btn.dataset.choice = choice;

      if (answered) {
        // แสดงผลตามที่เคยตอบแล้ว
        btn.disabled = true;
        applyChoiceStyle(btn, choice, item.answer, answers[currentIndex]);
      } else {
        btn.addEventListener('click', () => handleAnswer(choice, item.answer));
      }

      quizEls.choices.appendChild(btn);
    });

    // Feedback
    if (answered) {
      const wasCorrect = answers[currentIndex] === item.answer;
      showFeedback(wasCorrect, item.answer);
    } else {
      quizEls.feedback.className = 'feedback';
    }

    // Nav buttons
    quizEls.backBtn.style.display = currentIndex > 0 ? 'block' : 'none';
    quizEls.nextBtn.style.display = answered ? 'flex' : 'none';
    quizEls.nextBtn.textContent = currentIndex < total - 1 ? 'ข้อถัดไป →' : '🏆 ดูผลคะแนน';
  }

  function handleAnswer(selected, correctAnswer) {
    if (answered) return;
    answered = true;

    // บันทึกคำตอบ
    answers[currentIndex] = selected;
    const isCorrect = selected === correctAnswer;
    if (isCorrect) score++;

    // อัปเดตปุ่ม
    quizEls.choices.querySelectorAll('.choice-btn').forEach(btn => {
      btn.disabled = true;
      applyChoiceStyle(btn, btn.dataset.choice, correctAnswer, selected);
    });

    showFeedback(isCorrect, correctAnswer);
    quizEls.scoreBadge.textContent = `คะแนน: ${score}`;
    quizEls.progressBar.style.width = `${((currentIndex + 1) / quizData.length) * 100}%`;

    // ซ่อน/แสดงปุ่ม next
    quizEls.nextBtn.style.display = 'flex';
    const total = quizData.length;
    quizEls.nextBtn.textContent = currentIndex < total - 1 ? 'ข้อถัดไป →' : '🏆 ดูผลคะแนน';
  }

  function applyChoiceStyle(btn, choice, correctAnswer, userAnswer) {
    if (choice === correctAnswer) {
      btn.classList.add('correct');
    } else if (choice === userAnswer && userAnswer !== correctAnswer) {
      btn.classList.add('wrong');
    }
  }

  function showFeedback(isCorrect, answer) {
    quizEls.feedback.className = 'feedback show ' + (isCorrect ? 'correct' : 'wrong');
    quizEls.feedback.textContent = isCorrect
      ? '✅ ถูกต้อง! เยี่ยมมาก'
      : `❌ ผิด — เฉลย: ${answer}`;
  }

  // Next button
  quizEls.nextBtn.addEventListener('click', () => {
    if (currentIndex < quizData.length - 1) {
      currentIndex++;
      renderQuestion();
    } else {
      showResult();
    }
  });

  // Back button
  quizEls.backBtn.addEventListener('click', () => {
    if (currentIndex > 0) {
      currentIndex--;
      renderQuestion();
    }
  });

  // ============================================================
  // RESULT VIEW
  // ============================================================
  function showResult() {
    const total = quizData.length;
    const pct = Math.round((score / total) * 100);

    quizEls.progressBar.style.width = '100%';

    // Emoji + title based on score
    let emoji, title, subtitle;
    if (pct === 100) { emoji = '🏆'; title = 'Perfect Score!'; subtitle = 'คุณทำได้ 100% ยอดเยี่ยมมาก!'; }
    else if (pct >= 80) { emoji = '🎉'; title = 'ยอดเยี่ยม!'; subtitle = 'คุณทำได้ดีมาก!'; }
    else if (pct >= 60) { emoji = '👍'; title = 'ผ่านแล้ว!'; subtitle = 'ยังมีที่ต้องปรับปรุง'; }
    else if (pct >= 40) { emoji = '😅'; title = 'พอผ่าน...'; subtitle = 'ลองใหม่อีกครั้งนะ!'; }
    else { emoji = '📚'; title = 'ต้องศึกษาเพิ่ม'; subtitle = 'อ่านเนื้อหาแล้วลองใหม่!'; }

    resultEls.emoji.textContent = emoji;
    resultEls.title.textContent = title;
    resultEls.subtitle.textContent = subtitle;
    resultEls.bigScore.innerHTML = `${score}/${total} <span id="r-pct">(${pct}%)</span>`;

    // Review answers
    resultEls.review.innerHTML = quizData.map((item, i) => {
      const userAns = answers[i];
      const isCorrect = userAns === item.answer;
      return `
        <div class="review-item ${isCorrect ? 'correct' : 'wrong'}">
          <b>${isCorrect ? '✅' : '❌'} ข้อ ${i + 1}:</b> ${escapeHTML(item.question)}<br>
          ${isCorrect
            ? `เฉลย: ${escapeHTML(item.answer)}`
            : `คุณตอบ: ${escapeHTML(userAns || '—')} | เฉลย: ${escapeHTML(item.answer)}`
          }
        </div>`;
    }).join('');

    showView('result');
  }

  // Retry (ทำข้อสอบชุดเดิมใหม่)
  resultEls.retryBtn.addEventListener('click', () => startQuiz(quizData));

  // New quiz (กลับหน้า setup)
  resultEls.newBtn.addEventListener('click', () => {
    showView('setup');
    showStatus('');
  });

  // ============================================================
  // UTILS
  // ============================================================
  function escapeHTML(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/[&<>'\"]/g, tag => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));
  }
});