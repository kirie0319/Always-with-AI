/**
 * 投資戦略データ管理とUIとの連携を担当
 */
import config from './config.js';
import { getAuthHeaders } from './api-service.js';

// 戦略コンテンツ要素
let currentAnalysisContent;
let strategy1Content;
let strategy2Content;
let strategy3Content;

// 最新の戦略データ
let latestStrategyData = null;

/**
 * 投資戦略表示機能の初期化
 */
function initStrategyDisplay() {
  // DOM要素の参照を取得
  currentAnalysisContent = document.getElementById('currentAnalysisContent');
  strategy1Content = document.getElementById('strategy1Content');
  strategy2Content = document.getElementById('strategy2Content');
  strategy3Content = document.getElementById('strategy3Content');
  
  if (!currentAnalysisContent || !strategy1Content || !strategy2Content || !strategy3Content) {
    console.error('戦略表示要素が見つかりません');
    return;
  }
  
  // 戦略データを取得
  fetchStrategyData();
  
  // タブ切り替え時の処理
  setupStrategyTabs();
}

/**
 * 戦略タブの設定
 */
function setupStrategyTabs() {
  const strategyTabs = document.querySelectorAll('.investment-tab-btn');
  strategyTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // すべてのタブからactiveクラスを削除
      strategyTabs.forEach(t => t.classList.remove('active'));
      
      // クリックされたタブにactiveクラスを追加
      tab.classList.add('active');
      
      // タブコンテンツの表示を切り替え
      const tabId = tab.getAttribute('data-tab');
      document.querySelectorAll('.investment-strategy-tab').forEach(content => {
        content.classList.remove('active');
      });
      
      const targetContent = document.getElementById(tabId);
      if (targetContent) {
        targetContent.classList.add('active');
      }
    });
  });
}

/**
 * 戦略データをAPIから取得
 */
async function fetchStrategyData() {
  try {
    const response = await fetch(`/financial/get-strategy`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    
    const result = await response.json();
    
    if (response.ok && result.success) {
      // 戦略データを取得できた場合
      console.log('戦略データを取得しました:', result);
      
      // 最新の戦略データを取得（日付でソート）
      const timestamps = Object.keys(result.strategy_data).sort().reverse();
      if (timestamps.length > 0) {
        latestStrategyData = result.strategy_data[timestamps[0]];
        
        // UIに戦略データを表示
        updateStrategyDisplay(latestStrategyData);
      }
    } else {
      console.log('戦略データはまだ生成されていません。フォームを完了してください。');
    }
  } catch (error) {
    console.error('戦略データの取得に失敗しました:', error);
  }
}

/**
 * 戦略データをUI要素に表示
 * @param {Object} strategyData - バックエンドから取得した戦略データ
 */
function updateStrategyDisplay(strategyData) {
  if (!strategyData) return;
  
  // markedがロードされているか確認
  const parseMarkdown = typeof marked !== 'undefined' ? 
    (text) => marked.parse(text) : 
    (text) => `<pre>${text}</pre>`;
  
  // 現在の分析
  if (currentAnalysisContent && strategyData.current_analysis) {
    currentAnalysisContent.innerHTML = parseMarkdown(strategyData.current_analysis);
  }
  
  // 戦略1
  if (strategy1Content && strategyData.strategy_1) {
    strategy1Content.innerHTML = parseMarkdown(strategyData.strategy_1);
  }
  
  // 戦略2
  if (strategy2Content && strategyData.strategy_2) {
    strategy2Content.innerHTML = parseMarkdown(strategyData.strategy_2);
  }
  
  // 戦略3
  if (strategy3Content && strategyData.strategy_3) {
    strategy3Content.innerHTML = parseMarkdown(strategyData.strategy_3);
  }
  
  // ハイライトコードブロック（もしhljs利用可能なら）
  if (typeof hljs !== 'undefined') {
    document.querySelectorAll('.markdown-content pre code').forEach((block) => {
      hljs.highlightElement(block);
    });
  }
}

/**
 * フォーム送信後に戦略データを再取得
 */
function refreshStrategyData() {
  console.log('戦略データを更新しています...');
  fetchStrategyData();
}

export {
  initStrategyDisplay,
  refreshStrategyData
};