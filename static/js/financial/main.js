/**
 * Financial Supporter AI アプリケーションのメインファイル
 * アプリケーションの初期化と統合を担当
 */
import config from './config.js';
import { fetchCRMData, loadConversationHistory, submitFormData, validateToken } from './api-service.js';
import { collectFormData, populateFormWithCRMData } from './form-handler.js';
import { 
  updateStepVisibility, 
  changeStep, 
  setupOptionButtons, 
  addEventListenerById, 
  elementExists,
  changeTab,
  changeInvestmentTab
} from './ui-controller.js';
import { 
  initChat, 
  appendMessage, 
  send, 
  clearChat 
} from './chat-handler.js';
import {
    initStrategyDisplay,
    refreshStrategyData
} from './strategy-handler.js';

/**
 * アプリケーションの初期化
 */
function initApp() {
  console.log('Financial Supporter AIを初期化しています...');
  
  // チャット機能の初期化
  initChat();

  initStrategyDisplay();
  
  // 選択中のプロンプト名を表示
  displaySelectedPromptName();
  
  // UI要素のイベントリスナーを設定
  setupEventListeners();
  
  // オプションボタンの設定
  setupOptionButtons();
  
  // 会話履歴のロード
  loadConversationHistory()
    .then(history => {
      history.forEach(msg => {
        appendMessage(msg.role === "user" ? "user" : "ai", msg.content);
      });
    })
    .catch(error => {
      console.error('Error loading conversation history:', error);
      appendMessage('ai', '申し訳ありません。会話履歴の読み込みに失敗しました。');
    });
    
  // トークン検証
  validateSessionToken();
  
  // 初期ステップの表示
  updateStepVisibility();
  
  // 投資戦略タブの設定
  setupInvestmentTabs();
  
  console.log('初期化完了');
}

/**
 * セッションストレージから選択中のプロンプト名を取得して表示
 */
function displaySelectedPromptName() {
  const promptNameElement = document.getElementById('prompt-name');
  if (promptNameElement) {
    const selectedPromptName = sessionStorage.getItem(config.storageKeys.selectedPromptName);
    if (selectedPromptName) {
      promptNameElement.textContent = selectedPromptName;
    }
  }
}

/**
 * アクセストークンの検証
 */
function validateSessionToken() {
  const token = localStorage.getItem(config.storageKeys.accessToken);
  if (!token) {
    console.error('アクセストークンがありません。ログインページにリダイレクトします。');
    window.location.href = '/login';
    return;
  }
  
  console.log('アクセストークンが見つかりました。トークンの最初の10文字: ' + token.substring(0, 10) + '...');

  validateToken()
    .then(data => {
      console.log('トークン検証成功:', data);
    })
    .catch(error => {
      console.error('トークン検証エラー:', error);
      // トークンが無効な場合はログインページにリダイレクト
      localStorage.removeItem(config.storageKeys.accessToken);
      window.location.href = '/login?invalid_token=true';
    });
}

/**
 * UI要素のイベントリスナーを設定
 */
function setupEventListeners() {
  // CRMデータ連携ボタン
  addEventListenerById('connect-info-btn', 'click', handleConnectInfoClick);
  
  // ステップナビゲーションボタン
  addEventListenerById('back-to-step-0', 'click', () => changeStep(0));
  addEventListenerById('next-to-step-2', 'click', () => changeStep(2));
  addEventListenerById('back-to-step-1', 'click', () => changeStep(1));
  addEventListenerById('next-to-step-3', 'click', () => changeStep(3));
  addEventListenerById('back-to-step-2', 'click', () => changeStep(2));
  
  // フォーム完了ボタン
  addEventListenerById('complete-form', 'click', handleFormCompletion);
  
  // チャット関連
  addEventListenerById('input', 'keypress', event => {
    if (event.key === 'Enter') {
      send();
    }
  });
  addEventListenerById('send-btn', 'click', send);
  addEventListenerById('clear-btn', 'click', clearChat);
  
  // 顧客情報タブに戻るボタン
  const returnButtons = document.querySelectorAll('.return-to-customer-info');
  returnButtons.forEach(button => {
    button.addEventListener('click', () => {
      changeTab(0);
    });
  });
}

/**
 * 投資戦略タブの設定
 */
function setupInvestmentTabs() {
  const investmentTabButtons = document.querySelectorAll('.investment-tab-btn');
  
  investmentTabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabId = button.getAttribute('data-tab');
      changeInvestmentTab(tabId);
    });
  });
}

/**
 * CRM情報連携ボタンの処理
 */
async function handleConnectInfoClick() {
  console.log('Connect Info Button Clicked');
  
  const cifInput = document.getElementById('cif');
  if (!cifInput) {
    console.error('CIF入力フィールドが見つかりません');
    return;
  }
  
  const cifId = cifInput.value.trim();
  
  if (!cifId) {
    alert('CIF番号を入力してください');
    return;
  }
  
  try {
    // サーバーからCRMデータを取得
    const result = await fetchCRMData(cifId);
    
    if (!result.success) {
      throw new Error(result.message || 'CRMデータの取得に失敗しました');
    }
    
    console.log(`CIF ID ${cifId} のデータを取得しました:`, result.data);
    
    // フォームにデータを設定
    populateFormWithCRMData(result.data);
    
    // ステップを進める
    changeStep(1);
  } catch (error) {
    console.error('CRMデータ取得エラー:', error);
    alert(`CIF ID ${cifId} のデータの取得に失敗しました: ${error.message}`);
  }
}

/**
 * フォーム完了時の処理
 */
async function handleFormCompletion() {
  try {
    // フォームデータの収集
    const formData = collectFormData();
    console.log('収集したフォームデータ:', formData);
    
    // バックエンドにデータを送信
    const result = await submitFormData(formData);
    console.log('サーバーレスポンス:', result);
    
    // 成功メッセージ
    alert('フォーム情報が送信されました！');

    refreshStrategyData();
    
    // AIアシスタントに表示するメッセージを送信
    appendMessage('ai', `
      お客様の情報を受け付けました。以下の情報に基づいて、最適な資産運用プランをご提案いたします。
      
      • 年齢: ${formData.personalInfo.age}歳
      • 年収: ${formData.personalInfo.annualIncome}万円
      • 貯金額: ${formData.financialInfo.savings}万円
      • 運用資産: ${formData.financialInfo.hasInvestments ? 'あり' : 'なし'}
      • 投資スタンス: ${formData.intentions.investmentStance}
      
      ご質問やご相談がございましたら、お気軽にメッセージをお送りください。
    `);
  } catch (error) {
    console.error('フォーム送信エラー:', error);
    alert(`エラーが発生しました: ${error.message}`);
  }
}

// DOMContentLoaded イベントで初期化
document.addEventListener('DOMContentLoaded', initApp);

// グローバルに公開する関数
window.changeTab = changeTab;
window.clearChat = clearChat;
window.send = send;