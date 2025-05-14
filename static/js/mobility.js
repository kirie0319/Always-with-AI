// DOM elements
const chatBox = document.getElementById('chat-box');
const inputField = document.getElementById('input');
const sendButton = document.getElementById('send-btn');
const promptNameElement = document.getElementById('prompt-name');

// State variables
let currentStep = 0;
let isProposalVisible = false;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
  inputField.focus();
  loadConversationHistory();

  // Create proposal button handler
  const createProposalBtn = document.getElementById('create-proposal-btn');
  if (createProposalBtn) {
    createProposalBtn.addEventListener('click', showProposal);
  }


  // マークダウンの設定
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function (code, lang) {
      if (hljs && lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(code, { language: lang }).value;
        } catch (e) { }
      }
      return code;
    }
  });

  // Submit on Enter key
  inputField.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      send();
    }
  });
  
  // Send button click event
  sendButton.addEventListener('click', send);

  // セッションストレージから選択中のプロンプト名を取得して表示
  const selectedPromptName = sessionStorage.getItem('selectedPromptName');
  if (selectedPromptName) {
    promptNameElement.textContent = selectedPromptName;
  }
  
  // DOM要素の取得
  const menuItems = document.querySelectorAll('.sidebar-menu .menu-item');
  menuItems.forEach(item => {
    item.addEventListener('click', (e) => {
      menuItems.forEach(mi => mi.classList.remove('active'));
      item.classList.add('active');
    });
  });

  const currentPath = window.location.pathname;
  menuItems.forEach(item => {
    const link = item.querySelector('a');
    if (link && currentPath.includes(link.getAttribute('href'))) {
      menuItems.forEach(mi => mi.classList.remove('active'));
      item.classList.add('active');
    }
  });

  const toggleBtn = document.querySelector('.toggle-btn');
  const sidebar = document.querySelector('.sidebar');
  const step0 = document.getElementById('step-0');
  const step1 = document.getElementById('step-1');
  const step3 = document.getElementById('step-3');
  const step4 = document.getElementById('step-4');
  const step5 = document.getElementById('step-5');
  
  // ボタン参照
  const connectInfoBtn = document.getElementById('connect-info-btn');
  const backToStep0Btn = document.getElementById('back-to-step-0');
  const nextToStep2Btn = document.getElementById('next-to-step-2');
  const backToStep2Btn = document.getElementById('back-to-step-2');
  const nextToStep4Btn = document.getElementById('next-to-step-4');
  const backToStep3Btn = document.getElementById('back-to-step-3');
  const nextToStep5Btn = document.getElementById('next-to-step-5');
  const backToStep4Btn = document.getElementById('back-to-step-4');
  const completeFormFinalBtn = document.getElementById('complete-form-final');
  const addCarComparisonBtn = document.getElementById('add-car-comparison');
  const optionButtons = document.querySelectorAll('.mobility-option-button');
  const supportButtons = document.querySelectorAll('.support-button');

  // Update step visibility based on current step
  updateStepVisibility();
  
  // サイドバーの折りたたみ/展開
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      toggleBtn.innerHTML = sidebar.classList.contains('collapsed') ? '«' : '»';
    });
  }

  // 情報連携ボタン (Step 0 -> Step 1)
  if (connectInfoBtn) {
    connectInfoBtn.addEventListener('click', () => {
      currentStep = 1;
      updateStepVisibility();
      appendMessage('bot', 'CRM情報の連携が完了しました。顧客の基本情報に入力をお願いします。名前と年齢は必須項目となっています。');
    });
  }

  // 前へボタン (Step 1 -> Step 0)
  if (backToStep0Btn) {
    backToStep0Btn.addEventListener('click', () => {
      currentStep = 0;
      updateStepVisibility();
    });
  }

  // 次へボタン (Step 1 -> Step 3)
  if (nextToStep2Btn) {
    nextToStep2Btn.addEventListener('click', () => {
      // 必須項目のチェック
      const nameField = document.getElementById('name');
      const ageField = document.getElementById('age');
      
      if (!nameField.value.trim()) {
        alert('名前は必須項目です。入力してください。');
        nameField.focus();
        return;
      }
      
      if (!ageField.value.trim()) {
        alert('年齢は必須項目です。入力してください。');
        ageField.focus();
        return;
      }
      
      // Step 3に進む
      currentStep = 3;
      updateStepVisibility();
      appendMessage('bot', '基本情報の入力ありがとうございます。次に家計状況についてお聞かせください。');
    });
  }
  
  // 前へボタン (Step 3 -> Step 1)
  if (backToStep2Btn) {
    backToStep2Btn.addEventListener('click', () => {
      currentStep = 1;
      updateStepVisibility();
    });
  }
  
  // 次へボタン (Step 3 -> Step 4)
  if (nextToStep4Btn) {
    nextToStep4Btn.addEventListener('click', () => {
      // 必須項目のチェック
      const housingLoanField = document.getElementById('housing-loan');
      
      if (!housingLoanField.value) {
        alert('家賃・住宅ローンは必須項目です。選択してください。');
        housingLoanField.focus();
        return;
      }
      
      // Step 4に進む
      currentStep = 4;
      updateStepVisibility();
      appendMessage('bot', '家計状況の入力ありがとうございます。次に車両情報についてお聞かせください。');
    });
  }
  
  // 前へボタン (Step 4 -> Step 3)
  if (backToStep3Btn) {
    backToStep3Btn.addEventListener('click', () => {
      currentStep = 3;
      updateStepVisibility();
    });
  }
  
  // 次へボタン (Step 4 -> Step 5)
  if (nextToStep5Btn) {
    nextToStep5Btn.addEventListener('click', () => {
      // 必須項目のチェック
      const carTypeField = document.getElementById('car-type');
      const carYearField = document.getElementById('car-year');
      const inspectionDateField = document.getElementById('inspection-date');
      const mileageField = document.getElementById('mileage');
      
      if (!carTypeField.value.trim()) {
        alert('車種は必須項目です。入力してください。');
        carTypeField.focus();
        return;
      }
      
      if (!carYearField.value.trim()) {
        alert('年式は必須項目です。入力してください。');
        carYearField.focus();
        return;
      }
      
      if (!inspectionDateField.value) {
        alert('車検満了日は必須項目です。入力してください。');
        inspectionDateField.focus();
        return;
      }
      
      if (!mileageField.value) {
        alert('走行距離は必須項目です。入力してください。');
        mileageField.focus();
        return;
      }
      
      // Step 5に進む
      currentStep = 5;
      updateStepVisibility();
      appendMessage('bot', '車両情報の入力ありがとうございます。次に車両コスト比較についてお聞かせください。現在の車両情報と、比較したい車両の情報を入力してください。');
      
      // 自動的に現在の車両情報をStep 4の情報から転記
      if (carTypeField.value) {
        document.getElementById('current-car-type').value = carTypeField.value;
      }
    });
  }
  
  // 前へボタン (Step 5 -> Step 4)
  if (backToStep4Btn) {
    backToStep4Btn.addEventListener('click', () => {
      currentStep = 4;
      updateStepVisibility();
    });
  }
  
  // 比較車両追加ボタン
  if (addCarComparisonBtn) {
    addCarComparisonBtn.addEventListener('click', () => {
      alert('この機能は現在開発中です。次期アップデートでご利用いただけるようになります。');
    });
  }
  
  // 最終登録完了ボタン
  if (completeFormFinalBtn) {
    completeFormFinalBtn.addEventListener('click', () => {
      // 必須項目のチェック
      const currentCarTypeField = document.getElementById('current-car-type');
      const currentCarModelField = document.getElementById('current-car-model');
      const annualMileageField = document.getElementById('annual-mileage');
      
      if (!currentCarTypeField.value.trim()) {
        alert('現在の車両の車種は必須項目です。入力してください。');
        currentCarTypeField.focus();
        return;
      }
      
      if (!currentCarModelField.value.trim()) {
        alert('現在の車両の型式は必須項目です。入力してください。');
        currentCarModelField.focus();
        return;
      }
      
      if (!annualMileageField.value) {
        alert('年間走行距離は必須項目です。入力してください。');
        annualMileageField.focus();
        return;
      }
      
      // 完了メッセージを表示
      appendMessage('bot', 'すべての情報の入力ありがとうございます！車両コスト比較情報も含めて登録されました。比較結果は後ほど担当者よりご連絡いたします。今後の車検案内や保険更新のご案内、車の買い替え時期など、適切なタイミングでご連絡させていただきます。他にご質問などがありましたら、チャットでお気軽にお聞きください。');
    });
  }

  // オプションボタンの選択処理
  if (optionButtons) {
    optionButtons.forEach((button) => {
      button.addEventListener('click', () => {
        // 同じグループ内の他のボタンからアクティブクラスを削除
        const parentGroup = button.closest('.mobility-button-group');
        if (parentGroup) {
          parentGroup.querySelectorAll('.mobility-option-button').forEach((groupButton) => {
            groupButton.classList.remove('active');
          });
        }

        // クリックされたボタンにアクティブクラスを追加
        button.classList.add('active');
      });
    });
  }

  // サポートボタン（T）クリック
  if (supportButtons) {
    supportButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const fieldName = e.target.closest('.mobility-input-row').querySelector('label').textContent;
        appendMessage('bot', `「${fieldName}」について何かお手伝いできることはありますか？情報の入力方法や、この項目の重要性についてご説明できます。`);
      });
    });
  }

  // トークン認証の確認
  const token = localStorage.getItem('access_token');
  if (!token) {
    console.error('アクセストークンがありません。ログインページにリダイレクトします。');
    window.location.href = '/login';
  } else {
    console.log('アクセストークンが見つかりました。トークンの最初の10文字: ' + token.substring(0, 10) + '...');

    // トークンの検証リクエストを送信
    fetch('/validate-token', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
      .then(response => {
        if (!response.ok) {
          throw new Error('トークン検証に失敗しました');
        }
        return response.json();
      })
      .then(data => {
        console.log('トークン検証成功:', data);
      })
      .catch(error => {
        console.error('トークン検証エラー:', error);
        // トークンが無効な場合はログインページにリダイレクト
        localStorage.removeItem('access_token');
        window.location.href = '/login?invalid_token=true';
      });
  }
});

