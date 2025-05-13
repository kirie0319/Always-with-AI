// 投資戦略タブのHTMLを初期化する関数
function initInvestmentStrategyTab() {
    const investmentContent = document.getElementById('investment-strategy-content');
    
    // 投資戦略タブの内容を空にして基本構造だけ残す
    investmentContent.innerHTML = `
      <div class="financial-step-container">
        <div class="financial-step-header">
          <div class="financial-step-number"><i class="fas fa-chart-line"></i></div>
          <div class="financial-step-title">ライフプランニング戦略提案</div>
        </div>
        
        <div class="financial-step-content">
          <p class="financial-instruction">お客様の状況に合わせた最適な資産運用プランをご提案します。</p>
          
          <!-- 投資戦略タブナビゲーション -->
          <div class="investment-tab-navigation">
            <button class="investment-tab-btn active" data-tab="currentOperation">
              現運用
            </button>
            <button class="investment-tab-btn" data-tab="strategy1">
              戦略パターン 1
            </button>
            <button class="investment-tab-btn" data-tab="strategy2">
              戦略パターン 2
            </button>
            <button class="investment-tab-btn" data-tab="strategy3">
              戦略パターン 3
            </button>
          </div>
          
          <!-- 投資戦略タブコンテンツ -->
          <div class="investment-container">
            <div id="currentOperation" class="investment-strategy-tab active">
              <div class="loading-indicator">
                <i class="fas fa-spinner fa-spin"></i> 現運用データを読み込み中...
              </div>
            </div>
            
            <div id="strategy1" class="investment-strategy-tab">
              <div class="loading-indicator">
                <i class="fas fa-spinner fa-spin"></i> 戦略パターン1を読み込み中...
              </div>
            </div>
            
            <div id="strategy2" class="investment-strategy-tab">
              <div class="loading-indicator">
                <i class="fas fa-spinner fa-spin"></i> 戦略パターン2を読み込み中...
              </div>
            </div>
            
            <div id="strategy3" class="investment-strategy-tab">
              <div class="loading-indicator">
                <i class="fas fa-spinner fa-spin"></i> 戦略パターン3を読み込み中...
              </div>
            </div>
          </div>
          
          <div class="financial-button-container">
            <button class="financial-action-button return-to-customer-info">顧客情報に戻る</button>
          </div>
        </div>
      </div>
    `;
    
    // タブ切り替え機能を初期化
    initInvestmentTabSwitching();
    
    // 「顧客情報に戻る」ボタンの処理
    document.querySelector('.return-to-customer-info').addEventListener('click', () => {
      changeTab(0);
    });
  }
  
  // 投資戦略タブの切り替え機能を初期化
  function initInvestmentTabSwitching() {
    const tabButtons = document.querySelectorAll('.investment-tab-btn');
    const tabContents = document.querySelectorAll('.investment-strategy-tab');
    
    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        // タブボタンの切替
        tabButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        
        // タブコンテンツの切替
        const tabId = button.getAttribute('data-tab');
        tabContents.forEach(content => {
          content.classList.remove('active');
        });
        document.getElementById(tabId).classList.add('active');
      });
    });
  }
  
  // 投資戦略データを取得する関数
  async function fetchStrategyData() {
    try {
      console.log('戦略データを取得中...');
      
      // APIからデータを取得
      const response = await fetch('/financial/get-strategy', {
        method: 'GET',
        headers: getAuthHeaders()
      });
      
      if (!response.ok) {
        // 404の場合は財務情報を送信していない可能性があるのでフォーム送信を促す
        if (response.status === 404) {
          showStrategyErrorMessage('戦略データがまだ生成されていません。まずは顧客情報を入力して完了ボタンを押してください。');
          return;
        }
        throw new Error('戦略データの取得に失敗しました');
      }
      
      const data = await response.json();
      
      if (data.success && data.strategy_data) {
        // マークダウンデータを各タブに適用
        applyMarkdownToStrategyTabs(data.strategy_data);
      } else {
        showStrategyErrorMessage('戦略データが見つかりませんでした。顧客情報を入力してください。');
      }
    } catch (error) {
      console.error('戦略データの取得エラー:', error);
      showStrategyErrorMessage('戦略データの取得中にエラーが発生しました。');
    }
  }
  
  // マークダウンを各タブに適用する関数
  function applyMarkdownToStrategyTabs(strategyData) {
    const mappings = {
      'current_analysis': 'currentOperation',
      'strategy_1': 'strategy1',
      'strategy_2': 'strategy2',
      'strategy_3': 'strategy3'
    };
    
    // 各タブのコンテンツを更新
    for (const [dataKey, tabId] of Object.entries(mappings)) {
      if (strategyData[dataKey]) {
        const tabContent = document.getElementById(tabId);
        if (tabContent) {
          // マークダウンをHTMLに変換してタブに設定
          const markdownText = strategyData[dataKey];
          
          // マークダウンを表示用のHTMLに変換
          tabContent.innerHTML = renderStrategyMarkdown(markdownText);
        }
      }
    }
  }
  
  // 戦略用のマークダウンをHTMLに変換する関数
  function renderStrategyMarkdown(markdownText) {
    // マークダウンをHTMLに変換
    const html = marked.parse(markdownText);
    
    // もし特定のスタイリングや構造調整が必要であれば、
    // ここでさらに処理を追加することができます
    
    return html;
  }
  
  // エラーメッセージを表示する関数
  function showStrategyErrorMessage(message) {
    const tabContents = document.querySelectorAll('.investment-strategy-tab');
    tabContents.forEach(tab => {
      tab.innerHTML = `
        <div class="error-message">
          <i class="fas fa-exclamation-circle"></i>
          <p>${message}</p>
        </div>
      `;
    });
  }
  
  // フォームの送信処理を行う関数
  async function submitFinancialFormData() {
    try {
      // ローディング表示
      showFinancialFormSubmittingMessage();
      
      // フォームデータの収集
      const formData = collectFinancialFormData();
      
      // フォームデータをAPIに送信
      const response = await fetch('/financial/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        throw new Error('財務情報の送信に失敗しました');
      }
      
      const data = await response.json();
      
      if (data.success) {
        // 送信成功のメッセージをチャットに表示
        appendMessage('ai', '財務情報の分析が完了しました。投資戦略タブで詳細な提案をご確認いただけます。');
        
        // 投資戦略タブに切り替え
        changeTab(2);
        
        // 少し遅延を入れて戦略データを取得（サーバー側の処理に時間がかかる場合）
        setTimeout(() => {
          // 投資戦略タブを初期化して戦略データを取得
          initInvestmentStrategyTab();
          fetchStrategyData();
        }, 500);
        
        return true;
      } else {
        throw new Error(data.message || '財務情報の送信に失敗しました');
      }
    } catch (error) {
      console.error('財務情報送信エラー:', error);
      appendMessage('ai', `エラー: ${error.message}`);
      return false;
    }
  }
  
  // フォーム送信中のメッセージを表示
  function showFinancialFormSubmittingMessage() {
    appendMessage('ai', '財務情報を分析中です。少々お待ちください...');
  }
  
  // フォームデータを収集する関数
  function collectFinancialFormData() {
    // 実際のフォームデータを収集するコードをここに実装
    // この例では簡略化のため、ダミーデータを返します
    return {
      personal_info: {
        age: parseInt(document.getElementById('age').value) || 0,
        industry: document.getElementById('industry').value,
        company: document.getElementById('company').value,
        position: document.getElementById('position').value,
        job_type: document.getElementById('job-type').value,
        annual_income: parseInt(document.getElementById('annual-income').value) || 0,
        // 家族構成の取得
        family_structure: document.querySelector('.financial-option-button.active[data-value]')?.dataset.value || '独身'
      },
      // 他の必要なフォームデータを追加
      // ...
    };
  }
  
  // イベントリスナーの設定
  document.addEventListener('DOMContentLoaded', function() {
    // 既存のDOMContentLoadedイベントハンドラに追加
    
    // 投資戦略タブが選択されたときの処理
    document.querySelectorAll('.financial-tab-item')[2].addEventListener('click', function() {
      // 投資戦略タブが初めて選択されたときの処理
      const investmentContent = document.getElementById('investment-strategy-content');
      if (!investmentContent.querySelector('.investment-container')) {
        initInvestmentStrategyTab();
        fetchStrategyData();
      }
    });
    
    // フォーム完了ボタンのイベントリスナー
    const completeFormButton = document.getElementById('complete-form');
    if (completeFormButton) {
      completeFormButton.addEventListener('click', async function(e) {
        e.preventDefault();
        await submitFinancialFormData();
      });
    }
  });
  
  // スタイルの追加
  document.head.insertAdjacentHTML('beforeend', `
    <style>
      .loading-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        color: #6b7280;
        font-size: 0.9rem;
      }
      
      .loading-indicator i {
        margin-right: 0.5rem;
      }
      
      .error-message {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        color: #ef4444;
        text-align: center;
      }
      
      .error-message i {
        font-size: 2rem;
        margin-bottom: 1rem;
      }
      
      /* マークダウンスタイルの調整 */
      .investment-strategy-tab h1, 
      .investment-strategy-tab h2 {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 0.75rem;
        margin-top: 1.5rem;
      }
      
      .investment-strategy-tab h3 {
        font-size: 1.25rem;
        font-weight: 600;
        color: #334155;
        margin-bottom: 0.5rem;
        margin-top: 1.25rem;
      }
      
      .investment-strategy-tab h4 {
        font-size: 1.125rem;
        font-weight: 600;
        color: #475569;
        margin-bottom: 0.5rem;
        margin-top: 1rem;
      }
      
      .investment-strategy-tab p {
        margin-bottom: 1rem;
        line-height: 1.5;
      }
      
      .investment-strategy-tab ul {
        margin-bottom: 1rem;
        padding-left: 1.5rem;
        list-style-type: disc;
      }
      
      .investment-strategy-tab li {
        margin-bottom: 0.25rem;
      }
      
      .investment-strategy-tab table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1rem;
      }
      
      .investment-strategy-tab table th {
        background-color: #f1f5f9;
        font-weight: 600;
        text-align: left;
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid #e2e8f0;
      }
      
      .investment-strategy-tab table td {
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid #e2e8f0;
      }
      
      .investment-strategy-tab table tr:nth-child(even) {
        background-color: #f8fafc;
      }
    </style>
  `);