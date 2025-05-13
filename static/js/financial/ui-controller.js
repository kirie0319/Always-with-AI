/**
 * UI操作関連の関数
 * UIの表示/非表示や状態管理を担当
 */
import config from './config.js';

// 現在のステップを管理する変数
let currentStep = config.defaultStep;

/**
 * ステップの表示/非表示を更新する関数
 */
function updateStepVisibility() {
  // すべてのステップを取得
  const step0 = document.getElementById('step-0');
  const step1 = document.getElementById('step-1');
  const step2 = document.getElementById('step-2');
  const step3 = document.getElementById('step-3');
  const steps = [step0, step1, step2, step3];
  
  // すべてのステップを非表示
  steps.forEach(step => {
    if (step) {
      step.classList.add('hidden');
    }
  });

  // 現在のステップを表示
  if (steps[currentStep]) {
    steps[currentStep].classList.remove('hidden');
  }
}

/**
 * ステップを指定の番号に変更する関数
 * @param {number} step - 移動先のステップ番号
 */
function changeStep(step) {
  if (step >= 0 && step <= 3) {
    currentStep = step;
    updateStepVisibility();
  }
}

/**
 * 次のステップに進む関数
 */
function nextStep() {
  if (currentStep < 3) {
    currentStep++;
    updateStepVisibility();
  }
}

/**
 * 前のステップに戻る関数
 */
function prevStep() {
  if (currentStep > 0) {
    currentStep--;
    updateStepVisibility();
  }
}

/**
 * タブを切り替える関数
 * @param {number} index - 表示するタブのインデックス
 */
function changeTab(index) {
  // すべてのタブからactiveクラスを削除
  const tabs = document.querySelectorAll('.financial-tab-item');
  tabs.forEach(tab => {
    tab.classList.remove('active');
  });

  // クリックされたタブにactiveクラスを追加
  if (tabs[index]) {
    tabs[index].classList.add('active');
  }
  
  // タブコンテンツの表示を切り替える
  const tabContents = document.querySelectorAll('.tab-content');
  tabContents.forEach(content => {
    content.classList.add('hidden');
    content.classList.remove('active');
  });
  
  if (index === 0) {
    const customerInfoContent = document.getElementById('customer-info-content');
    if (customerInfoContent) {
      customerInfoContent.classList.remove('hidden');
      customerInfoContent.classList.add('active');
    }
  } else if (index === 1) {
    const lifeSimulationContent = document.getElementById('life-simulation-content');
    if (lifeSimulationContent) {
      lifeSimulationContent.classList.remove('hidden');
      lifeSimulationContent.classList.add('active');
    }
  } else if (index === 2) {
    const investmentStrategyContent = document.getElementById('investment-strategy-content');
    if (investmentStrategyContent) {
      investmentStrategyContent.classList.remove('hidden');
      investmentStrategyContent.classList.add('active');
    }
  }
}

/**
 * 投資戦略タブを切り替える関数
 * @param {string} tabId - 表示するタブのID
 */
function changeInvestmentTab(tabId) {
  // すべてのタブボタンからactiveクラスを削除
  const tabButtons = document.querySelectorAll('.investment-tab-btn');
  tabButtons.forEach(btn => btn.classList.remove('active'));
  
  // クリックされたタブボタンにactiveクラスを追加
  const targetButton = document.querySelector(`.investment-tab-btn[data-tab="${tabId}"]`);
  if (targetButton) {
    targetButton.classList.add('active');
  }
  
  // すべてのタブコンテンツからactiveクラスを削除
  const tabContents = document.querySelectorAll('.investment-strategy-tab');
  tabContents.forEach(content => content.classList.remove('active'));
  
  // 対象のタブコンテンツにactiveクラスを追加
  const targetContent = document.getElementById(tabId);
  if (targetContent) {
    targetContent.classList.add('active');
  }
}

/**
 * オプションボタンの選択処理を設定する関数
 */
function setupOptionButtons() {
  const optionButtons = document.querySelectorAll('.financial-option-button');
  optionButtons.forEach((button) => {
    button.addEventListener('click', () => {
      // 同じグループ内の他のボタンからアクティブクラスを削除
      const parentGroup = button.closest('.financial-button-group');
      if (parentGroup) {
        parentGroup.querySelectorAll('.financial-option-button').forEach((groupButton) => {
          groupButton.classList.remove('active');
        });
      }

      // クリックされたボタンにアクティブクラスを追加
      button.classList.add('active');
    });
  });
}

/**
 * DOM要素のイベントリスナーを設定する関数
 * @param {string} elementId - イベントリスナーを追加する要素のID
 * @param {string} eventType - イベントタイプ（例: 'click'）
 * @param {Function} handler - イベントハンドラ関数
 */
function addEventListenerById(elementId, eventType, handler) {
  const element = document.getElementById(elementId);
  if (element) {
    element.addEventListener(eventType, handler);
  }
}

/**
 * 要素がDOMに存在するかどうかを確認する関数
 * @param {string} elementId - 確認する要素のID
 * @returns {boolean} - 要素が存在すればtrue、そうでなければfalse
 */
function elementExists(elementId) {
  return !!document.getElementById(elementId);
}

export {
  currentStep,
  updateStepVisibility,
  changeStep,
  nextStep,
  prevStep,
  changeTab,
  changeInvestmentTab,
  setupOptionButtons,
  addEventListenerById,
  elementExists
};