// ステップの表示/非表示を更新する関数
function updateStepVisibility() {
  const steps = [
    document.getElementById('step-0'),
    document.getElementById('step-1'),
    document.getElementById('step-3'),
    document.getElementById('step-4'),
    document.getElementById('step-5')
  ];

  // すべてのステップを非表示
  steps.forEach(step => {
    if (step) step.classList.add('hidden');
  });

  // 現在のステップだけ表示
  const currentStepIndices = [0, 1, 3, 4, 5]; // 実際のステップID
  const currentStepIndex = currentStepIndices.indexOf(currentStep);
  
  if (currentStepIndex >= 0 && steps[currentStepIndex]) {
    steps[currentStepIndex].classList.remove('hidden');
  }
  
  document.body.setAttribute('data-current-step', currentStep);
}

// Format timestamp
function formatTimestamp() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}

// Add message to chat
function appendMessage(role, text) {
  const timestamp = formatTimestamp();
  const messageDiv = document.createElement('div');

  if (role === 'user') {
    messageDiv.className = 'message user';

    // ユーザーアバター
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar';
    const avatarIcon = document.createElement('i');
    avatarIcon.className = 'fas fa-user';
    avatarDiv.appendChild(avatarIcon);

    // メッセージコンテンツ
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;

    // タイムスタンプ
    const timeSpan = document.createElement('span');
    timeSpan.className = 'timestamp';
    timeSpan.textContent = timestamp;
    contentDiv.appendChild(timeSpan);

    // メッセージの組み立て
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
  } else {
    messageDiv.className = 'message bot';

    // AIアバター
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar';
    const avatarIcon = document.createElement('i');
    avatarIcon.className = 'fas fa-robot';
    avatarDiv.appendChild(avatarIcon);

    // メッセージコンテンツ
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // AIメッセージの場合はマークダウンをサポート
    if (containsMarkdown(text)) {
      // マークダウンを含む場合
      const contentInner = document.createElement('div');
      contentInner.className = 'markdown-content';
      contentInner.innerHTML = renderMarkdown(text);

      // コードブロックがあれば、highlight.jsを適用
      if (hljs) {
        contentInner.querySelectorAll('pre code').forEach((block) => {
          hljs.highlightElement(block);
        });
      }

      contentDiv.appendChild(contentInner);
    } else {
      // マークダウンがない場合は段落に分ける
      const paragraphs = text.split('\n\n');

      for (const paragraph of paragraphs) {
        if (paragraph.trim()) {
          const p = document.createElement('p');
          p.textContent = paragraph;
          contentDiv.appendChild(p);
        }
      }
    }

    // タイムスタンプ
    const timeSpan = document.createElement('span');
    timeSpan.className = 'timestamp';
    timeSpan.textContent = timestamp;
    contentDiv.appendChild(timeSpan);

    // メッセージの組み立て
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
  }

  // Add to chat
  chatBox.appendChild(messageDiv);

  // Scroll to bottom
  scrollToBottom();
}

// マークダウンをパースして安全に描画する関数
function renderMarkdown(text) {
  return marked.parse(text);
}

// マークダウンかどうかを判定する関数
function containsMarkdown(text) {
  // 一般的なマークダウン記法をチェック
  const markdownPatterns = [
    /\*\*.*?\*\*/,           // 太字 **bold**
    /\*.*?\*/,               // 斜体 *italic*
    /`.*?`/,                 // インラインコード `code`
    /```[\s\S]*?```/,        // コードブロック ```code```
    /^#+\s+.*/m,             // 見出し # Heading
    /^\s*[-*+]\s+.*/m,       // リスト - item
    /^\s*\d+\.\s+.*/m,       // 数字リスト 1. item
    /\[.*?\]\(.*?\)/,        // リンク [link](url)
    /!\[.*?\]\(.*?\)/,       // 画像 ![alt](url)
    /^\s*>\s+.*/m,           // 引用 > quote
    /^\s*---+\s*$/m,         // 水平線 ---
    /\|\s.*\s\|/             // テーブル | table |
  ];

  // いずれかのパターンにマッチすればマークダウンと判定
  return markdownPatterns.some(pattern => pattern.test(text));
}

// Show typing indicator
function showTyping() {
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message bot typing-message';
  typingDiv.innerHTML = `
    <div class="avatar">
      <i class="fas fa-robot"></i>
    </div>
    <div class="message-content">
      <div class="typing">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  `;

  chatBox.appendChild(typingDiv);
  scrollToBottom();
  return typingDiv;
}

// Scroll chat to bottom
function scrollToBottom() {
  chatBox.scrollTop = chatBox.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
  const typingMessage = document.querySelector('.typing-message');
  if (typingMessage) {
    chatBox.removeChild(typingMessage);
  }
}

// Function to get auth headers
function getAuthHeaders() {
  const token = localStorage.getItem('access_token');
  return token ? {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  } : {
    'Content-Type': 'application/json'
  };
}

// Function to load conversation history
async function loadConversationHistory() {
  try {
    const response = await fetch('/conversation_history', {
      method: 'GET',
      headers: getAuthHeaders()
    });

    if (!response.ok) {
      throw new Error('Error loading conversation history');
    }

    const history = await response.json();

    history.forEach((msg) => {
      appendMessage(msg.role, msg.content);
    });
  } catch (error) {
    console.error('Error loading conversation history:', error);
  }
}

// Function to send message
async function send() {
  const text = inputField.value.trim();
  if (!text) return;

  // 入力フィールドをクリア
  inputField.value = '';
  inputField.focus();

  // ユーザーメッセージをUIに追加
  appendMessage('user', text);

  // 既存のEventSourceがあれば閉じる
  if (window.eventSource) {
    window.eventSource.close();
    window.eventSource = null;
  }

  // ローディング表示
  const typingIndicator = showTyping();

  try {
    // POSTリクエスト
    const response = await fetch('/mobility_chat', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ message: text })
    });

    if (!response.ok) {
      throw new Error('Error: ' + response.status);
    }

    if (response.headers.get('Content-Type').includes('text/event-stream')) {
      // SSEストリーミングの場合
      processEventStream(response);
    } else {
      // 通常のJSONレスポンスの場合
      const jsonData = await response.json();
      removeTypingIndicator();
      appendMessage('bot', jsonData.response);
    }
  } catch (error) {
    console.error('Error:', error);
    removeTypingIndicator();
    appendMessage('bot', 'すみません、エラーが発生しました。もう一度お試しください。');
  }
}

// Function to process event stream
function processEventStream(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let assistant_text = '';

  // メッセージ表示用の要素を作成
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message bot';

  const avatarDiv = document.createElement('div');
  avatarDiv.className = 'avatar';
  const avatarIcon = document.createElement('i');
  avatarIcon.className = 'fas fa-robot';
  avatarDiv.appendChild(avatarIcon);

  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';

  const contentInner = document.createElement('div');
  contentInner.className = 'markdown-content';
  contentDiv.appendChild(contentInner);

  const timeSpan = document.createElement('span');
  timeSpan.className = 'timestamp';
  timeSpan.textContent = formatTimestamp();
  contentDiv.appendChild(timeSpan);

  messageDiv.appendChild(avatarDiv);
  messageDiv.appendChild(contentDiv);

  // 読み込み開始
  read();

  function read() {
    reader.read().then(({ done, value }) => {
      if (done) {
        // ストリーム終了、必要なクリーンアップを行う
        removeTypingIndicator();

        // マークダウンの完全なレンダリング
        if (containsMarkdown(assistant_text)) {
          contentInner.innerHTML = renderMarkdown(assistant_text);

          // コードブロックがあれば、highlight.jsを適用
          if (hljs) {
            contentInner.querySelectorAll('pre code').forEach((block) => {
              hljs.highlightElement(block);
            });
          }
        } else {
          // マークダウンがない場合は段落に分ける
          contentInner.innerHTML = '';
          const paragraphs = assistant_text.split('\n\n');
          for (const paragraph of paragraphs) {
            if (paragraph.trim()) {
              const p = document.createElement('p');
              p.textContent = paragraph;
              contentInner.appendChild(p);
            }
          }
        }

        return;
      }

      // 受信したバイナリデータを文字列に変換して蓄積
      buffer += decoder.decode(value, { stream: true });

      // イベントデータを解析
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // 最後の不完全な行は次回処理のために保持

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const eventData = JSON.parse(line.substring(6));

            if (eventData.text) {
              // 最初のテキストチャンクが来たら、タイピングインジケータを削除しメッセージ要素を追加
              if (!assistant_text) {
                removeTypingIndicator();
                chatBox.appendChild(messageDiv);
              }

              // テキストを追加
              assistant_text += eventData.text;

              // 暫定的なレンダリング（ストリーミング表示）
              if (containsMarkdown(assistant_text)) {
                contentInner.innerHTML = renderMarkdown(assistant_text);
              } else {
                contentInner.innerHTML = '';
                const paragraphs = assistant_text.split('\n\n');
                for (const paragraph of paragraphs) {
                  if (paragraph.trim()) {
                    const p = document.createElement('p');
                    p.textContent = paragraph;
                    contentInner.appendChild(p);
                  }
                }
              }

              // 自動スクロール
              scrollToBottom();
            }

            if (eventData.error) {
              // エラーメッセージの処理
              console.error('Error from server:', eventData.error);
              removeTypingIndicator();
              appendMessage('bot', 'すみません、エラーが発生しました: ' + eventData.error);
            }

            if (eventData.complete) {
              // ストリーム完了通知
              console.log('Stream complete');
            }
          } catch (e) {
            console.error('Error parsing event data:', e, line.substring(6));
          }
        }
      }

      // 次のチャンクを読み込む
      read();
    }).catch(error => {
      console.error('Error reading stream:', error);
      removeTypingIndicator();
      appendMessage('bot', 'すみません、データの読み込み中にエラーが発生しました。もう一度お試しください。');
    });
  }
}

// Function to clear chat
function clearChat() {
  if (!confirm('チャット履歴をクリアしますか？')) return;

  try {
    fetch('/clear', {
      method: 'POST',
      headers: getAuthHeaders()
    })
    .then(res => res.json())
    .then(data => {
      // Clear UI
      document.getElementById('chat-box').innerHTML = '';

      // Add welcome message
      appendMessage('bot', 'こんにちは！<br>まずは左側「CRM情報と連携する」にある情報を連携するボタンをクリックしてください☺️');
    })
    .catch(error => {
      console.error('Error clearing chat:', error);
      alert('チャットのクリアに失敗しました。もう一度お試しください。');
    });
  } catch (error) {
    console.error('Error clearing chat:', error);
    alert('チャットのクリアに失敗しました。もう一度お試しください。');
  }
}

// 提案書を表示する関数
function showProposal() {
  // ローディングメッセージを表示
  const proposalBtn = document.getElementById('create-proposal-btn');
  if (proposalBtn) {
      proposalBtn.textContent = '提案書をダウンロードする';
  }
  appendMessage('bot', '提案書を作成中です。しばらくお待ちください...');
  
  // レイアウトを変更するためのクラスを追加
  const formContainer = document.querySelector('.mobility-form-container');
  if (formContainer) {
    formContainer.style.display = 'none';
  }
  
  // 提案書コンテナを作成（存在しない場合）
  let proposalWrapper = document.querySelector('.proposal-container-wrapper');
  if (!proposalWrapper) {
    proposalWrapper = document.createElement('div');
    proposalWrapper.className = 'proposal-container-wrapper';
    
    // スクロール可能にするスタイルを追加
    proposalWrapper.style.position = 'relative';
    proposalWrapper.style.display = 'flex';
    proposalWrapper.style.flexDirection = 'column';
    proposalWrapper.style.width = '100%';
    proposalWrapper.style.height = '100%';
    proposalWrapper.style.overflow = 'hidden';
    
    // 提案書のヘッダー部分
    const proposalHeader = document.createElement('div');
    proposalHeader.className = 'proposal-header';
    proposalHeader.style.position = 'sticky';
    proposalHeader.style.top = '0';
    proposalHeader.style.zIndex = '10';
    proposalHeader.style.backgroundColor = 'white';
    proposalHeader.innerHTML = `
    `;
    proposalWrapper.appendChild(proposalHeader);
    
    // 提案書のコンテンツ部分（スクロール可能に設定）
    const proposalContent = document.createElement('div');
    proposalContent.className = 'proposal-content';
    proposalContent.id = 'proposal-content-area';
    proposalContent.style.overflowY = 'auto';
    proposalContent.style.height = 'calc(100% - 50px)'; // ヘッダーの高さを引く
    proposalContent.style.padding = '0';
    proposalContent.style.boxSizing = 'border-box';
    
    proposalWrapper.appendChild(proposalContent);
    document.querySelector('.mobility-main-content').appendChild(proposalWrapper);
    
    fetch('/static/html/proposal.html')
    .then(response => {
        if (!response.ok) {
            throw new Error('提案書の読み込みに失敗しました。');
        }
        return response.text();
    })
    .then(html => {
        const proposalContent = document.getElementById('proposal-content-area');
        if (proposalContent) {
            proposalContent.innerHTML = html;
            
            // 提案書内部のスタイルを調整
            const styleElement = document.createElement('style');
            styleElement.textContent = `
                .proposal-container {
                    max-width: 100%;
                    margin: 0;
                    height: auto;
                    overflow: visible;
                }
                .content-section {
                    overflow: visible;
                    height: auto;
                }
                .tab-container {
                    position: sticky;
                    top: 0;
                    z-index: 5;
                    background: #f0f0f0;
                }
                #proposal-content-area {
                    -webkit-overflow-scrolling: touch;
                }
            `;
            document.head.appendChild(styleElement);
            
            // 内部コンテナのスクロール調整
            const proposalContainer = proposalContent.querySelector('.proposal-container');
            if (proposalContainer) {
                proposalContainer.style.height = 'auto';
                proposalContainer.style.overflow = 'visible';
                proposalContainer.style.maxWidth = '100%';
            }
            
            const scripts = proposalContent.querySelectorAll('script');
            scripts.forEach(oldScript => {
                const newScript = document.createElement('script');
                Array.from(oldScript.attributes).forEach(attr => {
                    newScript.setAttribute(attr.name, attr.value);
                });
                newScript.appendChild(document.createTextNode(oldScript.innerHTML));
                oldScript.parentNode.replaceChild(newScript, oldScript);
            });

            // DOMContentLoadedイベントを発火して初期化
            const tabsInit = document.createEvent('Event');
            tabsInit.initEvent('DOMContentLoaded', true, true);
            document.dispatchEvent(tabsInit);
            
            // 追加: 閉じるボタンの初期化
            setTimeout(() => {
              initializeProposalCloseButton();
            }, 500);
        }
    })
    .catch(error => {
        console.error('提案書の読み込みに失敗しました。', error);
        appendMessage('bot', '申し訳ありませんが、提案書の読み込みに失敗しました。もう一度お試しください。');
    });
  } else {
    // すでに存在する場合は表示
    proposalWrapper.style.display = 'flex';
    
    // 追加: 閉じるボタンの初期化
    setTimeout(() => {
      initializeProposalCloseButton();
    }, 500);
  }
  
  // 少し遅延させて提案書が表示された後にメッセージを追加
  setTimeout(() => {
    appendMessage('bot', '提案書が表示されました。右側のタブを切り替えて、各セクションをご確認ください。ご質問があればいつでもお聞きください。');
  }, 1500);
}


// 提案書を非表示にする関数
function hideProposal() {
  // レイアウト変更クラスを削除
  const proposalWrapper = document.querySelector('.proposal-container-wrapper');
  if (proposalWrapper) {
    proposalWrapper.style.display = 'none';
    
    // フォームコンテナを再表示
    const formContainer = document.querySelector('.mobility-form-container');
    if (formContainer) {
      formContainer.style.display = 'block';
    }
    
    appendMessage('bot', '提案書を閉じました。また確認されたい場合は「提案を作成する」ボタンをクリックしてください。');
    
    // メニューアイテムの元の動作を復元
    const menuItems = document.querySelectorAll('.sidebar-menu .menu-item');
    menuItems.forEach(item => {
      const menuText = item.querySelector('.menu-text');
      if (menuText && menuText.hasAttribute('onclick')) {
        // 元のonclick属性を維持し、再度正しいURLを割り当てる
        const href = menuText.getAttribute('href');
        if (href) {
          menuText.setAttribute('onclick', `window.location.href='${href}'`);
        }
      }
    });
    
    // 必要に応じてアクティブクラスを再設定
    const currentPath = window.location.pathname;
    menuItems.forEach(item => {
      const link = item.querySelector('a');
      if (link && currentPath.includes(link.getAttribute('href'))) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  }
}

function initializeProposalCloseButton() {
  const closeButton = document.querySelector('.proposal-header .proposal-close-btn');
  if (closeButton) {
    closeButton.addEventListener('click', hideProposal);
  } else {
    const closeButtons = document.querySelectorAll('.proposal-header div');
    closeButtons.forEach(btn => {
      if (btn.textContent.includes('×')) {
      btn.style.cursor = 'pointer';
      btn.addEventListener('click', hideProposal);
      }
    });
  }
}

// タブ切り替えの初期化
function initializeProposalTabs() {
  const tabs = document.querySelectorAll('.tab');
  if (tabs.length === 0) return;
  
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // すべてのタブから active クラスを削除
      tabs.forEach(t => t.classList.remove('active'));
      
      // クリックされたタブに active クラスを追加
      tab.classList.add('active');
      
      // すべてのコンテンツセクションを非表示
      const contentSections = document.querySelectorAll('.content-section');
      contentSections.forEach(section => section.classList.remove('active'));
      
      // 対応するコンテンツセクションを表示
      const tabId = tab.getAttribute('data-tab');
      const contentSection = document.getElementById(tabId);
      if (contentSection) {
        contentSection.classList.add('active');
      }
    });
  });
}

// 支払いプランの対話機能初期化
function initializePaymentInteractions() {
  setTimeout(() => {
    const paymentInputs = document.querySelectorAll('.payment-input');
    if (paymentInputs.length > 0) {
      paymentInputs.forEach(input => {
        input.addEventListener('input', updatePaymentCalculation);
      });
    }
    
    // 初期計算を実行
    updatePaymentCalculation();
  }, 500);
}

// 支払い計算の更新
function updatePaymentCalculation() {
  const downPaymentInput = document.querySelector('.payment-input[value="500,000"]');
  const termInput = document.querySelector('.payment-input[value="5"]');
  
  if (!downPaymentInput || !termInput) return;
  
  // 値の解析
  let downPayment = parseFloat(downPaymentInput.value.replace(/,/g, '')) || 500000;
  let term = parseFloat(termInput.value) || 5;
  
  // 入力値の検証と制限
  downPayment = Math.max(0, Math.min(downPayment, 3000000));
  term = Math.max(1, Math.min(term, 10));
  
  // 入力値の表示形式を設定
  downPaymentInput.value = downPayment.toLocaleString();
  termInput.value = term;
  
  // ローン計算
  const vehiclePrice = 3580000;
  const tradeInValue = 1800000;
  const loanAmount = vehiclePrice - tradeInValue - downPayment;
  const interestRate = 0.019; // 1.9%
  const months = term * 12;
  
  // 月々の支払い計算
  const monthlyInterestRate = interestRate / 12;
  const monthlyPayment = (loanAmount * monthlyInterestRate) / (1 - Math.pow(1 + monthlyInterestRate, -months));
  
  // 表示を更新
  const totalDisplays = document.querySelectorAll('.highlight-value');
  if (totalDisplays.length >= 2) {
    totalDisplays[1].textContent = Math.round(monthlyPayment).toLocaleString() + '円';
  }
  
  // 計算詳細を更新
  const calculationDetails = document.querySelectorAll('.calculation-details');
  if (calculationDetails.length >= 2) {
    const rows = calculationDetails[1].querySelectorAll('.calculation-row');
    if (rows.length >= 4) {
      rows[0].textContent = '頭金　　　　　　' + downPayment.toLocaleString() + '円';
      rows[1].textContent = 'お支払い回数　　' + (term * 12) + '回（' + term + '年）';
      rows[2].textContent = '金利　　　　　　1.9%';
      rows[3].textContent = 'ローン金額　　　' + loanAmount.toLocaleString() + '円';
    }
  }
}
